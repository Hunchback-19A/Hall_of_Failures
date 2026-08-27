"""Axon Viewer placeholder.

Future versions may display brain meshes and network graphs from the Ranvier
models. That display would be a map, not a territory: geometry and connectivity,
never stimulation and never a biological interface.

Axon v0.1 does not implement a viewer.
"""

from __future__ import annotations

PLACEHOLDER_TITLE = "Axon Viewer"
PLACEHOLDER_VERSION = "planned"

PLACEHOLDER_MESSAGE = """\
Axon Viewer is not available in v0.1.

Future idea:
    display brain meshes and network models
    (atlas bounds, tracts, associated networks)

This would be visualization of files in models/, not a brain interface.

Axon will not:
    stimulate neurons
    control tissue
    open a biological connection

Never compile a destiny when you only measured a state.
"""


class AxonViewer:
    """Reserved surface for a future model viewer."""

    implemented = False

    def show(self, parent=None) -> str:
        """Return the placeholder text. A GUI host may show it in a dialog."""
        return PLACEHOLDER_MESSAGE.strip()


def open_viewer(parent=None) -> str:
    """Public placeholder entry. Does not display meshes."""
    return AxonViewer().show(parent)
