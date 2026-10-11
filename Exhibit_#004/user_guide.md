# User Guide — Block Copolymer Self-Assembly Design Prototype

This guide is written for two audiences:

| Audience | What you will find here |
|----------|-------------------------|
| **Polymer scientists & materials professionals** | What the software *means* physically, what it can and cannot claim (§3 disclaimer), and which knobs map to χ, χN, morphology, and domain spacing — with or without writing code. |
| **Programmers & computational researchers** | Package layout, CLI commands, how to extend solvers. For packaging on GitHub, see `github_release_checklist.txt`. |

**Project status:** educational / research prototype (local, open, explainable). It is **not** a commercial SCFT package and **not** a black-box AI design tool.

---

## 1. In one sentence

You describe a block copolymer (composition, χ or χ-estimate, chain length *N*), and the software returns **traceable** predictions of segregation strength (χN), classical morphology class, free-energy proxies, approximate domain spacing, and (optionally) simple numerical simulations — always with assumptions and limitations written out. The `run` command files that answer as a report plus a JSON record (§6.4).

---

## 2. What this is — and what it is not

### What it is

- A **physics-first** teaching and exploration tool for **AB diblock** (and limited triblock) self-assembly ideas.
- Modular code: thermodynamics → morphology → energetics → structure → solvers → reports.
- Transparent numerics: NumPy by default; optional C++ only for speed-critical kernels.
- An optional periodic diblock check through University of Minnesota’s `pscf_rpc` (lamellae, hexagonal cylinders, gyroid, BCC). On Windows that program is `third_party/pscfpp/bin/pscf_rpc.exe`.
- Scientific-style reports that separate **Interpretation** from **Reason** (why the claim was made).
- A file-based calculation (`run`) that a person or another program can submit. Both go through the same checks. The solver does not change because the request says `client: ai`.

### What it is not

- Not a substitute for experiment, calibrated SCFT for process design, or DSA lithography workflows.
- The **toy 1D phase-field** solver does **not** predict real lamellae / cylinders / gyroid.
- The **minimal SCFT** solver is **1D AB only** (density waves along a line). It does not resolve 3D morphologies.
- `pscf_rpc` is a separate, optional backend: Minnesota’s periodic solver for four AB diblock cells. It is not a calibrated process or DSA model, and the analytical ranking remains the default.
- Inverse “design” here means **ranked exploration of local monomer grids**, not industrial formulation optimization.
- Not an agent. Nothing in this repository writes requests on its own or treats an `ai` label as permission to skip validation, enlarge a batch, or retry a failed candidate.

If you need production SCFT (2D/3D cells, ABC, DSA masks), treat this repository as a **starting architecture** and see §8 for deliberate extension points.

Please also read **§3** before treating any prediction as a physical, biological, or materials-design conclusion.

---

## 3. Scope, models, and responsibility (disclaimer)

This section states how far the software’s claims are meant to go. It is part of the scientific framing of the tool, not optional fine print.

### 3.1 Directed self-assembly is one mechanism of organization, not the definition of Nature

Self-assembly provides a powerful way to understand how molecular interactions can produce organized structures. However, the existence and behaviour of biological systems cannot be reduced to directed self-assembly alone.

A biological system is not simply a collection of molecules arranged into a desired structure. It is a dynamic network involving energy consumption, information storage, regulation, adaptation, evolution, environmental interaction, and many other processes across different scales.

Therefore, designing a polymer morphology or predicting molecular organization with this software should not be interpreted as reproducing the complexity of living systems.

**Practical implication:** A successful prediction of self-assembly does not mean a material is biologically functional, safe, or equivalent to a natural structure.

### 3.2 Computational models are approximations of discovered patterns, not complete descriptions of Nature

The equations and assumptions implemented here are mathematical descriptions created to capture specific behaviours observed in physical systems. They are useful because they simplify reality into a form that can be analysed and tested.

However, every model has boundaries. Parameters, assumptions, numerical approximations, and omitted variables influence the accuracy and applicability of predictions.

No single theoretical framework can represent the entire universe. Scientific progress occurs by developing models that describe different aspects of reality and by understanding when each model is appropriate.

**Practical implication:** A model output from this tool should always be treated as a prediction or hypothesis requiring interpretation and validation, not as an absolute statement of what Nature must do.

### 3.3 Higher-level theories do not replace the fundamental processes that create them

The emergence of self-assembled structures does not remove the underlying physical and chemical mechanisms responsible for their existence.

Copolymer synthesis, molecular interactions, and material formation still depend on fundamental principles such as electronic structure, chemical bonding, electromagnetic interactions, thermodynamics, and molecular motion.

A mesoscale model describing domains, phases, or morphologies — including the educational morphology maps and SCFT modules in this repository — is not a replacement for chemistry. It is a higher-level description built upon the behaviour of atoms and molecules.

**Practical implication:** Understanding a pattern at one scale does not mean the lower-scale mechanisms have disappeared. A successful self-assembly prediction remains dependent on the chemistry that produced the molecules.

### 3.4 Designing biologically inspired materials requires responsibility beyond molecular design

The ability to design self-assembling materials may inspire visions of increasingly complex biological applications, such as artificial tissues, synthetic blood-like materials, or engineered structures that resemble components of living organisms. However, the organization of molecules into a designed material is not equivalent to the creation of life or the complete recreation of biological systems.

Living systems are not defined only by their physical structures. They depend on complex interactions involving metabolism, genetic information, cellular communication, repair mechanisms, evolution, and continuous exchange with their environment. A material that imitates one function or structure of biology does not automatically possess the properties, behaviours, or responsibilities associated with a living system.

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
5. In a `run` report, keep the four readings apart: the number that was calculated, the prediction inside the model, the experimental remark, and the limitations. A PSCF ranking is only among the cells that converged in that request.

---

## 5. What the scripts and packages do

### 5.1 Layout (project root)

```text
Block co-polymer design/
├── polymer_design/          # CLI app, polymer JSON, inverse design, benchmarks runner
│   ├── instrument/          # request check, batch run, human report, JSON result
│   ├── run_limits.json      # candidate ceiling (default 1000); not a request field
│   └── data/examples/       # sample request, including the lamellar PSCF check
├── polymer_engine/          # Physics core (χ, morphology, energy, structure, solvers, reporting)
├── benchmarks/              # Local morphology fixtures (PS-b-PMMA, PS-b-PEO, PI-b-PS)
├── cpp_core/                # Optional C++ kernels (phase-field timestep + SCFT MDE)
├── third_party/pscfpp/      # Vendored PSCF subset and, on Windows, bin/pscf_rpc.exe
├── tests/                   # Unit tests
├── requirements.txt
├── setup_cpp_core.py        # Optional: build C++ extensions
├── user_guide.md            # This file
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
| `instrument/` | Checks a `run` request, calls the existing solvers, and writes the report and the JSON result. It does not contain a second copy of the physics. |
| `run_limits.json` | Maximum candidates per `run` request. Default 1000. |
| `data/examples/periodic_lamellar.json` | Known-good PSCF request (f = 0.56, χN = 12, lamellar cell). |

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
| `pscf_rpc` | Optional | Periodic diblock SCFT (lamellae, hexagonal, gyroid, BCC) via University of Minnesota `pscf_rpc`. Windows: `third_party/pscfpp/bin/pscf_rpc.exe`, no WSL. Elsewhere: build it or set `PSCF_RPC`. Source in `third_party/pscfpp` (GPL-3.0-or-later). |
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
| `run` | File a request and keep the calculation record | `python -m polymer_design run polymer_design/data/examples/periodic_lamellar.json` |
| `visualize` | Optional picture of a stored result | `python -m polymer_design visualize result.json --illustrative` |

**Useful `evaluate` options**

- `--all` — evaluate every library polymer  
- `--file path.json` — evaluate your own JSON  
- `--brief` — shorter console output  

**Useful `simulate` options**

- `--solver analytical | phase_field | scft | pscf_rpc | monte_carlo`
- `--pscf-cell all|lam|hex|gyr|bcc` with `--solver pscf_rpc`
- `--list-solvers` — status of each solver  
- `--f`, `--chi`, `--N`, `--box`, `--n-grid`, `--iterations`, `--seed`  
- `--backend auto|numpy|cpp` (phase-field; SCFT uses `settings["propagator_backend"]` when called from Python)

**SCFT tips for professionals**

- Prefer **power-of-two** `--n-grid` (32, 64, …) if using the C++ propagator.
- `pscf_rpc` is separate from the 1D `scft` solver. On Windows the scripts run `third_party/pscfpp/bin/pscf_rpc.exe` and read space groups from `third_party/pscfpp/data`. Installing WSL is not part of using that file. `--pscf-cell lam` is the small check. `design --pscf` reruns the top analytical candidates on lamellar, hexagonal, gyroid, and BCC cells. If the executable is missing, the analytical ranking is unchanged and the report says so.
- Linux and macOS: build `third_party/pscfpp` (`./configure && make pscf_rpc`, with GSL and FFTW) and set `PSCF_RPC` to that executable. Rebuild notes, copyright, and the one source change are in `third_party/pscfpp/PROVENANCE.txt`. A `PSCF_RPC` value that is a Linux path is a developer override and may be launched through WSL.
- Low χN (e.g. 5): expect weak / homogeneous density from the 1D `scft` solver.
- High χN (e.g. 25): expect stronger 1D modulation.
- Optional box scan (Python API): `settings={"optimize_box": True, "box_lengths": [3.5, 4.5, 5.5]}` minimizes free energy over 1D cell lengths *L* only. The periodic `pscf_rpc` cells are a different calculation; see §6.4.

### 6.4 Filing a calculation (`run`)

`evaluate` and `simulate` print an answer and move on. `run` is the command that keeps the answer. You hand it one request file. It checks that file, calls the same solver a person would call from `simulate`, and writes two records: a report you can read, and a JSON file another program can read without scraping the prose.

A person at the terminal and a later program send the same kind of request. The solver does not look at who sent it.

**If you are running it yourself**

From the project root:

```text
python -m polymer_design run polymer_design/data/examples/periodic_lamellar.json
```

That example is the vendored lamellar check: block fractions 0.56 and 0.44, χ = 0.06, *N* = 200, so χN = 12, one cell (`lam`). On a machine with `pscf_rpc.exe` it should converge. The free energy is fHelmholtz 1.92567500294; the printed report rounds that number. The report is printed, and the terminal then names the files it wrote, as full paths:

```text
Output files
  report: ...\periodic_lamellar.out
  result: ...\periodic_lamellar.result.json
```

Those two files sit beside the request. The `.out` file is the calculation record. The `.result.json` file is the same calculation in a form you can open in Python or send on. While the job runs, progress lines such as `[1/1] lam-056 pscf_rpc` appear first. The paths are the last lines, so they stay on screen after the report.

Choose the names if you want:

```text
python -m polymer_design run candidate.inp --out candidate.out --json candidate.result.json --xlsx candidate.xlsx
```

| Flag | What it writes |
|------|----------------|
| *(none)* | `<request>.out` and `<request>.result.json` next to the request. The report is also printed. |
| `--out` | The human report at that path. It is not also printed. If you omit `--json`, the JSON result is that path plus `.json` (so `candidate.out` gives `candidate.out.json`). |
| `--json` | The structured result at that path. |
| `--xlsx` | A comparison table. One row per candidate and morphology. This is an export, not the scientific record. |
| `--resume` | An existing result JSON. Candidates already stored with the same id and the same parameters are kept and not rerun. |

Redirecting the printed report still works (`run request.json > copy.out`). The paths stay on the terminal because they are not part of the report.

A name ending in `.inp` is only a filename. The contents are this project's JSON. They are not a GAMESS input deck.

**What you put in the request**

```json
{
  "schema": "polymer_design.request.v1",
  "client": "human",
  "request_id": "periodic-lamellar-check",
  "solver": "pscf_rpc",
  "cells": ["lam"],
  "timeout_s": 180,
  "candidates": [
    {
      "id": "lam-056",
      "architecture": "diblock",
      "volume_fractions": [0.56, 0.44],
      "chi": 0.06,
      "degree_of_polymerization": 200
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `client` | `human` or `ai`. Written into the report as provenance. Default `human`. An `ai` label does not skip a check, raise the batch ceiling, or change the solver. |
| `request_id` | A name for this calculation. Default `request`. |
| `solver` | `analytical`, `phase_field`, `scft`, or `pscf_rpc`. One solver per request, so the numbers being ranked share one definition. |
| `cells` | Only for `pscf_rpc`. Any of `lam`, `hex`, `gyr`, `bcc`. Omit the field to run all four. |
| `timeout_s` | Seconds allowed for each PSCF cell. Default 3600. |
| `metadata` | Optional notes. Stored, not used as physics. |
| `candidates` | The designs to calculate. Required. |

Each candidate needs:

| Field | Meaning |
|-------|---------|
| `id` | Stable name. If you omit it, the file assigns `candidate-0001`, `candidate-0002`, and so on, in file order. Ids in one request must be unique. |
| `architecture` | `diblock` or `triblock`. `pscf_rpc` accepts diblocks only. |
| `volume_fractions` | Two numbers for a diblock, three for a triblock. They must already sum to 1 (within 0.001). They are not rescaled. For `pscf_rpc` each fraction must lie strictly between 0 and 1. |
| `chi` and/or `chiN` | Give one. If you give both, they must agree with `chiN = chi × N`. A disagreement stops the request; neither number is edited. |
| `N` or `degree_of_polymerization` | Chain length, greater than 0. If both are present they must be the same number. |

An unrecognized field is refused. In particular the request cannot contain `max_candidates`. The program does not invent a missing χ, a missing *N*, or a missing block fraction. Block names alone are not enough: this file is not the polymer library in §6.5, and it does not look up a χ for you.

**Several candidates**

Put them in the `candidates` list. This small batch stays on the analytical map, so it does not call PSCF:

```json
{
  "client": "human",
  "request_id": "two-compositions",
  "solver": "analytical",
  "candidates": [
    {
      "id": "symmetric",
      "architecture": "diblock",
      "volume_fractions": [0.5, 0.5],
      "chi": 0.08,
      "N": 200
    },
    {
      "id": "asymmetric",
      "architecture": "diblock",
      "volume_fractions": [0.25, 0.75],
      "chiN": 16,
      "degree_of_polymerization": 200
    }
  ]
}
```

The default ceiling is 1,000 candidates, from `polymer_design/run_limits.json`. A request of 1,001 is rejected before any solver starts, and the list is not silently shortened. The request file cannot raise the ceiling. The person operating the machine can, by editing `run_limits.json` or by setting the environment variable `POLYMER_DESIGN_MAX_CANDIDATES` to a positive integer. That variable is an operator setting, not a field an outside program should write into the request.

Progress is one line per candidate. A candidate that fails or does not converge stays in the output with that status. There is no automatic retry. `--resume previous.result.json` copies forward candidates whose id and parameters match the new request, and calculates only the rest. If an id is already stored with different parameters, the run stops rather than overwrite that record.

**How to read the report**

Read it in this order:

1. **Inputs and provenance.** Architecture, fractions, χ, *N*, χN, solver, software version, time, and `client`. When the solver is `pscf_rpc`, the PSCF commit from `third_party/pscfpp/PROVENANCE.txt` is on the page.
2. **Cells and numbers.** For PSCF, each requested morphology is listed with converged or not ranked. The free energy is fHelmholtz. A cell that did not converge is kept, including any number the log happened to print, and is left out of the ranking.
3. **Ranking.** Converged candidates only, lowest free energy first. For `pscf_rpc` that is the lowest converged fHelmholtz among the cells you named. For `analytical` it is the existing educational proxy, in which a lower score is the better score inside that model. Those two rankings are not the same kind of number, which is why one request uses one solver.
4. **Four sentences that are not interchangeable.**
   - *Calculated result* — what the solver returned among the cases it actually finished.
   - *Model prediction* — what that number suggests inside the model. The wording is “predicted” and “among the tested morphologies.”
   - *Experimental interpretation* — a qualitative remark about composition, segregation strength, and what the model leaves out (kinetics, dispersity, solvent history, temperature history, processing, defects). It asks for experimental validation. It does not cite an experiment that was not in the input.
   - *Limitations* — the assumptions that bound the paragraph above.

A single lamellar cell can still be called the lowest among the morphologies that were tested. That sentence means “of the cells in this request,” not “the equilibrium morphology of this chemistry.”

**The JSON result**

`schema` is `polymer_design.result.v1`. It repeats the inputs, the solver, the software version, the PSCF commit when that backend was used, the start and finish times, the assumptions, every candidate (including failures), the ranking, the warnings, and the same four-part interpretation. `client` is in the file.

Each PSCF morphology carries a small record, `pscf_example_cell_v1`: the cell key, the morphology name, the dimension, the lattice, the space group of the vendored example, whether it converged, and the free energy. The space groups are the ones in the example parameter files (`P_-1`, `p_6_m_m`, `I_a_-3_d`, `I_m_-3_m`). They are labels of those examples, not a symmetry the program discovered for your composition. The record is not a density field and not a file for Avogadro. It is the place a later export would start.

**What `pscf_rpc` is doing, in one paragraph**

The adapter takes the project’s χN and the first block fraction, writes them into a copy of the matching vendored example, and runs the local `pscf_rpc`. In those examples the block lengths already sum to 1, and the `chi` entry is χN. The adapter does not pass a separate *N*, and it does not change that convention. Initial fields stay the example’s `in/w.bf`. The 1D `scft` solver and the analytical map remain available; ask for them by name in `solver`.

**If you are calling it from another program**

Write the same JSON. Set `"client": "ai"` so the record shows the origin. Parse `*.result.json`. Do not scrape the `.out` file. The exit code is 0 when every candidate converged, 1 when the request finished but one or more candidates failed or did not converge, and 2 when the request was refused before a solver started. A refusal is printed on the terminal and does not produce a partial ranking.

### 6.5 Defining your own polymer (no deep coding)

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

### 6.6 Tests (programmers)

From project root:

```text
python -m unittest discover -s tests
```

### 6.7 A picture of the morphology (`visualize`)

This step is optional, and it happens after the calculation. `run` by itself still writes only the report and the result JSON.

The picture is there to answer: “What might this predicted morphology look like?” It does not answer: “Has the calculation proved that the polymer will form this structure?”

**If you are looking at it yourself**

1. Run the calculation and read the `.out` file: χN, fractions, which cells converged, the free energy, and the experimental paragraph.
2. If you want a sketch of the winning label (layers, cylinders, a gyroid network, or BCC spheres):

```text
python -m polymer_design visualize polymer_design/data/examples/periodic_lamellar.result.json --illustrative
```

The same program writes the other current pictures. Point it at `periodic_hex.result.json`, `periodic_gyroid.result.json`, or `periodic_bcc_spheres.result.json`. `--illustrative` draws the sketch of that name. Without it, the command draws the stored PSCF concentration, including the hexagonal lattice and the letters above the box. `--overwrite` is required when that cube already exists.

The red and blue surfaces follow the kind of cell in Figure 5 of Takano, Hiratsuka, and Takahashi (2024), cited in section 9. In that figure, red and blue are the segment profiles of the A and B blocks. The cube here is drawn from this file. It is not that figure.

3. That command writes the Avogadro cube itself. The terminal prints the folder, under `visualizations/<calculation-id>/batch_001/`, and the full path of `candidate_0001.cube`. Close any old copy of that cube in Avogadro and open the printed path. You should see a box. The balls and sticks are only the edges of the cell, so Avogadro has something to aim the camera at. Leave **Surfaces** on. Inside the box, Avogadro draws two surfaces from the A-block fraction: one where that fraction is A-rich, and one where it is B-rich. Above the box, a red letter A and a blue letter B name those surfaces: A is polymer A and B is polymer B. The letters are not atoms of the polymer. Avogadro has no caption field in a cube, so the letters are the legend. A lamellar pattern is repeated along the layer direction so the cell holds several layers rather than one wall. Drag the view until you look along the layers. The colors are whatever Avogadro uses for the two surfaces. This is the same kind of cell picture as Figure 5 of Takano, Hiratsuka, and Takahashi (2024), drawn from this file's fraction. It is not that figure, and it is not a SUSHI result. `candidate_0001.profile.png` is that fraction as curves. An XYZ or PDB file is not written.
4. Read `VISUALIZATION.txt` in that folder before you treat the picture as a material.

The cube draws boundaries, not filled domains. Each color is one side of the interface, the zone where the two blocks mix. In the polymer, one block fills the volume on the A-rich side of its surface and the other fills the volume on the B-rich side. Nothing between the two surfaces is painted, and nothing deep inside a domain is painted either.

For BCC spheres the red surface closes the minority cores, at the cell corners and at the body center. The blue surface is the boundary of the majority matrix around those cores, so each sphere looks wrapped. The matrix is the material outside that shell. Spheres that sit on the outer faces are cut by the cell. Hexagonal cylinders use the same reading: one surface is the core of the tube, and the other is the matrix boundary around it. For lamellae, each sheet is one side of an interface, and the layer is the material between the sheets.

A sketch is marked `illustrative`. It is a geometric drawing of the name on the result: lamellae, hexagonal cylinders, gyroid, or BCC spheres. PSCF did not produce it. The other three use the same two surfaces. Cylinders are round tubes on a hexagonal lattice, six neighbors at the same distance, repeated so the packing fills the box. The gyroid is one cell, with one surface for each network. BCC spheres are repeated so several spheres sit in the box.

To see the concentration from PSCF itself:

```text
python -m polymer_design run request.json --keep-concentration
python -m polymer_design visualize request.result.json --format avogadro
```

`--keep-concentration` adds `WRITE_C_RGRID` to the copied PSCF command, after `ITERATE` and before `FINISH`. The iteration is the same one that produced fHelmholtz. The saved grid is that monomer concentration (`density_source: pscf_calculated`). Gyroid and BCC are already 3D. Lamellae are 1D; the cube repeats that profile along y and z. A hexagonal cell is 2D; the cube places that mesh on the hexagonal lattice vectors and repeats the cell, so the tubes stay round and the packing is a honeycomb. That viewing cube is marked `derived_from_pscf`. Those viewing axes are not an extra PSCF result. Each surface is still only a boundary, read the same way as the sketch. A block that only weakly leaves one half is still given a surface, so both colors can show. That adjustment is part of the calculated export: `visualize` without `--illustrative` writes it from the stored PSCF grid.

`polymer_design/data/examples/periodic_bcc_spheres.json` is the BCC cell at the vendored example composition, f = 0.25 and χN = 20. `periodic_bcc.json` keeps the lamellar composition, which did not converge on that cell and so has no concentration to draw.

If the result has no grid and you do not pass `--illustrative`, the command stops. It does not draw a stand-in and call it the calculation.

There is no play/pause movie of the iterations. The command file does not keep the concentration at each SCFT step, and a smooth animation of “chains moving” would be a fiction. What you can inspect is the final picture: rotate and zoom it in Avogadro, and read the batch file for the morphology name, the density source, and the calculation it came from.

**Several candidates**

Pictures are written at most 100 at a time (`max_visualization_batch` in `polymer_design/run_limits.json`). The calculation limit of 1,000 is unchanged. A list of 1,000 is ten batches. By default only batch 1 is written, and the batch file reports how many remain:

```text
Requested: 1000
Batch limit: 100
Completed: 100
Remaining: 900
Status: batch_complete
```

`--batch 2` writes the next hundred. `--all-batches` writes each batch to disk before starting the next. A request for 101 files in one batch is rejected, not clipped. `--overwrite` is required before an existing picture is replaced.

**If another program is asking**

Send the same kind of JSON a person would write. `client` is still only provenance.

```json
{
  "schema": "polymer_design.visualize.v1",
  "client": "ai",
  "calculation": "screen.result.json",
  "illustrative": false,
  "batch": 2,
  "batch_size": 100
}
```

```text
python -m polymer_design visualize visualize.json
```

An `ai` label does not raise the batch of 100 or the calculation ceiling of 1,000. Parse `batch.json` in the batch folder. Do not assume a later batch was written unless `remaining` is 0 or you passed `--all-batches`.

Each `candidate_NNNN.morphology.json` file is the viewer-independent record: morphology, grid, density source, and provenance (candidate id, calculation id, solver, software version, PSCF commit when that solver was used, calculation time, export format, exporter version). The `.cjson` file is only the Avogadro view of that record.

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
4. Optional: add `--pscf` to rescore the leading candidates with `pscf_rpc`. The analytical list stays if that program is absent.

### C. Numerical segregation demo

1. `simulate --solver phase_field …` for a **toy** order-parameter movie in 1D.  
2. Or `simulate --solver scft …` for **mean-field chain** physics in 1D.  
3. Or `simulate --solver pscf_rpc --pscf-cell lam` for one periodic cell from Minnesota’s program (the four-cell set is `--pscf-cell all`).  
4. Always read the scientific report’s Interpretation + Reason lines.

### D. A calculation you can file

1. Copy `polymer_design/data/examples/periodic_lamellar.json`, or write a request as in §6.4.
2. `python -m polymer_design run that_file.json`
3. Read the paths the terminal prints. Open the `.out` for the narrative and the `.result.json` if you want the numbers in a table or in another program.
4. For a screening, list the candidates in one request and, for PSCF, name the cells. Rank only the rows marked converged.

### E. Look at the morphology after you have read the numbers

1. Read the `.out` report first.
2. `visualize` the result. Use `--illustrative` for a labeled sketch, or `--keep-concentration` on the earlier `run` if you want the PSCF concentration field.
3. Open the `.cube` the terminal prints. Above the box, the red letter A is polymer A and the blue letter B is polymer B. Compare candidates by their batch files.
4. Decide what is worth taking to the lab. The picture is not that decision.

---

## 8. Features you (or future field users) can add

These are intentional extension points — kept out of the educational core so ABC / 2D–3D work stays with people who need it.

### For polymer scientists collaborating with developers

| Desired capability | Where to extend | Notes |
|--------------------|-----------------|-------|
| Chemistry-specific χ(*T*) databases | `polymer_engine/thermodynamics/chi_models.py` | Keep models explicit; avoid silent scraping. |
| Better classical phase boundaries | `morphology/phase_map.py` | Document fit source (Matsen-type maps, your SAXS, etc.). |
| Calibrated domain spacing | `structure/domain_size.py` | Replace default *a* and exponents with your chemistry. |
| Periodic diblock cells (lamellae, hex, gyroid, BCC) | `solvers/pscf_rpc/` and `third_party/pscfpp` | Optional. Windows users run `bin/pscf_rpc.exe`. Keep the 1D `scft` path intact. |
| Another client of the same calculation | `polymer_design/instrument/` | Send the JSON request from §6.4. Do not teach the SCFT solver who the caller is. |
| Further 2D/3D cells beyond those four | New modules under `solvers/scft/` | Do not fold them into the 1D AB solver. |
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

Arora, A., Qin, J., Morse, D. C., Delaney, K. T., Fredrickson, G. H., Bates, F. S., & Dorfman, K. D. (2016). Broadly accessible self consistent field theory for block polymer materials discovery. *Macromolecules, 49*(13), 4675–4690. https://doi.org/10.1021/acs.macromol.6b00107  
*Used for:* the periodic diblock free energies from `pscf_rpc`. PSCF’s README asks for this citation when the program is used in published work. The article describes the Fortran PSCF; its SCFT algorithms are the ones the current `pscf_rpc` still follows.

Cheong, G. K., Chawla, A., Morse, D. C., & Dorfman, K. D. (2020). Open-source code for self-consistent field theory calculations of block polymer phase behavior on graphics processing units. *The European Physical Journal E, 43*, Article 15. https://doi.org/10.1140/epje/i2020-11938-y  
*Used for:* attribution of the C++ PSCF package vendored in `third_party/pscfpp`. This exhibit runs the CPU program, not the GPU one.

Chen, K., & Morse, D. C. (2025). Improved algorithm for identifying partial saddle-points in polymer field theoretic simulations. *The Journal of Chemical Physics, 162*, 234901. https://doi.org/10.1063/5.0264036  
*Used for:* attribution of later PSCF work. The design scripts do not launch those field-theoretic simulations.

Takano, F., Hiratsuka, M., & Takahashi, K. Z. (2024). Distinguish microphase-separated structures of diblock copolymers using local order parameters. *Scientific Reports, 14*, Article 23908. https://doi.org/10.1038/s41598-024-74525-y  
*Used for:* the kind of colored cell in the Avogadro cubes. Figure 5 of that paper draws the A-block and B-block segment profiles in red and blue. The cubes here aim at that kind of picture, from this file's fraction or from a stored PSCF grid. They are not that figure, and they are not the local-order-parameter classification in the paper.

Morse, D. C., & contributors. (2015–2026). *PSCF: Polymer Self-Consistent Field* [Computer software]. https://github.com/dmorse/pscfpp  
*Used for:* the `pscf_rpc` program. Copyright 2015–2026, The Regents of the University of Minnesota. GPL-3.0-or-later. Commit and the Windows build note are in `third_party/pscfpp/PROVENANCE.txt`.

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
| **SCFT** | Self-consistent field theory. Here, either the small 1D solver (`scft`) or, if you ask, Minnesota’s periodic `pscf_rpc`. |
| **MDE** | Modified diffusion equation for the chain propagator *q*. |
| **WSL / SSL** | Weak / strong segregation limits used in spacing estimates. In the spacing notes this is not Windows Subsystem for Linux. |
| **Backend** | NumPy vs optional C++ for a numerical kernel. For `run`, also the named solver: analytical, phase field, 1D SCFT, or `pscf_rpc`. |
| **client** | `human` or `ai` on a `run` request. Provenance only. Same checks either way. |
| **fHelmholtz** | The Helmholtz free energy `pscf_rpc` prints. Compared only among cells that converged. |
| **illustrative** | A geometric sketch of a morphology name. Not a PSCF field and not a measurement. |
| **Letter A / letter B** | The legend above the cube. Red A is polymer A. Blue B is polymer B. The letters are not atoms of the chain. |

---

*End of user guide.* Start from §3 and the console report’s Assumptions and Reasons for physical interpretation; for code changes, start from `polymer_engine/solvers/` and keep new architectures in separate modules.
