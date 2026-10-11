#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "cahn_hilliard_1d.hpp"

namespace py = pybind11;

PYBIND11_MODULE(_phase_field_cpp, m) {
    m.doc() = "Optional C++ kernel for 1D toy Cahn–Hilliard timesteps";

    py::class_<polymer_cpp::EvolveResult>(m, "EvolveResult")
        .def_readonly("phi", &polymer_cpp::EvolveResult::phi)
        .def_readonly("energy_history", &polymer_cpp::EvolveResult::energy_history)
        .def_readonly("max_update", &polymer_cpp::EvolveResult::max_update);

    m.def(
        "evolve_cahn_hilliard_1d",
        &polymer_cpp::evolve_cahn_hilliard_1d,
        py::arg("phi0"),
        py::arg("dx"),
        py::arg("dt"),
        py::arg("n_steps"),
        py::arg("eps2"),
        py::arg("mobility"),
        py::arg("alpha"),
        "Evolve φ with the semi-implicit spectral Cahn–Hilliard toy kernel."
    );

    m.attr("kernel_name") = "cahn_hilliard_1d_semi_implicit_fft";
}
