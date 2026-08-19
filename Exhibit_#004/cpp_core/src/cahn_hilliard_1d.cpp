#include "cahn_hilliard_1d.hpp"

#include <algorithm>
#include <cmath>
#include <complex>
#include <stdexcept>
#include <vector>

namespace polymer_cpp {
namespace {

using Complex = std::complex<double>;
constexpr double PI = 3.14159265358979323846;

bool is_power_of_two(int n) {
    return n > 0 && (n & (n - 1)) == 0;
}

// In-place Cooley–Tukey FFT. invert=false: forward (numpy.fft.fft convention unnormalized).
// invert=true: inverse without 1/n (caller divides).
void fft_radix2(std::vector<Complex>& a, bool invert) {
    const int n = static_cast<int>(a.size());
    if (!is_power_of_two(n)) {
        throw std::invalid_argument("FFT size must be a power of two");
    }
    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) {
            j ^= bit;
        }
        j ^= bit;
        if (i < j) {
            std::swap(a[i], a[j]);
        }
    }
    for (int len = 2; len <= n; len <<= 1) {
        const double ang = 2.0 * PI / len * (invert ? 1.0 : -1.0);
        const Complex wlen(std::cos(ang), std::sin(ang));
        for (int i = 0; i < n; i += len) {
            Complex w(1.0, 0.0);
            for (int j = 0; j < len / 2; ++j) {
                Complex u = a[i + j];
                Complex v = a[i + j + len / 2] * w;
                a[i + j] = u + v;
                a[i + j + len / 2] = u - v;
                w *= wlen;
            }
        }
    }
    if (invert) {
        for (auto& x : a) {
            x /= static_cast<double>(n);
        }
    }
}

std::vector<double> fftfreq_hz(int n, double dx) {
    // Match numpy.fft.fftfreq(n, d=dx)
    std::vector<double> freq(n);
    const double inv = 1.0 / (n * dx);
    for (int i = 0; i < n; ++i) {
        int v = (i < (n + 1) / 2) ? i : i - n;
        freq[i] = v * inv;
    }
    return freq;
}

}  // namespace

EvolveResult evolve_cahn_hilliard_1d(
    const std::vector<double>& phi0,
    double dx,
    double dt,
    int n_steps,
    double eps2,
    double mobility,
    double alpha
) {
    const int n = static_cast<int>(phi0.size());
    if (n < 8) {
        throw std::invalid_argument("n_grid must be >= 8");
    }
    if (!is_power_of_two(n)) {
        throw std::invalid_argument(
            "C++ phase-field kernel requires n_grid to be a power of two"
        );
    }
    if (dx <= 0.0 || dt <= 0.0 || n_steps < 1) {
        throw std::invalid_argument("invalid dx/dt/n_steps");
    }

    std::vector<double> phi = phi0;
    for (double& v : phi) {
        v = std::clamp(v, -1.5, 1.5);
    }

    const auto freq = fftfreq_hz(n, dx);
    std::vector<double> k2(n);
    std::vector<double> denom(n);
    for (int i = 0; i < n; ++i) {
        const double k = 2.0 * PI * freq[i];
        k2[i] = k * k;
        denom[i] = 1.0 + dt * mobility * eps2 * (k2[i] * k2[i]);
    }

    EvolveResult result;
    result.energy_history.reserve(32);
    double max_update = 0.0;

    auto sample_energy = [&](const std::vector<double>& field) {
        double e = 0.0;
        for (int i = 0; i < n; ++i) {
            const double p = field[i];
            const double p_next = field[(i + 1) % n];
            const double bulk = 0.25 * (p * p - 1.0) * (p * p - 1.0) - 0.5 * alpha * p * p;
            const double gp = (p_next - p) / dx;
            const double grad = 0.5 * eps2 * gp * gp;
            e += (bulk + grad) * dx;
        }
        return e;
    };

    for (int step = 0; step < n_steps; ++step) {
        std::vector<Complex> phi_hat(n), mu_hat(n);
        for (int i = 0; i < n; ++i) {
            const double p = phi[i];
            const double mu_nl = p * p * p - (1.0 + alpha) * p;
            phi_hat[i] = Complex(p, 0.0);
            mu_hat[i] = Complex(mu_nl, 0.0);
        }
        fft_radix2(phi_hat, false);
        fft_radix2(mu_hat, false);

        std::vector<Complex> phi_new_hat(n);
        for (int i = 0; i < n; ++i) {
            phi_new_hat[i] =
                (phi_hat[i] - dt * mobility * k2[i] * mu_hat[i]) / denom[i];
        }
        fft_radix2(phi_new_hat, true);

        max_update = 0.0;
        std::vector<double> phi_new(n);
        for (int i = 0; i < n; ++i) {
            double v = phi_new_hat[i].real();
            v = std::clamp(v, -1.5, 1.5);
            max_update = std::max(max_update, std::abs(v - phi[i]));
            phi_new[i] = v;
        }
        phi.swap(phi_new);

        const int stride = std::max(1, n_steps / 20);
        if (step % stride == 0 || step == n_steps - 1) {
            result.energy_history.push_back(sample_energy(phi));
        }
    }

    result.phi = std::move(phi);
    result.max_update = max_update;
    return result;
}

}  // namespace polymer_cpp
