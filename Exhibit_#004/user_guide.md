# User Guide — Block Copolymer Self-Assembly Design Prototype

This guide is written for two audiences:

| Audience | What you will find here |
|----------|-------------------------|
| **Polymer scientists & materials professionals** | What the software *means* physically, what it can and cannot claim, and which knobs map to χ, χN, morphology, and domain spacing — with or without writing code. |
| **Programmers & computational researchers** | Package layout, CLI commands, how to extend solvers. For packaging on GitHub, see `github_release_checklist.txt`. |

**Project status:** educational / research prototype (local, open, explainable). It is **not** a commercial SCFT package and **not** a black-box AI design tool.

---

## 1. In one sentence

You describe a block copolymer (composition, χ or χ-estimate, chain length *N*), and the software returns **traceable** predictions of segregation strength (χN), classical morphology class, free-energy proxies, approximate domain spacing, and (optionally) simple numerical simulations — always with assumptions and limitations written out.

---

## 2. What this is — and what it is not

### What it is

- A **physics-first** teaching and exploration tool for **AB diblock** (and limited triblock) self-assembly ideas.
- Modular code: thermodynamics → morphology → energetics → structure → solvers → reports.
- Transparent numerics: NumPy by default; optional C++ only for speed-critical kernels.
- Scientific-style reports that separate **Interpretation** from **Reason** (why the claim was made).

### What it is not

- Not a substitute for experiment, calibrated SCFT for process design, or DSA lithography workflows.
- The **toy 1D phase-field** solver does **not** predict real lamellae / cylinders / gyroid.
- The **minimal SCFT** solver is **1D AB only** (density waves along a line). It does not resolve 3D morphologies.
- Inverse “design” here means **ranked exploration of local monomer grids**, not industrial formulation optimization.

If you need production SCFT (2D/3D cells, ABC, DSA masks), treat this repository as a **starting architecture** and see §7 for deliberate extension points.

---

## 3. Polymer-science concepts used by the software

These are the quantities professionals already know; the code uses the same language.

| Symbol / term | Meaning in this tool |
|---------------|----------------------|
| **Architecture** | `diblock` or `triblock` (SCFT core: diblock only). |
| **Volume fraction *f*** | Composition of block A (and 1−*f* for B). Classical phase windows depend strongly on *f*. |
| **Flory–Huggins χ** | Unlike-contact interaction strength (constant, *T*-dependent, or solubility estimate). |
| **Degree of polymerization *N*** | Chain length entering segregation strength. |
| **χN** | Product χ × *N*; main control of order vs disorder. |
| **ODT (mean-field, symmetric diblock)** | Reference threshold **χN ≈ 10.495**. Below ≈ disordered; above ≈ ordered tendency (educational map). |
| **Morphology (analytical path)** | Rule-based classical map: spheres → cylinders → gyroid → lamellae with minority fraction (when ordered). |
| **Domain spacing *D*** | Scaling estimates (weak segregation / Leibler-style peak; strong segregation *D* ~ χ¹⁄⁶ *N*²⁄³). Default segment length *a* = 0.5 nm unless changed. |
| **SCFT (minimal)** | Mean-field Gaussian-chain SCFT in a **1D periodic box**; reports density modulation amplitude, free-energy terms, and optional box-length scan. |

**How to read outputs as a professional**

1. Check **χN** vs **~10.5** first (segregation regime).
2. Treat **analytical morphology** as an *educational classical map*, not a fitted experimental phase diagram for your chemistry.
3. Treat **SCFT “modulated”** as *1D microphase tendency*, not “gyroid predicted.”
4. Read every **Assumptions / Notes** block before comparing to SAXS, TEM, or rheology.

---

## 4. What the scripts and packages do

### 4.1 Layout (project root)

```text
Block co-polymer design/
├── polymer_design/     # CLI app, polymer JSON, inverse design, benchmarks runner
├── polymer_engine/     # Physics core (χ, morphology, energy, structure, solvers, reporting)
├── benchmarks/         # Local morphology fixtures (PS-b-PMMA, PS-b-PEO, PI-b-PS)
├── cpp_core/           # Optional C++ kernels (phase-field timestep + SCFT MDE)
├── tests/              # Unit tests
├── requirements.txt
├── setup_cpp_core.py   # Optional: build C++ extensions
├── user_guide.md       # This file
└── github_release_checklist.txt
```

### 4.2 `polymer_design` — the application layer

| Piece | Role |
|-------|------|
| `main.py` / `python -m polymer_design` | Command-line interface (see §5). |
| `polymer.py` + `data/polymers.json`, `data/monomers.json` | Load polymer definitions and monomer library. |
| `evaluator.py` | Runs the simplified physics evaluation (χN, morphology, energy proxy, domain size). |
| `design/` | Inverse design: target → candidate grid → rank → report. |
| `validation/` | Compare predictions to local `benchmarks/*.json` (no web scraping). |
| `optimization/` | Thin wrappers for random search, PSO, and MCTS (stubs / educational explorers). |
| `visualization/console_display.py` | Pretty-prints evaluation reports in the terminal. |

### 4.3 `polymer_engine` — the physics core

| Module | Role for professionals | Role for programmers |
|--------|------------------------|----------------------|
| `thermodynamics/` | χN, ODT constant, χ(*T*), solubility χ | `flory_huggins.py`, `chi_models.py` |
| `morphology/` | Classical phase-map prediction | `phase_map.py`, `morphology_prediction.py` |
| `energetics/` | Mixing / interface / stretching-style contributions (proxy) | `contributions.py`, `free_energy.py` |
| `structure/` | *R_g* and domain-spacing scaling | `domain_size.py` |
| `solvers/` | Pluggable solvers behind one I/O contract | `SimulationInput` / `SimulationOutput` |
| `solvers/scft/` | Minimal 1D AB SCFT | fields → MDE → density → free energy → mix |
| `reporting/` | Scientific interpretation with reasons | `interpretation.py`, `scientific_report.py` |

**Solvers currently registered**

| Name | Status | What a professional should expect |
|------|--------|-----------------------------------|
| `analytical` | Implemented | Rule-based / scaling evaluation (same spirit as `evaluate`). |
| `phase_field` | Implemented (toy) | 1D Cahn–Hilliard demo; **toy labels only**. |
| `scft` | Implemented (minimal) | 1D AB mean-field SCFT; density wave + free energy. |
| `monte_carlo` | Placeholder | Raises `NotImplementedError` (interface reserved). |

### 4.4 Optional C++ (`cpp_core/`)

Default installs need only NumPy. If you have a C++17 compiler and `pybind11`:

```text
pip install pybind11 numpy
python setup_cpp_core.py build_ext --inplace
```

| Extension | Accelerates |
|-----------|-------------|
| `polymer_engine._phase_field_cpp` | Toy phase-field timestep |
| `polymer_engine._scft_mde_cpp` | SCFT chain propagator (1D AB MDE) |

Missing C++ → automatic NumPy fallback (`auto` backend).

---

## 5. Getting started

### 5.1 Requirements

- Python 3.10+ recommended (tested with modern CPython).
- Install:

```text
pip install -r requirements.txt
```

Optional C++ build: see §4.4.

### 5.2 Where to run commands

From the **project root** (folder that contains `polymer_design/` and `polymer_engine/`):

```text
python -m polymer_design list
python -m polymer_design evaluate --polymer PS-b-PMMA
```

Or from inside `polymer_design/`:

```text
python main.py list
python main.py evaluate --polymer PS-b-PMMA
```

### 5.3 Commands (what each does)

| Command | For professionals | Example |
|---------|-------------------|---------|
| `list` | Show polymers in the library | `python -m polymer_design list` |
| `evaluate` | χN, morphology, energy proxy, domain spacing | `python -m polymer_design evaluate --polymer PS-b-PMMA` |
| `validate` | Run local morphology fixtures | `python -m polymer_design validate` |
| `design` | Rank candidates toward a target morphology / spacing | `python -m polymer_design design --target-morphology lamellae --top 5` |
| `search` | Simple random / PSO / MCTS exploration wrappers | `python -m polymer_design search --method random --n 20` |
| `simulate` | Numerical / analytical solvers with scientific report | `python -m polymer_design simulate --solver scft --chi 0.1 --N 200 --f 0.5 --box 4 --iterations 80` |
| `example-json` | Print a polymer JSON template | `python -m polymer_design example-json` |

**Useful `evaluate` options**

- `--all` — evaluate every library polymer  
- `--file path.json` — evaluate your own JSON  
- `--brief` — shorter console output  

**Useful `simulate` options**

- `--solver analytical | phase_field | scft | monte_carlo`
- `--list-solvers` — status of each solver  
- `--f`, `--chi`, `--N`, `--box`, `--n-grid`, `--iterations`, `--seed`  
- `--backend auto|numpy|cpp` (phase-field; SCFT uses `settings["propagator_backend"]` when called from Python)

**SCFT tips for professionals**

- Prefer **power-of-two** `--n-grid` (32, 64, …) if using the C++ propagator.
- Low χN (e.g. 5): expect weak / homogeneous density.  
- High χN (e.g. 25): expect stronger 1D modulation.  
- Optional box scan (Python API): `settings={"optimize_box": True, "box_lengths": [3.5, 4.5, 5.5]}` minimizes free energy over 1D cell lengths *L* only.

### 5.4 Defining your own polymer (no deep coding)

Save a JSON file, then:

```text
python -m polymer_design evaluate --file my_polymer.json
```

Minimal example:

```json
{
  "name": "PS-b-PMMA",
  "architecture": "diblock",
  "blocks": [
    {"name": "styrene", "fraction": 0.5},
    {"name": "MMA", "fraction": 0.5}
  ],
  "parameters": {
    "chi": 0.04,
    "degree_of_polymerization": 100
  }
}
```

`fraction` values should sum to 1. χ may be omitted if you rely on monomer solubility estimates (when those data exist in `monomers.json`).

### 5.5 Tests (programmers)

From project root:

```text
python -m unittest discover -s tests
```

---

## 6. Typical workflows

### A. Quick morphology / χN check (most professionals start here)

1. Add or pick a polymer JSON.  
2. `evaluate` and read χN vs ~10.5, morphology label, and domain spacing.  
3. Optional: `validate` to see how the educational map behaves on the bundled fixtures.

### B. Inverse exploration toward a target

1. Choose target morphology and/or domain spacing.  
2. `design --target-morphology … --spacing … --top 5`.  
3. Inspect ranked candidates and score breakdown (composition, χN window, spacing error).

### C. Numerical segregation demo

1. `simulate --solver phase_field …` for a **toy** order-parameter movie in 1D.  
2. Or `simulate --solver scft …` for **mean-field chain** physics in 1D.  
3. Always read the scientific report’s Interpretation + Reason lines.

---

## 7. Features you (or future field users) can add

These are intentional extension points — kept out of the educational core so ABC / 2D–3D work stays with people who need it.

### For polymer scientists collaborating with developers

| Desired capability | Where to extend | Notes |
|--------------------|-----------------|-------|
| Chemistry-specific χ(*T*) databases | `polymer_engine/thermodynamics/chi_models.py` | Keep models explicit; avoid silent scraping. |
| Better classical phase boundaries | `morphology/phase_map.py` | Document fit source (Matsen-type maps, your SAXS, etc.). |
| Calibrated domain spacing | `structure/domain_size.py` | Replace default *a* and exponents with your chemistry. |
| True 2D/3D SCFT morphologies | New modules under `solvers/scft/` | Keep current 1D AB path intact. |
| ABC / multiblock / blends | New specs beside `DiblockSCFTSpec` | Do not overload the diblock validator. |
| DSA / thin-film confinement | New solver + fields | Not implemented; would need dedicated thin-film / mask models. |
| Production inverse design (PSO+SCFT) | Replace educational PSO/MCTS wrappers | Case et al. / Patra et al. informed the *optimizer ≠ simulator* idea; wrappers here remain lightweight. |
| Monte Carlo chain simulations | `solvers/monte_carlo.py` | Interface exists; physics not implemented. |

### For programmers (concrete hooks)

1. **New χ model** — subclass `ChiModel` and wire into the evaluator.  
2. **New free-energy term** — implement a contribution and register it in the energetics proxy.  
3. **New solver** — implement `Solver.solve(SimulationInput) → SimulationOutput`, register in `solvers/registry.py`.  
4. **Faster MDE** — already optional via `_scft_mde_cpp`; keep the outer SCFT loop in Python.  
5. **Unit-cell metrics** — reuse `unit_cell.scan_box_lengths(evaluate_F, lengths)` with a 2D/3D `evaluate_F` later.  
6. **Benchmarks** — add JSON under `benchmarks/` with honest `expected.morphology` and optional real citations (never invent references).

**Design principle:** prefer small, auditable modules over one opaque “AI” predictor.

---

## 8. References (APA)

Case, L. J., Delaney, K. T., Fredrickson, G. H., Bates, F. S., & Dorfman, K. D. (2021). Open-source platform for block polymer formulation design using particle swarm optimization. *The European Physical Journal E*, *44*(9), Article 115. https://doi.org/10.1140/epje/s10189-021-00123-9  
*Used for:* keeping the optimizer separate from the physics evaluator (candidate generation + external scoring); informed `polymer_design/optimization/pso.py`.

Fredrickson, G. H. (2006). *The equilibrium theory of inhomogeneous polymers*. Oxford University Press. https://doi.org/10.1093/acprof:oso/9780198567295.001.0001  
*Used for:* free-energy minimization as the organizing idea; SCFT philosophy (fields / order parameters); later conceptual basis for the educational 1D SCFT modules under `polymer_engine/solvers/scft/`.

Hadjichristidis, N., Pispas, S., & Floudas, G. (2003). *Block copolymers: Synthetic strategies, physical properties, and applications*. John Wiley & Sons.  
*Used for:* chemically meaningful polymer descriptions — diblock / triblock architectures and example chemistries reflected in the JSON polymer schema and monomer library.

Patra, T. K., Loeffler, T. D., & Sankaranarayanan, S. K. R. S. (2020). Accelerating copolymer inverse design using Monte Carlo tree search. *Nanoscale*. Advance online publication. https://doi.org/10.1039/d0nr06091g  
*Used for:* hierarchical design-space search with an external scorer; informed `polymer_design/optimization/mcts.py`.

The educational ODT constant χN ≈ 10.495 for a symmetric diblock melt (hard-coded in `polymer_engine/thermodynamics/flory_huggins.py`) is the standard mean-field Leibler result common in polymer physics texts; it is used here as a transparent reference, not as a chemistry-specific fit.

---

## 9. Packaging for GitHub

For a printable step-by-step release checklist (what to include, what to omit, website steps, release-notes skeleton), see:

**`github_release_checklist.txt`**

---

## 10. Quick glossary

| Term | Plain meaning |
|------|----------------|
| **χN** | Segregation strength (χ times *N*). |
| **ODT** | Order–disorder transition; educational reference ~10.5 for symmetric diblocks. |
| **SCFT** | Self-consistent field theory; here a small 1D mean-field implementation. |
| **MDE** | Modified diffusion equation for the chain propagator *q*. |
| **WSL / SSL** | Weak / strong segregation limits used in spacing estimates. |
| **Backend** | NumPy vs optional C++ for a numerical kernel. |

---

*End of user guide.* For questions about physical interpretation, start from the console report’s Assumptions and Reasons; for code changes, start from `polymer_engine/solvers/` and keep new architectures in separate modules.
