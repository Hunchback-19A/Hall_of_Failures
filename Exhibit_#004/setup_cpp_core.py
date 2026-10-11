"""
Optional build for C++ kernels (pybind11).

Default package use does NOT require this build — NumPy fallbacks remain default.

Kernels:
  - polymer_engine._phase_field_cpp  (1D Cahn–Hilliard timestep)
  - polymer_engine._scft_mde_cpp     (1D AB-diblock MDE propagator)

Build (from project root, C++17 compiler required):

  pip install pybind11 numpy
  python setup_cpp_core.py build_ext --inplace
"""

from __future__ import annotations

from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

ROOT = Path(__file__).resolve().parent
CPP = ROOT / "cpp_core"

ext_modules = [
    Pybind11Extension(
        "polymer_engine._phase_field_cpp",
        [
            str(CPP / "src" / "cahn_hilliard_1d.cpp"),
            str(CPP / "src" / "bindings.cpp"),
        ],
        include_dirs=[str(CPP / "include")],
        cxx_std=17,
    ),
    Pybind11Extension(
        "polymer_engine._scft_mde_cpp",
        [
            str(CPP / "src" / "mde_1d.cpp"),
            str(CPP / "src" / "mde_bindings.cpp"),
        ],
        include_dirs=[str(CPP / "include")],
        cxx_std=17,
    ),
]

setup(
    name="polymer-engine-cpp-core",
    version="0.2.0",
    description="Optional C++ kernels for polymer_engine (phase-field + SCFT MDE)",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
