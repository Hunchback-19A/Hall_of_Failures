#pragma once

#include <utility>
#include <vector>

namespace polymer_cpp {

struct EvolveResult {
    std::vector<double> phi;
    std::vector<double> energy_history;
    double max_update = 0.0;
};

/**
 * Semi-implicit 1D periodic Cahn–Hilliard evolution matching the Python toy solver:
 *   φ_t = M ∂xx ( φ³ − (1+α)φ − ε² φ_xx )
 * Linear biharmonic term treated implicitly in Fourier space.
 *
 * Initial φ is provided by the caller (Python) for reproducibility with NumPy RNG.
 */
EvolveResult evolve_cahn_hilliard_1d(
    const std::vector<double>& phi0,
    double dx,
    double dt,
    int n_steps,
    double eps2,
    double mobility,
    double alpha
);

}  // namespace polymer_cpp
