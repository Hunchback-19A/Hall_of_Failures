"""Monte Carlo solver placeholder — interface only, no fake physics."""

from __future__ import annotations

from .base import SimulationInput, SimulationOutput, Solver


class MonteCarloSolver(Solver):
    """
    Placeholder for a future Monte Carlo polymer solver.

    Intentionally unimplemented: do not return fabricated MC results.
    """

    name = "monte_carlo"

    def solve(self, sim_input: SimulationInput) -> SimulationOutput:
        sim_input.validate()
        raise NotImplementedError(
            "MonteCarloSolver is an interface placeholder only. "
            "No Monte Carlo implementation is available in this phase."
        )
