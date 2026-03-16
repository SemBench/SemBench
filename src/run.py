"""
Created on May 28, 2025

@author: Jiale Lao

Main entry point for running benchmarks on different multi-modal data systems.

Supports two execution modes:
1. Isolated mode (default when .venvs/ exists): Each system runs in its own
   virtual environment via subprocess, avoiding dependency conflicts.
2. Direct mode (--no-isolation or when .venvs/ doesn't exist): All systems
   run in the current Python process (legacy behavior).
"""

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENVS_DIR = PROJECT_ROOT / ".venvs"


def get_runner_class(system: str, use_case: str):
    """Dynamically import and return the runner class for a given system."""

    # Define system to runner class name mapping
    runner_classes = {
        "lotus": "LotusRunner",
        "palimpzest": "PalimpzestRunner",
        "bigquery": "BigQueryRunner",
        "snowflake": "SnowflakeRunner",
        "thalamusdb": "ThalamusDBRunner",
        "flockmtl": "FlockMTLRunner",
        "caesura": "CaesuraRunner",
    }

    if system not in runner_classes:
        raise ValueError(f"Unknown system: {system}")

    try:
        # Construct the module path using the fixed format
        module_path = (
            f"scenario.{use_case}.runner.{system}_runner.{system}_runner"
        )
        class_name = runner_classes[system]

        # Dynamically import the module and get the class
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    except ImportError as e:
        print(f"Error importing runner for {system} from {module_path}: {e}")
        return None
    except AttributeError as e:
        print(
            f"Error: Class {class_name} not found in module {module_path}: {e}"
        )
        return None


def get_evaluator(use_case: str):
    """
    Get the evaluator for a specific use case.
    Dynamically imports the evaluator based on the use case.
    """
    # Define use case to evaluator class name mapping
    evaluator_classes = {
        "movie": "MovieEvaluator",
        "detective": "DetectiveEvaluator",
        "medical": "MedicalEvaluator",
        "animals": "AnimalsEvaluator",
        "ecomm": "EcommEvaluator",
        "mmqa": "MMQAEvaluator",
        "cars": "CarsEvaluator",
        # Add more use cases here as needed
    }

    if use_case not in evaluator_classes:
        raise ValueError(f"Unknown use case: {use_case}")

    try:
        # Construct the module path using the fixed format
        module_path = f"scenario.{use_case}.evaluation.evaluate"
        class_name = evaluator_classes[use_case]

        # Dynamically import the module and get the class
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    except ImportError as e:
        print(
            f"Error importing evaluator for {use_case} from {module_path}: {e}"
        )
        return None
    except AttributeError as e:
        print(
            f"Error: Class {class_name} not found in module {module_path}: {e}"
        )
        return None


def parse_query_ids(query_args: List[str]) -> List[int]:
    """
    Parse query IDs from command line arguments.

    Args:
        query_args: List of query identifiers (e.g., ['1', '5'] or ['Q1', 'Q5'])

    Returns:
        List of query IDs as integers
    """
    query_ids = []
    for arg in query_args:
        # Handle both formats: '1' and 'Q1'
        if arg.startswith("Q"):
            try:
                query_id = int(arg[1:])
                query_ids.append(query_id)
            except ValueError:
                print(f"Warning: Invalid query format '{arg}', skipping")
        else:
            query_ids.append(arg)

    return sorted(query_ids)


def get_system_venv_python(system: str) -> Optional[Path]:
    """Return the Python executable path for a system's venv, or None."""
    venv_python = VENVS_DIR / system / "bin" / "python"
    if venv_python.exists():
        return venv_python
    return None


def run_system_isolated(
    system: str,
    use_case: str,
    queries: Optional[List[int]],
    model_name: str,
    scale_factor: Optional[int],
    skip_setup: bool,
) -> Dict:
    """
    Run a system in its isolated virtual environment via subprocess.

    Returns:
        Dictionary of query results, or {"error": "..."} on failure.
    """
    venv_python = get_system_venv_python(system)
    if not venv_python:
        return {"error": f"No venv found for {system} at {VENVS_DIR / system}"}

    worker_script = PROJECT_ROOT / "src" / "run_worker.py"

    cmd = [
        str(venv_python),
        str(worker_script),
        "--system", system,
        "--use-case", use_case,
        "--model", model_name,
    ]
    if queries:
        cmd += ["--queries"] + [str(q) for q in queries]
    if scale_factor is not None:
        cmd += ["--scale-factor", str(scale_factor)]
    if skip_setup:
        cmd += ["--skip-setup"]

    print(f"  [isolated] Using venv: {venv_python}")

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Print worker output
    if result.stdout:
        # Filter out the worker result marker and print the rest
        for line in result.stdout.splitlines():
            if "__WORKER_RESULT__" in line or "__WORKER_ERROR__" in line:
                continue
            print(f"  [{system}] {line}")

    # Parse worker result from stdout
    if result.returncode == 0 and result.stdout:
        match = re.search(
            r"__WORKER_RESULT__(.+?)__END_WORKER_RESULT__", result.stdout
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # Parse error
    if result.stdout:
        match = re.search(
            r"__WORKER_ERROR__(.+?)__END_WORKER_ERROR__", result.stdout
        )
        if match:
            return {"error": match.group(1)}

    if result.returncode != 0:
        return {"error": f"Worker exited with code {result.returncode}"}

    # Fallback: try to read metrics from disk
    metrics_file = (
        PROJECT_ROOT / "files" / use_case / "metrics" / f"{system}.json"
    )
    if metrics_file.exists():
        with open(metrics_file) as f:
            return json.load(f)

    return {"error": "No results returned from worker"}


def run_benchmark(
    systems: List[str],
    use_cases: List[str],
    queries: List[int] = None,
    skip_setup: bool = False,
    model_name: str = "gemini-2.5-flash",
    scale_factor: str = None,
    use_isolation: bool = True,
):
    """
    Run benchmarks for specified systems and use cases.

    Args:
        systems: List of system names to benchmark
        use_cases: List of use cases to run
        queries: Optional list of specific query IDs to run (e.g., [1, 5])
        skip_setup: Whether to skip setup phase
        model_name: Model name to use for systems that support it
        use_isolation: Use per-system venvs when available
    """
    results = {}

    for use_case in use_cases:
        print(f"\n{'='*60}")
        print(f"Running benchmarks for use case: {use_case}")
        print(f"{'='*60}")

        results[use_case] = {}

        # Run each system
        for system in systems:
            print(f"\n--- Running {system} ---")

            # Decide execution mode
            venv_python = get_system_venv_python(system) if use_isolation else None

            if venv_python:
                # Isolated execution via subprocess
                system_results = run_system_isolated(
                    system=system,
                    use_case=use_case,
                    queries=queries,
                    model_name=model_name,
                    scale_factor=scale_factor,
                    skip_setup=skip_setup,
                )
                results[use_case][system] = system_results

                if "error" not in system_results:
                    print(f"✓ {system} completed successfully (isolated)")
                else:
                    print(f"✗ Error running {system}: {system_results['error']}")

            else:
                # Direct execution in current process (legacy mode)
                if use_isolation:
                    print(
                        f"  No venv found for {system}, "
                        f"falling back to direct execution"
                    )

                runner_class = get_runner_class(system, use_case)
                if not runner_class:
                    print(f"Skipping {system} due to import error")
                    continue

                try:
                    runner = runner_class(
                        use_case=use_case,
                        scale_factor=scale_factor,
                        skip_setup=skip_setup,
                        model_name=model_name,
                    )
                    system_metrics = runner.run_all_queries(queries=queries)

                    results[use_case][system] = {
                        f"Q{query_id}": metric.to_dict()
                        for query_id, metric in system_metrics.items()
                    }

                    print(f"✓ {system} completed successfully")

                except Exception as e:
                    print(f"✗ Error running {system}: {e}")
                    import traceback

                    traceback.print_exc()
                    results[use_case][system] = {"error": str(e)}

        # Run evaluation
        print(f"\n--- Running evaluation for {use_case} ---")
        try:
            evaluator_class = get_evaluator(use_case)
            evaluator = evaluator_class(use_case, scale_factor)

            # Evaluate all systems
            for system in systems:
                if (
                    system in results[use_case]
                    and "error" not in results[use_case][system]
                ):
                    print(f"Evaluating {system}...")
                    evaluator.evaluate_system(system, queries=queries)

            print("✓ Evaluation completed successfully")

        except Exception as e:
            print(f"✗ Error during evaluation: {e}")
            import traceback

            traceback.print_exc()

    return results


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run benchmarks on multi-modal data systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all queries for LOTUS on movie use case
  python run.py --systems lotus --use-cases movie

  # Run specific queries (1 and 5) for multiple systems
  python run.py --systems lotus bigquery --queries 1 5

  # Run queries using Q-prefix notation
  python run.py --systems lotus --queries Q1 Q5 Q10

  # Force direct execution (skip venv isolation)
  python run.py --systems lotus --no-isolation
        """,
    )

    parser.add_argument(
        "--systems",
        nargs="+",
        default=["lotus"],
        help="Systems to benchmark (e.g., lotus bigquery)",
    )

    parser.add_argument(
        "--use-cases",
        nargs="+",
        default=["movie"],
        help="Use cases to run (e.g., movie amazon_product real_estate)",
    )

    parser.add_argument(
        "--queries",
        nargs="+",
        default=None,
        help="Specific query IDs to run (e.g., 1 5 or Q1 Q5). If not specified, runs all queries.",  # noqa: E501
    )

    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip downloading and setting up the data sets for the specified use cases; used to speed up runs after the initial setup has been completed.",  # noqa: E501
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash",
        help="Model name to use for systems that support it (default: gemini-2.5-flash)",
    )

    parser.add_argument(
        "--scale-factor",
        type=int,
        help="Factor to control the dataset size. Note that each use case has its own range for its respective scale factor.",  # noqa: E501
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--no-isolation",
        action="store_true",
        help="Disable per-system venv isolation (run all systems in current process)",
    )

    args = parser.parse_args()

    # Parse query IDs
    query_ids = None
    if args.queries:
        query_ids = parse_query_ids(args.queries)
        if not query_ids:
            print("Error: No valid query IDs provided")
            sys.exit(1)

    # Determine isolation mode
    use_isolation = not args.no_isolation
    if use_isolation and VENVS_DIR.exists():
        available_venvs = [
            d.name for d in VENVS_DIR.iterdir()
            if d.is_dir() and d.name != "sembench"
            and (d / "bin" / "python").exists()
        ]
        if available_venvs:
            print(f"Per-system venvs detected: {', '.join(available_venvs)}")
        else:
            use_isolation = False
    else:
        use_isolation = False

    print("Multi-Modal Data Systems Benchmark")
    print(f"Systems: {', '.join(args.systems)}")
    print(f"Use cases: {', '.join(args.use_cases)}")
    print(f"Model: {args.model}")
    print(f"Queries: {', '.join(map(str, query_ids)) if query_ids else 'All'}")
    print(f"Scale factor: {args.scale_factor}")
    print(f"Isolation: {'enabled' if use_isolation else 'disabled'}")

    # Run benchmark
    results = run_benchmark(
        systems=args.systems,
        use_cases=args.use_cases,
        queries=query_ids,
        skip_setup=args.skip_setup,
        model_name=args.model,
        scale_factor=args.scale_factor,
        use_isolation=use_isolation,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    for use_case, systems_results in results.items():
        print(f"\n{use_case.upper()}:")
        for system, system_results in systems_results.items():
            if "error" in system_results:
                print(f"  {system}: ❌ Failed - {system_results['error']}")
            else:
                print(f"  {system}: ✅ Completed")
                if system_results:
                    # Sort by query ID for consistent output
                    sorted_results = sorted(
                        system_results.items(),
                        key=lambda x: (
                            x[0][1:] if x[0].startswith("Q") else x[0]
                        ),
                    )

                    for query_key, metrics in sorted_results:
                        if isinstance(metrics, dict):
                            query_id = metrics.get("query_id", query_key)
                            # Handle both formats: integer ID or "Q{id}" string
                            if isinstance(
                                query_id, str
                            ) and query_id.startswith("Q"):
                                display_id = query_id
                            else:
                                display_id = f"Q{query_id}"

                            status = metrics.get("status", "unknown")
                            time_str = (
                                f"{metrics.get('execution_time', 0):.2f}s"
                            )

                            if status == "success":
                                row_count = metrics.get("row_count", 0)
                                token_usage = metrics.get("token_usage", 0)
                                cost = metrics.get("money_cost", 0.0)

                                print(
                                    f"    {display_id}: ✅ {time_str}, {row_count} rows",  # noqa: E501
                                    end="",
                                )
                                if token_usage > 0:
                                    print(f", {token_usage} tokens", end="")
                                if cost > 0:
                                    print(f", ${cost:.4f}", end="")
                                print()
                            elif status == "failed":
                                error_msg = metrics.get(
                                    "error", "Unknown error"
                                )
                                print(
                                    f"    {display_id}: ❌ {time_str}, Error: {error_msg}"  # noqa: E501
                                )
                            else:
                                print(f"    {display_id}: {time_str}")

    # Flush output before force-terminating (os._exit skips buffer flush)
    sys.stdout.flush()
    sys.stderr.flush()

    # Force terminate all threads including background ones (LOTUS connection
    # pools)
    os._exit(0)


if __name__ == "__main__":
    main()
