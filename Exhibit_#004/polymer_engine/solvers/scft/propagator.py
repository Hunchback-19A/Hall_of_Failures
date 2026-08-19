"""
Chain propagator (modified diffusion equation) for Gaussian chains.

Dimensionless MDE (s ∈ [0,1], lengths in R_g units):

    ∂q/∂s = ∇² q − w(r,s) q

Solved with Strang operator splitting + Fourier spectral Laplacian (1D PBC).

Backends:
  - numpy (default installation path)
  - cpp   (optional polymer_engine._scft_mde_cpp; power-of-two grids)
  - auto  (cpp if available else numpy)

Scope: 1D AB diblock only. ABC / 2D / 3D belong in future field-facing modules.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PropagatorResult:
    q: np.ndarray          # shape (Ns+1, Nx)
    q_dagger: np.ndarray   # shape (Ns+1, Nx)
    Q: float               # single-chain partition function
    backend: str


def mde_cpp_available() -> bool:
    try:
        from polymer_engine import _scft_mde_cpp  # noqa: F401

        return True
    except Exception:
        return False


def resolve_propagator_backend(requested: str) -> str:
    key = (requested or "auto").lower().strip()
    if key == "numpy":
        return "numpy"
    if key == "cpp":
        if not mde_cpp_available():
            raise ImportError(
                "SCFT C++ MDE extension not available. "
                "Build with: python setup_cpp_core.py build_ext --inplace"
            )
        return "cpp"
    if key == "auto":
        return "cpp" if mde_cpp_available() else "numpy"
    raise ValueError("propagator_backend must be 'numpy', 'cpp', or 'auto'")


def _fftfreq_laplacian_factor(n: int, dx: float) -> np.ndarray:
    k = 2.0 * np.pi * np.fft.fftfreq(n, d=dx)
    return -(k**2)


def _diffusion_step(field: np.ndarray, lap_factor: np.ndarray, ds: float) -> np.ndarray:
    hat = np.fft.fft(field)
    hat *= np.exp(ds * lap_factor)
    return np.real(np.fft.ifft(hat))


def _potential_step(field: np.ndarray, w: np.ndarray, ds: float) -> np.ndarray:
    return field * np.exp(-ds * w)


def _strang_step(q: np.ndarray, w: np.ndarray, lap_factor: np.ndarray, ds: float) -> np.ndarray:
    q = _potential_step(q, w, 0.5 * ds)
    q = _diffusion_step(q, lap_factor, ds)
    q = _potential_step(q, w, 0.5 * ds)
    return q


def _w_at_contour(s: float, f_A: float, w_A: np.ndarray, w_B: np.ndarray) -> np.ndarray:
    return w_A if s < f_A else w_B


def propagate_diblock_1d(
    w_A: np.ndarray,
    w_B: np.ndarray,
    *,
    f_A: float,
    box_length: float,
    n_contour: int,
    backend: str = "auto",
) -> PropagatorResult:
    """
    Compute forward q(r,s) and complementary q†(r,s) for an AB diblock.

    q(r,0) = 1, integrate s: 0 → 1
    q†(r,1) = 1, integrate s: 1 → 0
    """
    resolved = resolve_propagator_backend(backend)
    if resolved == "cpp":
        return _propagate_cpp(w_A, w_B, f_A=f_A, box_length=box_length, n_contour=n_contour)
    return _propagate_numpy(w_A, w_B, f_A=f_A, box_length=box_length, n_contour=n_contour)


def _propagate_numpy(
    w_A: np.ndarray,
    w_B: np.ndarray,
    *,
    f_A: float,
    box_length: float,
    n_contour: int,
) -> PropagatorResult:
    nx = w_A.size
    dx = box_length / nx
    ns = int(n_contour)
    if ns < 10:
        raise ValueError("n_contour must be >= 10")
    ds = 1.0 / ns
    lap = _fftfreq_laplacian_factor(nx, dx)

    q = np.zeros((ns + 1, nx), dtype=float)
    q[0, :] = 1.0
    for i in range(ns):
        s_mid = (i + 0.5) * ds
        w = _w_at_contour(s_mid, f_A, w_A, w_B)
        q[i + 1, :] = _strang_step(q[i, :], w, lap, ds)

    q_dag = np.zeros((ns + 1, nx), dtype=float)
    q_dag[ns, :] = 1.0
    for i in range(ns, 0, -1):
        s_mid = (i - 0.5) * ds
        w = _w_at_contour(s_mid, f_A, w_A, w_B)
        q_dag[i - 1, :] = _strang_step(q_dag[i, :], w, lap, ds)

    volume = box_length
    Q_s = np.sum(q * q_dag, axis=1) * dx / volume
    Q = float(np.mean(Q_s))
    if Q <= 0 or not np.isfinite(Q):
        raise RuntimeError(f"Invalid single-chain partition function Q={Q}")

    return PropagatorResult(q=q, q_dagger=q_dag, Q=Q, backend="numpy")


def _propagate_cpp(
    w_A: np.ndarray,
    w_B: np.ndarray,
    *,
    f_A: float,
    box_length: float,
    n_contour: int,
) -> PropagatorResult:
    from polymer_engine import _scft_mde_cpp

    nx = int(w_A.size)
    if nx & (nx - 1) != 0:
        raise ValueError("C++ MDE requires n_grid to be a power of two")
    result = _scft_mde_cpp.propagate_diblock_mde_1d(
        np.asarray(w_A, dtype=float).tolist(),
        np.asarray(w_B, dtype=float).tolist(),
        float(f_A),
        float(box_length),
        int(n_contour),
    )
    ns = int(result.n_contour)
    nx = int(result.n_grid)
    q = np.asarray(result.q, dtype=float).reshape((ns + 1, nx))
    q_dag = np.asarray(result.q_dagger, dtype=float).reshape((ns + 1, nx))
    return PropagatorResult(q=q, q_dagger=q_dag, Q=float(result.Q), backend="cpp")
