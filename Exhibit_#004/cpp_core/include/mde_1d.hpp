#pragma once

#include <utility>
#include <vector>

namespace polymer_cpp {

struct MDEResult {
    std::vector<double> q;          // (n_contour+1) * n_grid, row-major in s
    std::vector<double> q_dagger;
    double Q = 0.0;
    int n_contour = 0;
    int n_grid = 0;
};

/**
 * 1D periodic AB diblock MDE (Gaussian chain), matching the NumPy Strang+FFT
 * propagator in polymer_engine.solvers.scft.propagator.
 *
 * Contour s ∈ [0,1]; lengths in R_g units.
 * Extension point: future ABC / 2D–3D solvers should keep this kernel 1D-only
 * and compose higher architectures in Python.
 */
MDEResult propagate_diblock_mde_1d(
    const std::vector<double>& w_A,
    const std::vector<double>& w_B,
    double f_A,
    double box_length,
    int n_contour
);

}  // namespace polymer_cpp
