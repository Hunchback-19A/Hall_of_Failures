"""Camera helpers — keep view logic out of mesh construction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, Tuple

if TYPE_CHECKING:
    import pyvista as pv


def configure_interactive_camera(
    plotter: "pv.Plotter",
    *,
    position: Sequence[float] = (4.2, 0.0, 0.9),
    focal_point: Sequence[float] = (0.0, 0.0, 0.0),
    view_up: Sequence[float] = (0.0, 0.0, 1.0),
) -> None:
    """
    Apply a north-up Earth view (+Z = North).

    Axes widget is placed in the **lower-right** so it does not collide with
    the layer legend on the lower-left.
    """
    plotter.camera_position = [tuple(position), tuple(focal_point), tuple(view_up)]
    plotter.enable_trackball_style()
    # Default show_axes() parks the gizmo at lower-left (on top of our legend).
    plotter.add_axes(viewport=(0.82, 0.02, 0.99, 0.22), line_width=2)
    plotter.add_text(
        "+Z North   +Y East   +X lon 0°\n"
        "Camera: drag=orbit   scroll=zoom   shift+drag=pan",
        position="upper_right",
        font_size=9,
        color="lightgray",
        name="axis_legend",
        viewport=True,
    )


def camera_summary(plotter: "pv.Plotter") -> Tuple[Tuple[float, ...], ...]:
    """Return a serializable camera snapshot for debugging / future tools."""
    cam = plotter.camera
    return (
        tuple(cam.position),
        tuple(cam.focal_point),
        tuple(cam.up),
    )
