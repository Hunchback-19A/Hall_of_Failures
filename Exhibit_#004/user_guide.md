# User Guide — Block Copolymer Self-Assembly Design Prototype

This guide is written for two audiences:

| Audience | What you will find here |
|----------|-------------------------|
| **Polymer scientists & materials professionals** | What the software *means* physically, what it can and cannot claim (§3 disclaimer), and which knobs map to χ, χN, morphology, and domain spacing — with or without writing code. |
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

If you need production SCFT (2D/3D cells, ABC, DSA masks), treat this repository as a **starting architecture** and see §8 for deliberate extension points.

Please also read **§3** before treating any prediction as a physical, biological, or materials-design conclusion.

---

## 3. Scope, models, and responsibility (disclaimer)

This section states how far the software’s claims are meant to go. It is part of the scientific framing of the tool, not optional fine print.

### 3.1 Directed self-assembly is one mechanism of organization, not the definition of Nature

Self-assembly provides a powerful way to understand how molecular interactions can produce organized structures. However, the existence and behavior of biological systems cannot be reduced to directed self-assembly alone.

A biological system is not simply a collection of molecules arranged into a desired structure. It is a dynamic network involving energy consumption, information storage, regulation, adaptation, evolution, environmental interaction, and many other processes across different scales.

Therefore, designing a polymer morphology or predicting molecular organization with this software should not be interpreted as reproducing the complexity of living systems.

**Practical implication:** A successful prediction of self-assembly does not mean a material is biologically functional, safe, or equivalent to a natural structure.

### 3.2 Computational models are approximations of discovered patterns, not complete descriptions of Nature

The equations and assumptions implemented here are mathematical descriptions created to capture specific behaviors observed in physical systems. They are useful because they simplify reality into a form that can be analyzed and tested.

However, every model has boundaries. Parameters, assumptions, numerical approximations, and omitted variables influence the accuracy and applicability of predictions.

No single theoretical framework can represent the entire universe. Scientific progress occurs by developing models that describe different aspects of reality and by understanding when each model is appropriate.

**Practical implication:** A model output from this tool should always be treated as a prediction or hypothesis requiring interpretation and validation, not as an absolute statement of what Nature must do.

### 3.3 Higher-level theories do not replace the fundamental processes that create them

The emergence of self-assembled structures does not remove the underlying physical and chemical mechanisms responsible for their existence.

Copolymer synthesis, molecular interactions, and material formation still depend on fundamental principles such as electronic structure, chemical bonding, electromagnetic interactions, thermodynamics, and molecular motion.

A mesoscale model describing domains, phases, or morphologies — including the educational morphology maps and SCFT modules in this repository — is not a replacement for chemistry. It is a higher-level description built upon the behavior of atoms and molecules.

**Practical implication:** Understanding a pattern at one scale does not mean the lower-scale mechanisms have disappeared. A successful self-assembly prediction remains dependent on the chemistry that produced the molecules.

### 3.4 Designing biologically inspired materials requires responsibility beyond molecular design

The ability to design self-assembling materials may inspire visions of increasingly complex biological applications, such as artificial tissues, synthetic blood-like materials, or engineered structures that resemble components of living organisms. However, the organization of molecules into a designed material is not equivalent to the creation of life or the complete recreation of biological systems.

Living systems are not defined only by their physical structures. They depend on complex interactions involving metabolism, genetic information, cellular communication, repair mechanisms, evolution, and continuous exchange with their environment. A material that imitates one function or structure of biology does not automatically possess the properties, behaviors, or responsibilities associated with a living system.

As computational and experimental tools advance, the question is not only whether humans can design increasingly complex materials, but also whether we understand the systems we are attempting to influence and whether we are prepared to responsibly manage the outcomes.

These questions have been explored for centuries in literature, including [Mary Shelley’s 1818 novel *Frankenstein; or, The Modern Prometheus*](https://www.gutenberg.org/files/41445/41445-h/41445-h.htm). The story is not a warning against discovery itself, but a reflection on the responsibilities that accompany the ability to create.

**Practical implication:** A successful self-assembly prediction or the creation of a biologically inspired material should not be interpreted as the creation of a living entity or a complete biological replacement. Progress in this field requires both technical capability and careful consideration of the systems being approached.

---

## 4. Polymer-science concepts used by the software

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

## 5. What the scripts and packages do

### 5.1 Layout (project root)

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

### 5.2 `polymer_design` — the application layer

| Piece | Role |
|-------|------|
| `main.py` / `python -m polymer_design` | Command-line interface (see §6). |
| `polymer.py` + `data/polymers.json`, `data/monomers.json` | Load polymer definitions and monomer library. |
| `evaluator.py` | Runs the simplified physics evaluation (χN, morphology, energy proxy, domain size). |
| `design/` | Inverse design: target → candidate grid → rank → report. |
| `validation/` | Compare predictions to local `benchmarks/*.json` (no web scraping). |
| `optimization/` | Thin wrappers for random search, PSO, and MCTS (stubs / educational explorers). |
| `visualization/console_display.py` | Pretty-prints evaluation reports in the terminal. |

### 5.3 `polymer_engine` — the physics core

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

### 5.4 Optional C++ (`cpp_core/`)

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

## 6. Getting started

### 6.1 Requirements

- Python 3.10+ recommended (tested with modern CPython).
- Install:

```text
pip install -r requirements.txt
```

Optional C++ build: see §5.4.

### 6.2 Where to run commands

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

### 6.3 Commands (what each does)

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

### 6.4 Defining your own polymer (no deep coding)

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

### 6.5 Tests (programmers)

From project root:

```text
python -m unittest discover -s tests
```

---

## 7. Typical workflows

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

## 8. Features you (or future field users) can add

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

## 9. References (APA)

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

## 10. Packaging for GitHub

For a printable step-by-step release checklist (what to include, what to omit, website steps, release-notes skeleton), see:

**`github_release_checklist.txt`**

---

## 11. Quick glossary

| Term | Plain meaning |
|------|----------------|
| **χN** | Segregation strength (χ times *N*). |
| **ODT** | Order–disorder transition; educational reference ~10.5 for symmetric diblocks. |
| **SCFT** | Self-consistent field theory; here a small 1D mean-field implementation. |
| **MDE** | Modified diffusion equation for the chain propagator *q*. |
| **WSL / SSL** | Weak / strong segregation limits used in spacing estimates. |
| **Backend** | NumPy vs optional C++ for a numerical kernel. |

---

*End of user guide.* Start from §3 and the console report’s Assumptions and Reasons for physical interpretation; for code changes, start from `polymer_engine/solvers/` and keep new architectures in separate modules.

