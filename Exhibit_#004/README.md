# Exhibit_004: Microphase Oracle

A polymer-physics sketchbook with manners. Hand it a diblock (or a JSON library of them), and it works through χN, classical morphology windows, free-energy proxies, and domain-spacing guesses out loud—then, if you ask, runs a 1D SCFT or a toy phase-field so you can watch segregation without pretending you’ve shipped a foundry simulator.

Self-assembly here is a model of organization, not a claim about life, biology, or Nature writ large. Read the disclaimer in `user_guide.md` (§3) before treating any prediction as more than a hypothesis under stated assumptions.

```
python -m polymer_design
```

More commands, physics limits, and the release checklist: `user_guide.md`, `github_release_checklist.txt`.

## A stricter free energy, if you ask

The everyday commands stay on the analytical map, the toy phase field, and the small 1D SCFT. Those need Python and the packages in `requirements.txt`. They do not need WSL.

If you ask for the periodic check, the sketchbook hands the candidate to University of Minnesota's `pscf_rpc` and ranks four diblock cells by Helmholtz free energy: lamellae, hexagonal cylinders, gyroid, and BCC spheres. On Windows that program is already in the tree, at `third_party/pscfpp/bin/pscf_rpc.exe`.

```text
python -m polymer_design simulate --solver pscf_rpc --pscf-cell lam --chi 0.06 --N 200 --f 0.56
python -m polymer_design design --target-morphology lamellae --pscf --top 5
```

`--pscf-cell lam` is the short check. `design --pscf` rescores the leading analytical candidates and leaves that ranking in place when the program cannot run. Linux and macOS do not receive this `.exe`. Build `pscf_rpc` there, or set `PSCF_RPC` to the executable you built. The recipe is in `third_party/pscfpp/PROVENANCE.txt`.

## A calculation record

`evaluate` talks. `run` files the answer. You give it one JSON request — the same file a person would write, or that another program might write later — and it calls the solver you already have. The terminal prints the report, then tells you where the copies went:

```text
python -m polymer_design run polymer_design/data/examples/periodic_lamellar.json
```

```text
Output files
  report: ...\periodic_lamellar.out
  result: ...\periodic_lamellar.result.json
```

The `.out` file is the record: inputs, which cells converged, free energies, a ranking of converged results only, then four separate readings (what was calculated, what the model predicts, what that might mean in an experiment, and the limits of the claim). The `.result.json` file is the same calculation for Python or a spreadsheet. A lower fHelmholtz is a comparison among the cells you asked for. It is not a promise that the morphology will form.

That example is the short PSCF check (fractions 0.56 and 0.44, χN = 12, lamellae). A file named `.inp` may hold the same JSON; the suffix does not make it a GAMESS deck. Block fractions must already sum to 1. If you supply both χ and χN and they disagree, the run stops and edits neither.

`client` may be `human` or `ai`. The word is copied into the report so you can see who wrote the request. It does not relax a check or change the solver.

One request can hold many candidates, up to 1,000 (`polymer_design/run_limits.json`). The request cannot raise that number. If you are the person at the machine and you mean a different ceiling, set `POLYMER_DESIGN_MAX_CANDIDATES`. Anything larger is refused before a solver starts. `--xlsx results.xlsx` adds a comparison table. `--resume` keeps candidates already stored with the same parameters and does not retry them. Failed candidates stay in the file.

The field list, the batch rules, and how to read both output files are in `user_guide.md`, section 6.4.

## A picture, if you ask

The report answers “what did the calculation find?” A picture, when you ask for one, answers “what might that morphology look like?” It does not answer “will this polymer form that structure?”

```text
python -m polymer_design visualize polymer_design/data/examples/periodic_lamellar.result.json --illustrative
```

The same command writes whatever picture that result names. Use `periodic_hex.result.json`, `periodic_gyroid.result.json`, or `periodic_bcc_spheres.result.json` in that same folder. Add `--illustrative` for the sketch. Leave it off, after a run with `--keep-concentration`, for the calculated cube. `--overwrite` replaces a cube that is already there.

The terminal prints the folder and the path of `candidate_0001.cube`. Open that cube in Avogadro. The box is the cell edge. With Surfaces on, one surface is the A-rich side of the interface and the other is the B-rich side. Above the box, a red letter A and a blue letter B name them: A is polymer A and B is polymer B. A cube file cannot carry a text caption, so those letters are the legend. They are not atoms of the polymer. Avogadro draws those boundaries only. It does not fill the domain. In the polymer, one block occupies the volume on one side and the other block occupies the volume on the other side. A blue shell around a red sphere or tube is the matrix side of that interface; the matrix is the material outside the shell. A layer is the material between its two sheets. The red and blue coloring follows Figure 5 of Takano, Hiratsuka, and Takahashi (2024), where those colors are the A-block and B-block segment profiles. The citation is in section 9 of `user_guide.md`. These cubes are not that figure, and they are not a SUSHI result. The same note is in `VISUALIZATION.txt` beside the cube. Section 6.7 of `user_guide.md` is the longer reading.

`--illustrative` draws a labeled sketch of lamellae, cylinders, gyroid, or BCC spheres, in the same kind of cell: a box, and one surface for each block. The file says `illustrative`. That sketch is not PSCF output. To export the concentration PSCF actually computed, run the calculation with `--keep-concentration` and then visualize without `--illustrative`. A 3D cell is passed through as calculated. A lamellar or hexagonal cell is only 1D or 2D in PSCF; the cube repeats that grid so you can see it, and the file says `derived_from_pscf`. If the result has no grid and you do not ask for a sketch, the command stops and does not invent one.

Pictures are written in batches of 100 (`max_visualization_batch` in `polymer_design/run_limits.json`). A request for 1,000 candidates is ten batches. One invocation writes the batch you asked for, then stops; `--all-batches` writes the rest, each batch on disk before the next. The calculation ceiling is still 1,000. `client: ai` uses the same rules. There is no playback of SCFT iterations: the PSCF run does not keep that history, and a made-up movie is not offered.

## License

This exhibit is free software under the GNU General Public License, version 3 or any later version. See `LICENSE`. There is no warranty, to the extent permitted by law. The root MIT license of Hall of Failures does not apply here.

Original files in this exhibit: Copyright (C) 2026 Disquietude, also under GPL-3.0-or-later in this revision.

The directory `third_party/pscfpp` is Polymer Self-Consistent Field (PSCF), https://github.com/dmorse/pscfpp, at the commit recorded in `third_party/pscfpp/PROVENANCE.txt`. Copyright 2015-2026, The Regents of the University of Minnesota. PSCF is free software under GPL version 3 or any later version, without warranty. The Windows program `bin/pscf_rpc.exe` is a build of that source. The corresponding PSCF source is the rest of `third_party/pscfpp`. One file was changed for that build: `src/prdc/crystal/groupFile.cpp` (7 October 2026, Disquietude) finds `data/groups` beside the executable. The notice is in the file and in `PROVENANCE.txt`.

The Windows program also contains the GNU Scientific Library, version 2.8 (https://www.gnu.org/software/gsl/, GPL version 3 or later), and FFTW, version 3.3.10 (https://www.fftw.org/, GPL version 2 or later). Their source is those upstream releases, built as `PROVENANCE.txt` records.

If you use PSCF in published work, cite that GitHub address and the papers in section 9 of `user_guide.md` (Arora et al., 2016; Cheong et al., 2020; Chen & Morse, 2025). PSCF's own README asks for that.

When this folder is published inside https://github.com/Hunchback-19A/Hall_of_Failures, paste `hall_of_failures_root_notices.txt` into that repository's root `LICENSE` and `README.md`. The commit of this exhibit already on `main` without PSCF stays MIT for anyone using that snapshot.
