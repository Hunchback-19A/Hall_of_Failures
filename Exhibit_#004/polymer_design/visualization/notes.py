# Copyright (C) 2026 Disquietude
# GPL-3.0-or-later. See the project LICENSE.
"""Wording shared by every morphology picture."""

VISUALIZATION_NOTE = (
    "This picture shows the morphology from the selected computational model. "
    "It is a coarse-grained view of A-rich and B-rich regions. "
    "Avogadro draws only the boundary of each region, not the material that fills it. "
    "A shell around a sphere or tube is the interface between the two blocks: "
    "one block fills the core, and the other fills the domain outside that shell. "
    "It is not an atomistic polymer structure, not a movie of chains moving, "
    "and not an experimental image. "
    "Experimental morphology may differ because of kinetics, dispersity, "
    "processing, solvent history, defects, and temperature history. "
    "The picture requires experimental validation."
)

SEGMENT_FIGURE_NOTE = (
    "profile.png plots the A-block fraction in red and one minus that fraction in blue. "
    "segment.png paints the same fraction on the cell: red is A-rich, blue is B-rich, "
    "and green is the interface between them. "
    "interface.png draws the surface where the fraction crosses one half. "
    "These pictures use this file's segment fraction. "
    "They are not a SUSHI calculation and not an experimental image."
)

EXPORTER_VERSION = "1"
MORPHOLOGY_SCHEMA = "polymer_design.morphology.v1"
BATCH_SCHEMA = "polymer_design.visualization.batch.v1"
REQUEST_SCHEMA = "polymer_design.visualize.v1"
