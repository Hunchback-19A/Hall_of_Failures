#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "mde_1d.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_scft_mde_cpp, m) {
    m.doc() = "Optional C++ 1D AB-diblock MDE kernel for SCFT (extensible; not ABC/2D/3D)";

    py::class_<polymer_cpp::MDEResult>(m, "MDEResult")
        .def_readonly("q", &polymer_cpp::MDEResult::q)
        .def_readonly("q_dagger", &polymer_cpp::MDEResult::q_dagger)
        .def_readonly("Q", &polymer_cpp::MDEResult::Q)
        .def_readonly("n_contour", &polymer_cpp::MDEResult::n_contour)
        .def_readonly("n_grid", &polymer_cpp::MDEResult::n_grid);

    m.def(
        "propagate_diblock_mde_1d",
        &polymer_cpp::propagate_diblock_mde_1d,
        py::arg("w_A"),
        py::arg("w_B"),
        py::arg("f_A"),
        py::arg("box_length"),
        py::arg("n_contour"),
        "AB diblock 1D MDE Strang+FFT propagator (Gaussian chain)."
    );

    m.attr("kernel_name") = "diblock_mde_1d_strang_fft";
    m.attr("scope") = "1D AB diblock only; higher architectures belong in Python/field codes";
}
