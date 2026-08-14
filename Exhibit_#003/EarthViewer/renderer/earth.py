"""
Earth mesh + scene graph for PyVista/VTK.

Geometry is built once. Per-frame work updates actor orientation and toggles
layer visibility — meshes are not rebuilt every frame (C++-acceleration ready).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from EarthViewer import config
from EarthViewer.renderer.layers import (
    CloudLayer,
    DataLayer,
    DayTextureLayer,
    LayerFrame,
    LayerRegistry,
    NightLightsLayer,
    SatellitePlaceholderLayer,
)
from EarthViewer.renderer.textures import load_texture_array, numpy_to_pyvista_texture


def lonlat_to_xyz(
    lon_deg: np.ndarray, lat_deg: np.ndarray, radius: float
) -> np.ndarray:
    """Convert geographic lon/lat degrees to XYZ on a sphere (Z-up = North)."""
    lon = np.radians(lon_deg)
    lat = np.radians(lat_deg)
    x = radius * np.cos(lat) * np.cos(lon)
    y = radius * np.cos(lat) * np.sin(lon)
    z = radius * np.sin(lat)
    return np.column_stack([x, y, z])


def make_textured_sphere(
    radius: float,
    theta_resolution: int,
    phi_resolution: int,
) -> Any:
    """
    Build a sphere with geographic equirectangular UVs and a longitude seam.

    Closed ``texture_map_to_sphere`` meshes pinch at the poles (kaleidoscope
    mirroring). This UV grid:

    - duplicates the ±180° meridian so ``u`` can run 0→1 without wrapping
      across a single triangle
    - keeps parallels slightly off the exact poles so vertices do not collapse
      to one point with every ``u`` at once

    Frame: +Z = North, +X = lon 0°, +Y = lon 90°E.
    Texture: ``u`` = 0 at 180°W … 1 at 180°E; ``v`` chosen so NASA row-0
    (North) appears at +Z under VTK's numpy texture sampling.
    """
    import pyvista as pv

    # Columns include a duplicated seam column (u=0 and u=1).
    n_lon = max(8, int(theta_resolution)) + 1
    n_lat = max(8, int(phi_resolution)) + 1

    # Longitude −180° … +180° (last column duplicates first geographically).
    lon = np.linspace(-np.pi, np.pi, n_lon)
    # Stay off exact ±90° so the pole is a small ring, not a UV singularity.
    lat_max = np.deg2rad(89.5)
    lat = np.linspace(lat_max, -lat_max, n_lat)

    lon_g, lat_g = np.meshgrid(lon, lat)
    x = radius * np.cos(lat_g) * np.cos(lon_g)
    y = radius * np.cos(lat_g) * np.sin(lon_g)
    z = radius * np.sin(lat_g)
    points = np.column_stack([x.ravel(), y.ravel(), z.ravel()])

    u = np.linspace(0.0, 1.0, n_lon)
    # NASA row-0 = North. VTK's numpy texture path samples row-0 at V≈1.
    v = np.linspace(1.0, 0.0, n_lat)  # North→1 … South→0
    u_g, v_g = np.meshgrid(u, v)
    tcoords = np.column_stack([u_g.ravel(), v_g.ravel()]).astype(np.float32)

    faces: list[int] = []
    for i in range(n_lat - 1):
        for j in range(n_lon - 1):
            a = i * n_lon + j
            b = a + 1
            c = a + n_lon
            d = c + 1
            faces.extend([3, a, b, d])
            faces.extend([3, a, d, c])

    mesh = pv.PolyData(points, np.asarray(faces, dtype=np.int64))
    mesh.active_texture_coordinates = tcoords
    mesh.compute_normals(inplace=True, auto_orient_normals=True, consistent_normals=True)
    return mesh


class EarthModel:
    """Spherical Earth geometry — separate from data layers."""

    def __init__(
        self,
        radius: float = config.EARTH_RADIUS,
        theta_resolution: int = config.SPHERE_THETA_RESOLUTION,
        phi_resolution: int = config.SPHERE_PHI_RESOLUTION,
    ) -> None:
        self.radius = radius
        self.mesh = make_textured_sphere(radius, theta_resolution, phi_resolution)


class EarthScene:
    """
    Modular scene controller.

    The plotter is the current graphics backend (PyVista/VTK). Methods that
    mutate actors are intentionally narrow so a future backend or C++ module
    can replace them without rewriting layer logic.
    """

    def __init__(self, plotter: Any, registry: LayerRegistry) -> None:
        self.plotter = plotter
        self.registry = registry
        self.earth = EarthModel()
        self._longitude_deg = 0.0
        self._cloud_longitude_deg = 0.0
        self.cloud_drift_deg_per_sec = float(config.CLOUD_DRIFT_DEG_PER_SEC)
        self._actors: Dict[str, Any] = {}
        self._textures: Dict[str, Any] = {}
        self._layer_visibility: Dict[str, bool] = {}

    def build(self) -> None:
        """Create actors once from geometry + currently available layers."""
        self.registry.load_all()

        day = self._texture_for_role("day", config.texture_path(config.DAY_TEXTURE_NAME))
        self._textures["day"] = day
        earth_actor = self.plotter.add_mesh(
            self.earth.mesh,
            texture=day,
            name="earth",
            smooth_shading=True,
            show_edges=False,
        )
        self._actors["earth"] = earth_actor
        self._layer_visibility["earth_texture"] = True

        # Optional night texture stored for toggling (swap day/night on earth).
        night_arr, _ = load_texture_array(
            config.texture_path(config.NIGHT_TEXTURE_NAME), role="night"
        )
        self._textures["night"] = numpy_to_pyvista_texture(night_arr)
        self._layer_visibility["night_lights"] = False

        # Cloud shell — slight larger radius; same geographic UVs as Earth.
        cloud_arr, _ = load_texture_array(
            config.texture_path(config.CLOUDS_TEXTURE_NAME), role="clouds"
        )
        self._textures["clouds"] = numpy_to_pyvista_texture(cloud_arr)
        clouds = make_textured_sphere(
            radius=self.earth.radius * 1.01,
            theta_resolution=max(16, config.SPHERE_THETA_RESOLUTION // 2 * 2),
            phi_resolution=max(16, config.SPHERE_PHI_RESOLUTION // 2 * 2),
        )
        cloud_actor = self.plotter.add_mesh(
            clouds,
            texture=self._textures["clouds"],
            name="clouds",
            opacity=0.55,
            smooth_shading=True,
        )
        cloud_actor.SetVisibility(True)
        self._actors["clouds"] = cloud_actor
        self._layer_visibility["clouds"] = True

        # Satellite actor is created lazily on first frame (PyVista rejects empty meshes).
        self._actors["satellite"] = None
        self._layer_visibility["satellite"] = False

        self._add_direction_labels()
        self._sync_linked_orientation()

    def _add_direction_labels(self) -> None:
        """Place N / S / E / W markers on the geographic axes (Z-up = North)."""
        r = self.earth.radius * 1.14
        points = np.array(
            [
                [0.0, 0.0, r],  # North
                [0.0, 0.0, -r],  # South
                [0.0, r, 0.0],  # East (lon 90°E)
                [0.0, -r, 0.0],  # West (lon 90°W)
            ],
            dtype=float,
        )
        labels = ["N", "S", "E", "W"]
        actor = self.plotter.add_point_labels(
            points,
            labels,
            font_size=22,
            text_color="white",
            point_color="cyan",
            point_size=8,
            render_points_as_spheres=True,
            shape=None,
            always_visible=False,  # occlude far-side labels (e.g. S when viewing N)
            show_points=True,
            name="direction_labels",
        )
        # World-fixed geographic axes (do not spin with the texture).
        self._actors["direction_labels"] = actor

    def _texture_for_role(self, role: str, path) -> Any:
        array, _src = load_texture_array(path, role=role)
        return numpy_to_pyvista_texture(array)

    def set_longitude(self, longitude_deg: float) -> None:
        """Set absolute Earth rotation (degrees). Does not rebuild meshes."""
        self._longitude_deg = float(longitude_deg) % 360.0
        self._sync_linked_orientation()

    def rotate(self, delta_deg: float) -> None:
        """Spin Earth (and baseline cloud shell) by *delta_deg*."""
        self.set_longitude(self._longitude_deg + delta_deg)

    def tick(self, dt_seconds: float, earth_spin_deg_per_sec: float = 0.0) -> None:
        """
        Advance animation without rebuilding meshes.

        Earth uses *earth_spin_deg_per_sec*. Clouds use that plus an independent
        drift so weather appears to move across the surface.
        """
        dt = float(dt_seconds)
        earth_delta = float(earth_spin_deg_per_sec) * dt
        cloud_delta = earth_delta + self.cloud_drift_deg_per_sec * dt
        self._longitude_deg = (self._longitude_deg + earth_delta) % 360.0
        self._cloud_longitude_deg = (self._cloud_longitude_deg + cloud_delta) % 360.0
        self._sync_linked_orientation()

    def _sync_linked_orientation(self) -> None:
        # Z-up globe: spin about polar axis. Clouds keep a separate longitude.
        earth = self._actors.get("earth")
        if earth is not None:
            earth.SetOrientation(0.0, 0.0, self._longitude_deg)

        clouds = self._actors.get("clouds")
        if clouds is not None:
            clouds.SetOrientation(0.0, 0.0, self._cloud_longitude_deg)

        satellite = self._actors.get("satellite")
        if satellite is not None:
            # Keep markers locked to the surface frame.
            satellite.SetOrientation(0.0, 0.0, self._longitude_deg)

    def set_layer_visible(self, name: str, visible: bool) -> None:
        self._layer_visibility[name] = bool(visible)

        if name == "earth_texture":
            actor = self._actors.get("earth")
            if actor is not None:
                actor.SetVisibility(bool(visible))
            return

        if name == "night_lights":
            actor = self._actors.get("earth")
            if actor is None:
                return
            # Swap texture on the existing earth actor — no mesh rebuild.
            tex = self._textures["night" if visible else "day"]
            try:
                actor.texture = tex
            except Exception:
                # Fallback for older PyVista bindings
                self.plotter.remove_actor("earth", render=False)
                self._actors["earth"] = self.plotter.add_mesh(
                    self.earth.mesh,
                    texture=tex,
                    name="earth",
                    smooth_shading=True,
                )
                self._sync_linked_orientation()
            return

        if name == "clouds":
            actor = self._actors.get("clouds")
            if actor is not None:
                actor.SetVisibility(bool(visible))
            return

        if name == "satellite":
            if visible and self._actors.get("satellite") is None:
                self.ensure_satellite_markers()
            actor = self._actors.get("satellite")
            if actor is not None:
                actor.SetVisibility(bool(visible))
            return

        # Unknown layers: ask registry only (future overlays).
        try:
            self.registry.get(name).set_enabled(visible)
        except KeyError:
            pass

    def apply_layer_frame(self, frame: LayerFrame) -> None:
        """Push a processed frame into the scene (arrays only — no I/O)."""
        if frame.kind == "lonlat_points" and "lonlat" in frame.arrays:
            lonlat = frame.arrays["lonlat"]
            if lonlat.size == 0:
                return
            # Sit clearly above the cloud shell (clouds use radius * 1.01).
            xyz = lonlat_to_xyz(lonlat[:, 0], lonlat[:, 1], self.earth.radius * 1.08)
            import pyvista as pv

            poly = pv.PolyData(xyz)
            # Glyphs are reliable; raw OpenGL point sprites often draw nothing
            # (or vanish in screenshots) depending on the VTK backend.
            markers = poly.glyph(
                geom=pv.Sphere(radius=0.035, theta_resolution=12, phi_resolution=12),
                scale=False,
                orient=False,
            )
            self.plotter.remove_actor("satellite", render=False)
            actor = self.plotter.add_mesh(
                markers,
                color="yellow",
                name="satellite",
                smooth_shading=True,
                lighting=True,
            )
            actor.SetVisibility(self._layer_visibility.get("satellite", False))
            self._actors["satellite"] = actor
            self._sync_linked_orientation()

    def ensure_satellite_markers(self, earth_time=None) -> None:
        """Create or refresh the satellite placeholder points."""
        from EarthViewer.time.earth_time import EarthTime

        layer = self.registry.get("satellite")
        layer.set_enabled(True)
        if getattr(layer, "_points", None) is None:
            layer.load()
        frame = layer.build_frame(earth_time or EarthTime.now_utc())
        if frame is not None:
            self.apply_layer_frame(frame)

    def refresh_enabled_layers(self, earth_time) -> None:
        for frame in self.registry.enabled_frames(earth_time):
            self.apply_layer_frame(frame)


def build_default_registry() -> LayerRegistry:
    """Wire default interchangeable layers (local files / placeholders)."""
    registry = LayerRegistry()
    registry.register(DayTextureLayer(config.texture_path(config.DAY_TEXTURE_NAME)))
    registry.register(NightLightsLayer(config.texture_path(config.NIGHT_TEXTURE_NAME)))
    registry.register(CloudLayer(config.texture_path(config.CLOUDS_TEXTURE_NAME)))
    registry.register(SatellitePlaceholderLayer(config.SATELLITE_DIR))
    return registry
