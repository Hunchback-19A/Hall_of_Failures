# SCFT MDE C++ extension (optional)

## What is implemented now

Optional pybind11 module `polymer_engine._scft_mde_cpp` accelerates the **1D AB
diblock** modified diffusion equation (Strang + FFT), matching the NumPy
propagator in `polymer_engine/solvers/scft/propagator.py`.

Build from project root (C++17 + pybind11):

```
pip install pybind11 numpy
python setup_cpp_core.py build_ext --inplace
```

Select backend in SCFT settings:

- `propagator_backend`: `"numpy"` | `"cpp"` | `"auto"` (default `auto`)
- NumPy remains the default *install* path; C++ is optional.

Agreement target vs NumPy: max |q − q_cpp| ≲ 1e-10 on power-of-two grids.

## What is deliberately left for future field users

Keep complex architecture out of this educational core:

- ABC / multiblock / blend SCFT models
- 2D / 3D grids and classical morphologies (cylinders, gyroid, BCC, …)
- Full multi-parameter unit-cell optimization suites

Hooks already present:

- Python owns the outer SCFT self-consistency loop
- `unit_cell.scan_box_lengths(evaluate_F, lengths)` is a generic 1D L-scan;
  swap `evaluate_F` later for 2D/3D cell metrics
- C++ kernel stays 1D AB-only (`cpp_core/include/mde_1d.hpp`)

Do not move the SCFT outer loop into C++ for the educational package.
