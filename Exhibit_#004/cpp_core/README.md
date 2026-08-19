# Optional C++ acceleration kernels

Default runtime path remains pure NumPy — these builds are optional.

## Kernels

| Module | Role |
|--------|------|
| `polymer_engine._phase_field_cpp` | 1D Cahn–Hilliard timestep |
| `polymer_engine._scft_mde_cpp` | 1D AB-diblock SCFT MDE propagator |

See also `SCFT_MDE_EXTENSION.md` for SCFT scope and future-extension notes.

## Prerequisites

- C++17 compiler (MSVC on Windows, or clang/g++)
- Python packages: `pybind11`, `numpy`

## Build (from repository root)

```text
pip install pybind11 numpy
python setup_cpp_core.py build_ext --inplace
```

## Verify

```text
python -c "from polymer_engine import _phase_field_cpp; print(_phase_field_cpp.kernel_name)"
python -c "from polymer_engine import _scft_mde_cpp; print(_scft_mde_cpp.kernel_name)"
python -m unittest tests.test_phase8_cpp_kernel tests.test_scft_diblock -v
```

## Notes

- `n_grid` must be a power of two for C++ FFT kernels.
- Missing extensions: solvers fall back to NumPy (`backend` / `propagator_backend` = `auto`).
- Educational SCFT stays 1D AB; ABC / 2D–3D belong to future field-facing modules.
