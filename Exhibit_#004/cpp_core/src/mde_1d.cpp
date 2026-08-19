#include "mde_1d.hpp"

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

void fft_radix2(std::vector<Complex>& a, bool invert) {
    const int n = static_cast<int>(a.size());
    if (!is_power_of_two(n)) {
        throw std::invalid_argument("MDE FFT size must be a power of two");
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

std::vector<double> lap_factors(int n, double dx) {
    // Match numpy: k = 2π * fftfreq(n, d=dx); lap = -k²
    std::vector<double> lap(n);
    const double inv = 1.0 / (n * dx);
    for (int i = 0; i < n; ++i) {
        const int v = (i < (n + 1) / 2) ? i : i - n;
        const double k = 2.0 * PI * (v * inv);
        lap[i] = -(k * k);
    }
    return lap;
}

void potential_step(std::vector<double>& q, const std::vector<double>& w, double ds) {
    for (size_t i = 0; i < q.size(); ++i) {
        q[i] *= std::exp(-ds * w[i]);
    }
}

void diffusion_step(std::vector<double>& q, const std::vector<double>& lap, double ds) {
    const int n = static_cast<int>(q.size());
    std::vector<Complex> hat(n);
    for (int i = 0; i < n; ++i) {
        hat[i] = Complex(q[i], 0.0);
    }
    fft_radix2(hat, false);
    for (int i = 0; i < n; ++i) {
        hat[i] *= std::exp(ds * lap[i]);
    }
    fft_radix2(hat, true);
    for (int i = 0; i < n; ++i) {
        q[i] = hat[i].real();
    }
}

void strang_step(
    std::vector<double>& q,
    const std::vector<double>& w,
    const std::vector<double>& lap,
    double ds
) {
    potential_step(q, w, 0.5 * ds);
    diffusion_step(q, lap, ds);
    potential_step(q, w, 0.5 * ds);
}

const std::vector<double>& w_at_contour(
    double s,
    double f_A,
    const std::vector<double>& w_A,
    const std::vector<double>& w_B
) {
    return (s < f_A) ? w_A : w_B;
}

}  // namespace

MDEResult propagate_diblock_mde_1d(
    const std::vector<double>& w_A,
    const std::vector<double>& w_B,
    double f_A,
    double box_length,
    int n_contour
) {
    if (w_A.size() != w_B.size() || w_A.empty()) {
        throw std::invalid_argument("w_A and w_B must have equal nonempty size");
    }
    if (!(f_A > 0.0 && f_A < 1.0)) {
        throw std::invalid_argument("f_A must be in (0,1)");
    }
    if (box_length <= 0.0 || n_contour < 10) {
        throw std::invalid_argument("invalid box_length / n_contour");
    }
    const int nx = static_cast<int>(w_A.size());
    if (!is_power_of_two(nx)) {
        throw std::invalid_argument("C++ MDE requires n_grid power of two");
    }

    const int ns = n_contour;
    const double ds = 1.0 / ns;
    const double dx = box_length / nx;
    const auto lap = lap_factors(nx, dx);

    MDEResult out;
    out.n_contour = ns;
    out.n_grid = nx;
    out.q.assign(static_cast<size_t>(ns + 1) * nx, 0.0);
    out.q_dagger.assign(static_cast<size_t>(ns + 1) * nx, 0.0);

    auto row = [&](std::vector<double>& buf, int i) -> double* {
        return buf.data() + static_cast<size_t>(i) * nx;
    };

    // q(r,0) = 1
    for (int j = 0; j < nx; ++j) {
        row(out.q, 0)[j] = 1.0;
    }
    for (int i = 0; i < ns; ++i) {
        const double s_mid = (i + 0.5) * ds;
        const auto& w = w_at_contour(s_mid, f_A, w_A, w_B);
        std::vector<double> q(row(out.q, i), row(out.q, i) + nx);
        strang_step(q, w, lap, ds);
        std::copy(q.begin(), q.end(), row(out.q, i + 1));
    }

    // q†(r,1) = 1
    for (int j = 0; j < nx; ++j) {
        row(out.q_dagger, ns)[j] = 1.0;
    }
    for (int i = ns; i > 0; --i) {
        const double s_mid = (i - 0.5) * ds;
        const auto& w = w_at_contour(s_mid, f_A, w_A, w_B);
        std::vector<double> qd(row(out.q_dagger, i), row(out.q_dagger, i) + nx);
        strang_step(qd, w, lap, ds);
        std::copy(qd.begin(), qd.end(), row(out.q_dagger, i - 1));
    }

    // Q ≈ mean_s (1/V) ∫ q q† dr
    double Q_acc = 0.0;
    for (int i = 0; i <= ns; ++i) {
        double integ = 0.0;
        for (int j = 0; j < nx; ++j) {
            integ += row(out.q, i)[j] * row(out.q_dagger, i)[j];
        }
        Q_acc += integ * dx / box_length;
    }
    out.Q = Q_acc / (ns + 1);
    if (!(out.Q > 0.0) || !std::isfinite(out.Q)) {
        throw std::runtime_error("invalid Q from C++ MDE");
    }
    return out;
}

}  // namespace polymer_cpp
