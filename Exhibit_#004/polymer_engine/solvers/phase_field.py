"""
1D toy Cahn–Hilliard phase-field prototype.

IMPORTANT:
  This is a numerical architecture demonstration only.
  It is NOT a quantitative block-copolymer morphology predictor.

Backends:
  - numpy (default installation path; always available if NumPy is installed)
  - cpp (optional pybind11 extension: polymer_engine._phase_field_cpp)
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .base import SimulationInput, SimulationOutput, Solver

# Agreement tolerance used in Phase 8 verification (documented for reports/tests).
CPP_NUMPY_AGREEMENT_TOL = 1.0e-10


def cpp_extension_available() -> bool:
    try:
        from polymer_engine import _phase_field_cpp  # noqa: F401

        return True
    except Exception:
        return False


def _load_cpp():
    from polymer_engine import _phase_field_cpp

    return _phase_field_cpp


def evolve_numpy(
    phi0: np.ndarray,
    *,
    dx: float,
    dt: float,
    n_steps: int,
    eps2: float,
    mobility: float,
    alpha: float,
) -> tuple[np.ndarray, list[float], float]:
    """Reference NumPy semi-implicit spectral evolution."""
    phi = np.clip(np.asarray(phi0, dtype=float).copy(), -1.5, 1.5)
    n = phi.size
    k = 2.0 * np.pi * np.fft.fftfreq(n, d=dx)
    k2 = k * k
    denom = 1.0 + dt * mobility * eps2 * (k2**2)

    energy_history: list[float] = []
    max_update = 0.0
    stride = max(1, n_steps // 20)

    for step in range(n_steps):
        mu_nl = (phi**3) - (1.0 + alpha) * phi
        phi_hat = np.fft.fft(phi)
        mu_hat = np.fft.fft(mu_nl)
        phi_new_hat = (phi_hat - dt * mobility * k2 * mu_hat) / denom
        phi_new = np.real(np.fft.ifft(phi_new_hat))
        phi_new = np.clip(phi_new, -1.5, 1.5)
        max_update = float(np.max(np.abs(phi_new - phi)))
        phi = phi_new
        if step % stride == 0 or step == n_steps - 1:
            bulk = 0.25 * (phi**2 - 1.0) ** 2 - 0.5 * alpha * phi**2
            grad = 0.5 * eps2 * ((np.roll(phi, -1) - phi) / dx) ** 2
            energy_history.append(float(np.sum(bulk + grad) * dx))

    return phi, energy_history, max_update


def evolve_cpp(
    phi0: np.ndarray,
    *,
    dx: float,
    dt: float,
    n_steps: int,
    eps2: float,
    mobility: float,
    alpha: float,
) -> tuple[np.ndarray, list[float], float]:
    """Optional C++ timestep kernel (same math as evolve_numpy)."""
    mod = _load_cpp()
    result = mod.evolve_cahn_hilliard_1d(
        np.asarray(phi0, dtype=float).tolist(),
        float(dx),
        float(dt),
        int(n_steps),
        float(eps2),
        float(mobility),
        float(alpha),
    )
    return np.asarray(result.phi, dtype=float), list(result.energy_history), float(result.max_update)


def resolve_backend(requested: str) -> str:
    """
    requested: 'numpy' | 'cpp' | 'auto'
    auto -> cpp if extension importable, else numpy
    """
    key = (requested or "auto").lower().strip()
    if key == "numpy":
        return "numpy"
    if key == "cpp":
        if not cpp_extension_available():
            raise ImportError(
                "C++ phase-field extension not available. "
                "Build with: python setup_cpp_core.py build_ext --inplace"
            )
        return "cpp"
    if key == "auto":
        return "cpp" if cpp_extension_available() else "numpy"
    raise ValueError("backend must be 'numpy', 'cpp', or 'auto'")


class PhaseFieldSolver(Solver):
    """
    Periodic 1D Cahn–Hilliard evolution for a scalar order parameter φ(x).

    Semi-implicit Fourier spectral update (educational toy):
      φ_t = M ∂xx ( φ³ − (1+α)φ − ε² φ_xx )
    """

    name = "phase_field"

    def solve(self, sim_input: SimulationInput) -> SimulationOutput:
        sim_input.validate()
        rng = np.random.default_rng(sim_input.random_seed)

        n = int(sim_input.n_grid)
        L = float(sim_input.box_length)
        dx = L / n
        dt = float(sim_input.timestep)
        n_steps = int(sim_input.n_iterations)

        eps2 = float(sim_input.settings.get("epsilon_sq", 4.0e-3))
        mobility = float(sim_input.settings.get("mobility", 1.0))
        noise_amp = float(sim_input.settings.get("noise_amplitude", 0.01))
        alpha = float(
            sim_input.settings.get(
                "alpha",
                min(0.8, 0.005 * float(sim_input.chiN)),
            )
        )
        update_tol = float(sim_input.settings.get("update_tol", 1.0e-6))
        backend = resolve_backend(str(sim_input.settings.get("backend", "auto")))

        f = sim_input.volume_fractions[0]
        mean_phi = 2.0 * f - 1.0
        phi0 = mean_phi + noise_amp * rng.standard_normal(n)
        phi0 = np.clip(phi0, -1.5, 1.5)

        if backend == "cpp":
            if n & (n - 1) != 0:
                raise ValueError("C++ backend requires n_grid to be a power of two")
            phi, energy_history, max_update = evolve_cpp(
                phi0, dx=dx, dt=dt, n_steps=n_steps, eps2=eps2, mobility=mobility, alpha=alpha
            )
            integrator = "C++ semi-implicit spectral (pybind11 kernel)"
        else:
            phi, energy_history, max_update = evolve_numpy(
                phi0, dx=dx, dt=dt, n_steps=n_steps, eps2=eps2, mobility=mobility, alpha=alpha
            )
            integrator = "NumPy semi-implicit spectral (default fallback)"

        amp = float(np.max(phi) - np.min(phi))
        if not np.isfinite(amp):
            toy_morph = "toy-unstable (non-finite field)"
            success = False
        elif amp < 0.20:
            toy_morph = "toy-mixed (weak order-parameter contrast)"
            success = True
        else:
            signs = np.sign(phi - np.mean(phi))
            crossings = int(np.sum(signs * np.roll(signs, -1) < 0))
            periods = max(crossings // 2, 1)
            toy_morph = f"toy-segregated (approx. {periods} period(s) in 1D)"
            success = True

        final_energy = energy_history[-1] if energy_history else float("nan")
        converged = bool(np.isfinite(max_update) and max_update < update_tol)

        method_details: dict[str, Any] = {
            "method": "1D periodic Cahn–Hilliard (semi-implicit Fourier; toy)",
            "equation": "φ_t = M ∂xx(φ³ - (1+α)φ - ε² φ_xx)",
            "time_integrator": integrator,
            "backend": backend,
            "cpp_extension_available": cpp_extension_available(),
            "grid_size": n,
            "box_length": L,
            "dx": dx,
            "timestep": dt,
            "n_iterations": n_steps,
            "random_seed": sim_input.random_seed,
            "epsilon_sq": eps2,
            "mobility": mobility,
            "alpha(χN-linked)": alpha,
            "noise_amplitude": noise_amp,
            "numpy_version": np.__version__,
            "cpp_numpy_agreement_tol": CPP_NUMPY_AGREEMENT_TOL,
        }

        return SimulationOutput(
            solver_name=self.name,
            morphology=toy_morph,
            energy=final_energy,
            chiN=sim_input.chiN,
            structure={
                "order_parameter_phi": phi.tolist(),
                "x": (np.arange(n) * dx).tolist(),
                "phi_min": float(np.min(phi)),
                "phi_max": float(np.max(phi)),
                "phi_amplitude": amp,
                "mean_phi": float(np.mean(phi)),
            },
            convergence={
                "iterations": n_steps,
                "final_max_abs_update": max_update,
                "energy_samples": energy_history,
                "apparently_converged": converged,
                "criterion": "max|Δφ| < update_tol at final step (soft check)",
            },
            method_details=method_details,
            assumptions=[
                "Scalar 1D order parameter; no chain connectivity / SCFT Hamiltonian.",
                "Periodic boundaries; no defects or 2D/3D morphologies.",
                "α is a crude stand-in for segregation strength, not a fitted χ model.",
                "C++ accelerates only the timestep kernel; Python owns I/O and analysis.",
            ],
            notes=[
                "TOY NUMERICAL DEMONSTRATION ONLY — not a quantitative polymer morphology prediction.",
                "Do not interpret 'toy-segregated' as lamellae/cylinders/gyroid from polymer theory.",
            ],
            success=success,
        )
