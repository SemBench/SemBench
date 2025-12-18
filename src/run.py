"""
Created on May 28, 2025

@author: Jiale Lao

Main entry point for running benchmarks on different multi-modal data systems.
"""

import argparse
import importlib
import os
import sys
from typing import List

from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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


def run_benchmark(
    systems: List[str],
    use_cases: List[str],
    queries: List[int] = None,
    skip_setup: bool = False,
    model_name: str = "gemini-2.5-flash",
    scale_factor: str = None,
):
    """
    Run benchmarks for specified systems and use cases.

    Args:
        systems: List of system names to benchmark
        use_cases: List of use cases to run
        queries: Optional list of specific query IDs to run (e.g., [1, 5])
        skip_setup: Whether to skip setup phase
        model_name: Model name to use for systems that support it
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

            # Get runner class
            runner_class = get_runner_class(system, use_case)
            if not runner_class:
                print(f"Skipping {system} due to import error")
                continue

            # Initialize and run
            try:
                runner = runner_class(
                    use_case=use_case,
                    scale_factor=scale_factor,
                    skip_setup=skip_setup,
                    model_name=model_name,
                )
                system_metrics = runner.run_all_queries(queries=queries)

                # Convert metrics to serializable format
                # The metrics now contain the results (DataFrames) which we
                # don't serialize
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

    args = parser.parse_args()

    # Parse query IDs
    query_ids = None
    if args.queries:
        query_ids = parse_query_ids(args.queries)
        if not query_ids:
            print("Error: No valid query IDs provided")
            sys.exit(1)

    print("Multi-Modal Data Systems Benchmark")
    print(f"Systems: {', '.join(args.systems)}")
    print(f"Use cases: {', '.join(args.use_cases)}")
    print(f"Model: {args.model}")
    print(f"Queries: {', '.join(map(str, query_ids)) if query_ids else 'All'}")
    print(f"Scale factor: {args.scale_factor}")

    # Run benchmark
    results = run_benchmark(
        systems=args.systems,
        use_cases=args.use_cases,
        queries=query_ids,
        skip_setup=args.skip_setup,
        model_name=args.model,
        scale_factor=args.scale_factor,
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

    # Force terminate all threads including background ones (LOTUS connection
    # pools)
    os._exit(0)


if __name__ == "__main__":
    main()
