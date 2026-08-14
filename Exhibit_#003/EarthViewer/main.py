"""
EarthViewer entry point — rotating Earth with a lightweight control panel.

Run from the repository root::

    pip install -e ".[viewer]"
    python -m EarthViewer.main

Or::

    cd EarthViewer
    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root on path so ``EarthViewer`` and ``megadatetime`` both import cleanly.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from EarthViewer import config
from EarthViewer.renderer.camera import configure_interactive_camera
from EarthViewer.renderer.earth import EarthScene, build_default_registry
from EarthViewer.time.earth_time import EarthTime


class EarthViewerApp:
    """Thin application controller: time engine + scene + UI widgets."""

    # Named 2D overlay captions (not checkboxes, axes gizmo, slider bar, or sim time).
    _OVERLAY_TEXT_NAMES = (
        "axis_legend",
        "lbl_rotate",
        "lbl_layers_hdr",
        "lbl_earth_texture",
        "lbl_night_lights",
        "lbl_clouds",
        "lbl_satellite",
    )
    _SLIDER_TITLE = "Spin speed (deg/s)"
    # Ignore tiny jitter so a true click toggles; a drag still orbits.
    _CLICK_DRAG_PX = 6

    def __init__(self) -> None:
        import pyvista as pv

        config.ensure_data_dirs()

        self.earth_time = EarthTime.now_utc()
        self.rotating = True
        self.rotation_speed = config.DEFAULT_ROTATION_DEG_PER_SEC
        self._overlay_texts_visible = True
        self._press_pos: tuple[int, int] | None = None
        self._speed_slider = None

        pv.global_theme.background = config.BACKGROUND_COLOR
        self.plotter = pv.Plotter(window_size=list(config.WINDOW_SIZE), title=config.WINDOW_TITLE)
        self.plotter.set_background(config.BACKGROUND_COLOR)

        self.registry = build_default_registry()
        self.scene = EarthScene(self.plotter, self.registry)
        self.scene.build()
        # Pre-build satellite markers (hidden) so the toggle is instant.
        self.scene._layer_visibility["satellite"] = False
        self.scene.ensure_satellite_markers(self.earth_time)
        sat = self.scene._actors.get("satellite")
        if sat is not None:
            sat.SetVisibility(False)
            self.scene._layer_visibility["satellite"] = False
        self.registry.get("satellite").set_enabled(False)

        configure_interactive_camera(self.plotter)
        self._add_ui()
        self.plotter.add_text(
            self.earth_time.display(),
            position="upper_left",
            font_size=10,
            color="white",
            name="sim_time",
            viewport=True,
        )

        # Orientation-only timer — meshes are not rebuilt.
        # Large max_steps keeps the globe spinning for a long interactive session.
        if self.plotter.iren is not None:
            self.plotter.iren.initialize()
            self._install_text_toggle_click()
        self.plotter.add_timer_event(
            max_steps=10_000_000,
            duration=config.TIMER_INTERVAL_MS,
            callback=self._on_timer,
        )

    def _add_ui(self) -> None:
        """
        Build on-screen controls.

        Checkbox widgets use **pixel** coordinates from the bottom-left.
        Matching labels must use the same pixel space (``viewport=False``);
        ``viewport=True`` expects normalized 0–1 coords and hid our captions.
        """
        # --- Earth spin (green / red) ---
        self.plotter.add_checkbox_button_widget(
            self._toggle_rotation,
            value=True,
            position=(10, 10),
            size=30,
            border_size=2,
            color_on="lightgreen",
            color_off="tomato",
            background_color="gray",
        )
        self.plotter.add_text(
            "Earth spin  |  on=rotate  off=pause",
            position=(48, 16),
            font_size=11,
            color="white",
            name="lbl_rotate",
            viewport=False,
        )

        # Bottom-right band: short, narrow bar kept off the globe.
        # Title sits below the tube in modern style — leave a little floor
        # clearance so it does not clip the window edge.
        self._speed_slider = self.plotter.add_slider_widget(
            self._on_speed,
            rng=[0.0, config.MAX_ROTATION_DEG_PER_SEC],
            value=self.rotation_speed,
            title=self._SLIDER_TITLE,
            pointa=(0.62, 0.075),
            pointb=(0.84, 0.075),
            style="modern",
            title_height=0.022,
            slider_width=0.02,
            tube_width=0.004,
        )

        # --- Layer toggles (cyan) ---
        self.plotter.add_text(
            "Layers  (cyan = shown)",
            position=(10, 50),
            font_size=10,
            color="lightgray",
            name="lbl_layers_hdr",
            viewport=False,
        )

        layer_controls = (
            (78, "earth_texture", True, "Day map — land / ocean"),
            (118, "night_lights", False, "Night lights — city lights"),
            (158, "clouds", True, "Clouds — layer + drift"),
            (198, "satellite", False, "Satellite — yellow demo dots"),
        )
        for y, name, default, caption in layer_controls:
            self.plotter.add_checkbox_button_widget(
                lambda value, n=name: self._toggle_layer(n, value),
                value=default,
                position=(10, y),
                size=28,
                border_size=2,
                color_on="cyan",
                color_off="dimgray",
                background_color="gray",
            )
            self.plotter.add_text(
                caption,
                position=(48, y + 6),
                font_size=11,
                color="white",
                name=f"lbl_{name}",
                viewport=False,
            )

        # Camera help / axes gizmo live in configure_interactive_camera
        # (upper-right text + lower-right axes) to avoid overlapping this legend.

    def _install_text_toggle_click(self) -> None:
        """Left-click (no drag) toggles overlay captions; drag still orbits."""
        iren = self.plotter.iren
        if iren is None:
            return
        iren.add_observer("LeftButtonPressEvent", self._on_left_press)
        iren.add_observer("LeftButtonReleaseEvent", self._on_left_release)

    def _on_left_press(self, _obj, _event) -> None:
        iren = self.plotter.iren
        if iren is None:
            return
        x, y = iren.get_event_position()
        self._press_pos = (int(x), int(y))

    def _on_left_release(self, _obj, _event) -> None:
        if self._press_pos is None:
            return
        iren = self.plotter.iren
        if iren is None:
            self._press_pos = None
            return
        x, y = iren.get_event_position()
        px, py = self._press_pos
        self._press_pos = None
        if abs(int(x) - px) > self._CLICK_DRAG_PX or abs(int(y) - py) > self._CLICK_DRAG_PX:
            return
        if self._click_hits_chrome(int(x), int(y)):
            return
        self._overlay_texts_visible = not self._overlay_texts_visible
        self._apply_overlay_text_visibility()
        self.plotter.render()

    def _click_hits_chrome(self, x: int, y: int) -> bool:
        """
        True when the click is on checkboxes, slider, or axes — keep those
        interactive without also toggling captions.
        """
        w, h = self.plotter.window_size
        # Left legend: square buttons (+ a little label margin while texts show).
        if x < 48 and y < 240:
            return True
        # Bottom-right: spin slider + axes gizmo.
        if x > int(0.58 * w) and y < int(0.28 * h):
            return True
        return False

    def _apply_overlay_text_visibility(self) -> None:
        """Show/hide caption actors; leave checkboxes, axes, and slider bar."""
        visible = self._overlay_texts_visible
        actors = getattr(self.plotter, "actors", {}) or {}
        for name in self._OVERLAY_TEXT_NAMES:
            actor = actors.get(name)
            if actor is None:
                continue
            try:
                actor.SetVisibility(bool(visible))
            except Exception:
                pass

        if self._speed_slider is not None:
            try:
                rep = self._speed_slider.GetRepresentation()
                if visible:
                    rep.SetTitleText(self._SLIDER_TITLE)
                    rep.ShowSliderLabelOn()
                    rep.GetTitleProperty().SetOpacity(1.0)
                else:
                    rep.SetTitleText("")
                    rep.ShowSliderLabelOff()
                    rep.GetTitleProperty().SetOpacity(0.0)
            except Exception:
                pass

    def _toggle_rotation(self, value: bool) -> None:
        self.rotating = bool(value)

    def _on_speed(self, value: float) -> None:
        self.rotation_speed = float(value)
        if self.rotation_speed <= 0:
            self.rotating = False

    def _toggle_layer(self, name: str, value: bool) -> None:
        visible = bool(value)
        try:
            self.registry.get(name).set_enabled(visible)
        except KeyError:
            pass
        if name == "satellite" and visible:
            self.scene.ensure_satellite_markers(self.earth_time)
        self.scene.set_layer_visible(name, visible)
        self.plotter.render()

    def _on_timer(self, step: int = 0) -> None:
        dt = config.TIMER_INTERVAL_MS / 1000.0
        earth_spin = (
            self.rotation_speed if (self.rotating and self.rotation_speed > 0) else 0.0
        )
        # Clouds keep drifting even if Earth spin is paused.
        self.scene.tick(dt, earth_spin_deg_per_sec=earth_spin)
        if earth_spin > 0:
            # Advance simulation clock in lockstep with visual spin (demo scale).
            self.earth_time.advance(dt * 60.0)  # 1 sim-minute per real second @ default feel
        # Update HUD text without rebuilding the globe.
        try:
            self.plotter.remove_actor("sim_time", render=False)
        except Exception:
            pass
        self.plotter.add_text(
            self.earth_time.display(),
            position="upper_left",
            font_size=10,
            color="white",
            name="sim_time",
            viewport=True,
        )
        self.plotter.render()

    def run(self) -> None:
        self.plotter.show()


def main() -> None:
    try:
        import pyvista  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyVista is required for EarthViewer.\n"
            "Install with:  pip install -e \".[viewer]\"\n"
            f"Details: {exc}"
        ) from exc

    EarthViewerApp().run()


if __name__ == "__main__":
    main()
