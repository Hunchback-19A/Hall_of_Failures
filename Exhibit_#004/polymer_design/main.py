#!/usr/bin/env python3
"""
Console entry point for the block copolymer self-assembly design prototype.

From the project root (parent of this folder):
  python -m polymer_design
  python -m polymer_design list
  python -m polymer_design evaluate --polymer PS-b-PMMA

From inside this folder:
  python main.py
  python main.py list
  python main.py evaluate --polymer PS-b-PMMA
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `python main.py ...` work when the shell is already inside polymer_design/.
PACKAGE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = PACKAGE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from polymer_design.evaluator import SimplifiedPhysicsEvaluator
from polymer_design.optimization import (
    MonteCarloTreeSearch,
    ParticleSwarmOptimizer,
    RandomSearch,
)
from polymer_design.polymer import load_polymer_file, load_polymers
from polymer_design.visualization.console_display import print_report

DEFAULT_POLYMERS = PACKAGE_DIR / "data" / "polymers.json"
DEFAULT_MONOMERS = PACKAGE_DIR / "data" / "monomers.json"
DEFAULT_BENCHMARKS = _PROJECT_ROOT / "benchmarks"


def build_evaluator() -> SimplifiedPhysicsEvaluator:
    return SimplifiedPhysicsEvaluator(monomers_path=DEFAULT_MONOMERS)


def cmd_list(args: argparse.Namespace) -> int:
    polymers = load_polymers(args.polymers)
    print(f"Loaded {len(polymers)} polymer definition(s) from {args.polymers}")
    for p in polymers:
        chi = p.chi if p.chi is not None else "estimate"
        print(
            f"  - {p.name:28s}  {p.architecture:8s}  "
            f"χ={chi}  N={p.degree_of_polymerization:g}"
        )
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    evaluator = build_evaluator()

    if args.file:
        loaded = load_polymer_file(args.file)
        polymers = loaded if isinstance(loaded, list) else [loaded]
    else:
        polymers = load_polymers(args.polymers)
        if args.polymer:
            polymers = [p for p in polymers if p.name == args.polymer]
            if not polymers:
                names = [p.name for p in load_polymers(args.polymers)]
                print(f"Polymer '{args.polymer}' not found. Available: {', '.join(names)}")
                return 1
        elif args.all is not True:
            # Default demo: the weakly segregated example from the prompt spirit.
            preferred = [p for p in polymers if p.name == "weakly-segregated-demo"]
            polymers = preferred or polymers[:1]

    for polymer in polymers:
        prediction = evaluator.evaluate(polymer)
        print_report(prediction, show_calculations=not args.brief)
        print()
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    evaluator = build_evaluator()
    evaluate_fn = evaluator.evaluate
    target = args.target

    if args.search == "random":
        search = RandomSearch(evaluate_fn=evaluate_fn, chi=args.chi, seed=args.seed)
        result = search.run(n_candidates=args.n, target_morphology=target)
        label = "Random search"
    elif args.search == "pso":
        search = ParticleSwarmOptimizer(evaluate_fn=evaluate_fn, chi=args.chi, seed=args.seed)
        result = search.run(iterations=args.n, target_morphology=target)
        label = "Particle swarm optimization"
    elif args.search == "mcts":
        search = MonteCarloTreeSearch(evaluate_fn=evaluate_fn, chi=args.chi, seed=args.seed)
        result = search.run(iterations=max(args.n, 6), target_morphology=target)
        label = "Monte Carlo tree search"
    else:
        print(f"Unknown search method: {args.search}")
        return 1

    print("=" * 64)
    print(f"{label}: evaluated {len(result.history)} candidate(s)")
    if target:
        print(f"Target morphology hint: {target}")
    print("Best candidate report:")
    print("=" * 64)
    print_report(result.best, show_calculations=not args.brief)
    return 0


def cmd_dump_example(_: argparse.Namespace) -> int:
    example = {
        "name": "PS-b-PMMA",
        "architecture": "diblock",
        "blocks": [
            {"name": "styrene", "fraction": 0.5},
            {"name": "MMA", "fraction": 0.5},
        ],
        "parameters": {"chi": 0.04, "degree_of_polymerization": 100},
    }
    print(json.dumps(example, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from polymer_design.validation import BenchmarkRunner

    runner = BenchmarkRunner(evaluator=build_evaluator())
    report = runner.run_dir(args.benchmarks)
    print(report.format())
    return 0 if report.n_failed == 0 else 1


def cmd_design(args: argparse.Namespace) -> int:
    from polymer_design.design import DesignExplorer, DesignTarget

    target = DesignTarget(
        morphology=args.target_morphology,
        domain_spacing_nm=args.spacing,
        temperature_K=args.temperature,
        architecture=args.architecture,
        f_min=args.f_min,
        f_max=args.f_max,
        N_min=args.N_min,
        N_max=args.N_max,
        chi=args.chi,
        chi_min=args.chi_min,
        chi_max=args.chi_max,
        chiN_min=args.chiN_min,
        chiN_max=args.chiN_max,
        block_a=args.block_a,
        block_b=args.block_b,
        top_k=args.top,
    )
    explorer = DesignExplorer(
        monomers_path=DEFAULT_MONOMERS,
        evaluator=build_evaluator(),
    )
    _ranked, _n, report = explorer.explore(target)
    print(report)
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    from polymer_engine.solvers import SimulationInput, get_solver, list_solvers

    if args.list_solvers:
        print("Available solvers:")
        for name, status in list_solvers().items():
            print(f"  - {name}: {status}")
        return 0

    try:
        solver = get_solver(args.solver)
    except ValueError as exc:
        print(exc)
        return 1

    sim_input = SimulationInput(
        name=args.name,
        architecture=args.architecture,
        volume_fractions=[args.f, 1.0 - args.f],
        chi=args.chi,
        degree_of_polymerization=args.N,
        n_grid=args.n_grid,
        timestep=args.dt,
        n_iterations=args.iterations,
        random_seed=args.seed,
        box_length=args.box,
        settings={"backend": args.backend},
    )
    try:
        output = solver.solve(sim_input)
    except NotImplementedError as exc:
        print(f"Solver '{args.solver}' is a placeholder only:\n{exc}")
        return 2

    from polymer_engine.reporting import format_simulation_scientific_report

    print(format_simulation_scientific_report(output, sim_input=sim_input))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Educational block copolymer self-assembly design prototype."
    )
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--polymers",
        type=Path,
        default=DEFAULT_POLYMERS,
        help="Path to polymers.json library",
    )
    shared.add_argument(
        "--brief",
        action="store_true",
        help="Hide detailed calculation steps",
    )

    sub = parser.add_subparsers(dest="command")

    list_p = sub.add_parser("list", parents=[shared], help="List polymers in the library")
    list_p.set_defaults(func=cmd_list)

    eval_p = sub.add_parser("evaluate", parents=[shared], help="Evaluate one or more polymers")
    eval_p.add_argument("--polymer", type=str, help="Name of polymer in the library")
    eval_p.add_argument("--file", type=Path, help="JSON file with one polymer or a list")
    eval_p.add_argument("--all", action="store_true", help="Evaluate every library polymer")
    eval_p.set_defaults(func=cmd_evaluate)

    search_p = sub.add_parser("search", parents=[shared], help="Run a design-space search wrapper")
    search_p.add_argument(
        "--method",
        dest="search",
        choices=["random", "pso", "mcts"],
        default="random",
        help="Search algorithm",
    )
    search_p.add_argument("--target", type=str, default=None, help="Optional morphology target")
    search_p.add_argument("--n", type=int, default=15, help="Candidates / iterations")
    search_p.add_argument("--chi", type=float, default=0.05, help="Fixed χ for generated candidates")
    search_p.add_argument("--seed", type=int, default=0, help="RNG seed")
    search_p.set_defaults(func=cmd_search)

    ex_p = sub.add_parser("example-json", help="Print an example polymer JSON")
    ex_p.set_defaults(func=cmd_dump_example)

    val_p = sub.add_parser(
        "validate",
        parents=[shared],
        help="Run local morphology benchmarks (no network / no citation scraping)",
    )
    val_p.add_argument(
        "--benchmarks",
        type=Path,
        default=DEFAULT_BENCHMARKS,
        help="Directory of benchmark JSON files",
    )
    val_p.set_defaults(func=cmd_validate)

    design_p = sub.add_parser(
        "design",
        parents=[shared],
        help="Inverse design exploration via local monomer grids (not true optimization)",
    )
    design_p.add_argument("--target-morphology", type=str, default=None)
    design_p.add_argument("--spacing", type=float, default=None, help="Target domain spacing (nm)")
    design_p.add_argument("--temperature", type=float, default=None, help="Temperature (K)")
    design_p.add_argument("--architecture", type=str, default="diblock")
    design_p.add_argument("--f-min", dest="f_min", type=float, default=0.10)
    design_p.add_argument("--f-max", dest="f_max", type=float, default=0.50)
    design_p.add_argument("--N-min", dest="N_min", type=float, default=80.0)
    design_p.add_argument("--N-max", dest="N_max", type=float, default=300.0)
    design_p.add_argument("--chi", type=float, default=None, help="Fixed χ for all grid candidates")
    design_p.add_argument("--chi-min", dest="chi_min", type=float, default=None)
    design_p.add_argument("--chi-max", dest="chi_max", type=float, default=None)
    design_p.add_argument("--chiN-min", dest="chiN_min", type=float, default=None)
    design_p.add_argument("--chiN-max", dest="chiN_max", type=float, default=None)
    design_p.add_argument("--block-a", dest="block_a", type=str, default=None)
    design_p.add_argument("--block-b", dest="block_b", type=str, default=None)
    design_p.add_argument("--top", type=int, default=5, help="Show top-K ranked candidates")
    design_p.set_defaults(func=cmd_design)

    sim_p = sub.add_parser(
        "simulate",
        parents=[shared],
        help="Run a pluggable solver (analytical or toy phase-field; SCFT/MC placeholders)",
    )
    sim_p.add_argument(
        "--solver",
        type=str,
        default="phase_field",
        help="analytical | phase_field | scft | monte_carlo",
    )
    sim_p.add_argument("--list-solvers", action="store_true", help="List solver statuses")
    sim_p.add_argument("--name", type=str, default="sim")
    sim_p.add_argument("--architecture", type=str, default="diblock")
    sim_p.add_argument("--f", type=float, default=0.5, help="Volume fraction of block A")
    sim_p.add_argument("--chi", type=float, default=0.08)
    sim_p.add_argument("--N", type=float, default=200.0)
    sim_p.add_argument("--n-grid", dest="n_grid", type=int, default=64)
    sim_p.add_argument("--dt", type=float, default=5.0e-4, help="Timestep")
    sim_p.add_argument("--iterations", type=int, default=2000)
    sim_p.add_argument("--seed", type=int, default=0)
    sim_p.add_argument("--box", type=float, default=1.0, help="1D box length")
    sim_p.add_argument(
        "--backend",
        type=str,
        default="auto",
        choices=["auto", "numpy", "cpp"],
        help="phase_field backend: numpy (default install path), cpp (optional), or auto",
    )
    sim_p.set_defaults(func=cmd_simulate)

    # Also accept top-level flags for the default evaluate path.
    parser.add_argument("--polymers", type=Path, default=DEFAULT_POLYMERS)
    parser.add_argument("--brief", action="store_true")

    return parser


def _configure_stdout() -> None:
    """Prefer UTF-8 so scientific symbols (χ) print on Windows consoles."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)

    # Convenience: bare invocation evaluates the demo polymer.
    if args.command is None:
        args.command = "evaluate"
        args.polymer = None
        args.file = None
        args.all = False
        if not hasattr(args, "brief"):
            args.brief = False
        return cmd_evaluate(args)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
