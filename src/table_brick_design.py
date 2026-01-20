"""
Created on September 17, 2025

@author: Andi, Jiale Lao

Enhanced table generation module for creating heatmap-based LaTeX tables
with error bars across multiple system evaluation rounds.
"""

import json
import numpy as np
from pathlib import Path
from matplotlib import colors
from natsort import natsorted


class BenchmarkTableGenerator:
    def __init__(self, base_dir="."):
        self.base_dir = Path(base_dir)
        self.files_dir = self.base_dir / "files"
        self.figures_dir = self.base_dir / "figures"

        # Create figures directory if it doesn't exist
        self.figures_dir.mkdir(exist_ok=True)

        # Define system colors (similar to plotting)
        self.system_colors = {
            "lotus": "#1f77b4",
            "palimpzest": "#ff7f0e",
            "thalamusdb": "#2ca02c",
            "caesura": "#d62728",
            "bigquery": "#9467bd",
            "snowflake": "#8c564b",
        }

        # Define operator mappings for each use case and query
        # F: Semantic Filter, J: Semantic Join, M: Semantic Map,
        # R: Semantic Rank, C: Semantic Classify, L: limit clause
        self.operator_mappings = {
            "movie": {
                "1": "F L",
                "2": "F L",
                "3": "F",
                "4": "F",
                "5": "J L",
                "6": "J L",
                "7": "J",
                "8": "C",
                "9": "R",
                "10": "R",
            },
            "detective": {
                # All queries use J for detective
                "1": "J",
                "2": "J",
                "3": "J",
                "4": "J",
                "5": "J",
                "6": "J",
                "7": "J",
                "8": "J",
                "9": "J",
                "10": "J",
            },
            "animals": {
                "1": "F",
                "2": "F",
                "3": "F L",
                "4": "F L",
                "5": "F",
                "6": "F",
                "7": "F",
                "8": "F",
                "9": "F",
                "10": "F L",
            },
            "medical": {
                "1": "F",
                "2": "F",
                "3": "F L",
                "4": "F",
                "5": "F",
                "6": "F J",
                "7": "F",
                "8": "F L",
                "9": "F",
                "10": "C",
            },
            "cars": {
                "1": "F",
                "2": "F",
                "3": "F L",
                "4": "F",
                "5": "F",
                "6": "F J",
                "7": "F",
                "8": "F L",
                "9": "F",
                "10": "C",
            },
            "ecomm": {
                "1": "F",
                "2": "F",
                "3": "M",
                "4": "M",
                "5": "C",
                "6": "C",
                "7": "J",
                "8": "J",
                "9": "J",
                "10": "F J",
                "11": "F J",
                "12": "F M",
                "13": "F",
                "14": "F J R",
            },
            "mmqa": {
                "1": "M",
                "2a": "J",
                "2b": "J",
                "3a": "F",
                "3f": "F",
                "4": "M",
                "5": "M",
                "6a": "F",
                "6b": "F",
                "6c": "F",
                "7": "J",
            },
        }

    def get_system_color(self, system_name):
        """Get color for a system, similar to plotting module."""
        return self.system_colors.get(system_name.lower(), "#17becf")

    def unify_accuracy_metric(self, metric):
        """
        Unify different accuracy metrics into a single format.
        Returns (metric_type, accuracy_value).
        """
        if "metric_type" in metric and "accuracy" in metric:
            return metric["metric_type"], metric["accuracy"]
        elif "f1_score" in metric:
            return "f1_score", metric["f1_score"]
        elif "relative_error" in metric:
            return "relative_error", (
                1 / (1 + metric["relative_error"])
                if metric["relative_error"] is not None
                else None
            )
        elif "spearman_correlation" in metric:
            return "spearman_correlation", metric["spearman_correlation"]
        else:
            return None, None

    def load_aggregated_metrics_across_rounds(self, use_case, model_tag):
        """
        Load metrics data from multiple round folders and aggregate them.
        Auto-detects folders with pattern: across_system_{model_tag}_{round_number}
        Returns aggregated data with means and standard deviations.
        """
        # Auto-detect round folders
        base_dir = self.files_dir / use_case / "metrics"
        round_folders = []

        for i in range(1, 6):  # rounds 1-5
            round_folder = f"across_system_{model_tag}_{i}"
            round_path = base_dir / round_folder
            if round_path.exists():
                round_folders.append(round_folder)

        if not round_folders:
            print(f"No round folders found for across_system_{model_tag}")
            return {}, [], []

        print(f"Found {len(round_folders)} round folders: {round_folders}")

        # Load metrics data from all rounds
        all_round_data = {}  # {round: {system: metrics}}
        systems = set()

        for round_folder in round_folders:
            data_dir = base_dir / round_folder
            round_data = {}

            for json_file in data_dir.glob("*.json"):
                system_name = json_file.stem
                systems.add(system_name)
                try:
                    with open(json_file, "r") as f:
                        round_data[system_name] = json.load(f)
                    print(
                        f"Loaded metrics for {system_name} from {round_folder}"
                    )
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

            all_round_data[round_folder] = round_data

        if not all_round_data or not systems:
            print("No valid data found across rounds!")
            return {}, [], []

        systems = sorted(systems)

        # Collect all query IDs
        all_query_ids = set()
        for round_data in all_round_data.values():
            for system_data in round_data.values():
                for query_key in system_data.keys():
                    try:
                        query_id = query_key.replace("Q", "")
                        all_query_ids.add(query_id)
                    except ValueError:
                        continue

        query_ids = sorted(all_query_ids)
        print(f"Found {len(query_ids)} queries: {query_ids}")
        print(f"Found {len(systems)} systems: {systems}")

        # Aggregate data across rounds
        aggregated_data = (
            {}
        )  # {system: {query: {metric: [values_across_rounds]}}}

        for sys_name in systems:
            aggregated_data[sys_name] = {}
            for qid in query_ids:
                aggregated_data[sys_name][qid] = {
                    "money_cost": [],
                    "execution_time": [],
                    "quality": [],
                }

                # Collect values from all rounds
                for round_folder, round_data in all_round_data.items():
                    if sys_name in round_data:
                        query_data = round_data[sys_name].get(f"Q{qid}", {})

                        # Check if this system supports this query (money_cost > 0)
                        cost = query_data.get("money_cost", 0)
                        system_supports_query = cost > 0

                        if system_supports_query:
                            # Money cost
                            aggregated_data[sys_name][qid]["money_cost"].append(
                                cost
                            )

                            # Execution time
                            latency = query_data.get("execution_time", 0)
                            if latency > 0:
                                aggregated_data[sys_name][qid][
                                    "execution_time"
                                ].append(latency)

                            # Quality metric
                            value = None
                            if "accuracy" in query_data:
                                value = query_data["accuracy"]
                            elif "f1_score" in query_data:
                                value = query_data["f1_score"]
                            elif "relative_error" in query_data:
                                rel_err = query_data["relative_error"]
                                value = (
                                    1 / (1 + rel_err)
                                    if rel_err is not None
                                    else None
                                )
                            elif "spearman_correlation" in query_data:
                                value = query_data["spearman_correlation"]

                            if value is not None:
                                aggregated_data[sys_name][qid][
                                    "quality"
                                ].append(value)

        return aggregated_data, systems, query_ids

    def calculate_statistics(self, values):
        """Calculate mean and standard deviation from a list of values."""
        if len(values) == 0:
            return None, None
        elif len(values) == 1:
            return values[0], 0.0
        else:
            return np.mean(values), np.std(values)

    def latex_float(self, f):
        """Format float for LaTeX scientific notation."""
        float_str = "{0:.0e}".format(f)
        if "e" in float_str:
            base, exponent = float_str.split("e")
            return r"{0}${{\cdot\scriptstyle 10^{{{1}}}}}$".format(
                base, int(exponent)
            )
        else:
            return float_str

    def format_value_with_error(self, mean_val, std_val, metric_type="cost"):
        """Format value with error bar using ± notation."""
        if mean_val is None:
            return "\\fancyCellRed{n/a}"

        if metric_type == "cost":
            if round(mean_val, 2) > 0.0:
                mean_str = f"\\${mean_val:.2f}"
            else:
                mean_str = f"\\${self.latex_float(mean_val)}"
        elif metric_type == "time":
            if mean_val >= 1.0:
                mean_str = f"{mean_val:.1f}s"
            else:
                mean_str = f"{mean_val:.2f}s"
        else:  # quality
            mean_str = f"{mean_val:.2f}"

        if std_val is not None and std_val > 0:
            if metric_type == "cost":
                if round(std_val, 2) > 0.0:
                    std_str = f"{std_val:.2f}"
                else:
                    std_str = f"{self.latex_float(std_val)}"
                return f"{mean_str} \\pm \\${std_str}"
            elif metric_type == "time":
                if std_val >= 1.0:
                    std_str = f"{std_val:.1f}s"
                else:
                    std_str = f"{std_val:.2f}s"
                return f"{mean_str} \\pm {std_str}"
            else:  # quality
                return f"{mean_str} \\pm {std_val:.2f}"
        else:
            return mean_str

    def format_value_with_error_math(
        self, mean_val, std_val, metric_type="cost"
    ):
        """Format value with error bar using ± notation for math mode."""
        if mean_val is None:
            return "\\fancyCellRed{n/a}"

        if metric_type == "cost":
            if round(mean_val, 2) > 0.0:
                mean_str = f"\\${mean_val:.2f}"
            else:
                mean_str = f"\\${self.latex_float(mean_val)}"
        elif metric_type == "time":
            if mean_val >= 1.0:
                mean_str = f"{mean_val:.1f}\\,\\text{{s}}"
            else:
                mean_str = f"{mean_val:.2f}\\,\\text{{s}}"
        else:  # quality
            mean_str = f"{mean_val:.2f}"

        if std_val is not None and std_val > 0:
            if metric_type == "cost":
                if round(std_val, 2) > 0.0:
                    std_str = f"{std_val:.2f}"
                else:
                    std_str = f"{self.latex_float(std_val)}"
                return f"{mean_str} \\pm \\${std_str}"
            elif metric_type == "time":
                if std_val >= 1.0:
                    std_str = f"{std_val:.1f}\\,\\text{{s}}"
                else:
                    std_str = f"{std_val:.2f}\\,\\text{{s}}"
                return f"{mean_str} \\pm {std_str}"
            else:  # quality
                return f"{mean_str} \\pm {std_val:.2f}"
        else:
            return mean_str

    def generate_heatmap_table_extended(self, use_case, model_tag):
        """
        Generate enhanced heatmap-based LaTeX table with explicit column headers
        and error bars for cost, quality, and latency metrics.
        """
        # Load aggregated data across rounds
        aggregated_data, systems, query_ids = (
            self.load_aggregated_metrics_across_rounds(use_case, model_tag)
        )

        if not aggregated_data:
            print(f"No data found for {use_case} with model {model_tag}")
            return

        # Convert use case name for display
        special_cases = {
            "animals": "Wildlife",
            "mmqa": "MMQA",
            "ecomm": "E-Commerce",
        }

        if use_case in special_cases:
            display_use_case = special_cases[use_case]
        else:
            display_use_case = use_case.capitalize()

        # Filter systems for the table (based on reference code)
        selected_systems = [
            "LOTUS",
            "Palimpzest",
            "ThalamusDB",
            # "CAESURA",
            "BigQuery",
            # "Snowflake",
        ]

        # Only include systems that exist in our data
        available_systems = [
            s
            for s in selected_systems
            if s.lower() in [sys.lower() for sys in systems]
        ]

        query_ids = natsorted([f"Q{qid}" for qid in query_ids])

        # Set up output directory and file
        across_system_folder = f"across_system_{model_tag}"
        output_dir = self.figures_dir / use_case / across_system_folder
        output_dir.mkdir(exist_ok=True, parents=True)
        out_file_path = output_dir / f"heatmap_table_{use_case}_extended.tex"

        # Calculate statistics and prepare data similar to original implementation
        metrics_data = (
            {}
        )  # Convert to format similar to original: {system.lower(): {query_id: metrics}}
        plotting_data = []  # For normalization

        for sys_name in available_systems:
            sys_key = sys_name.lower()
            if sys_key not in [s.lower() for s in systems]:
                continue

            # Find the actual system name from the loaded data
            actual_sys_name = None
            for s in systems:
                if s.lower() == sys_key:
                    actual_sys_name = s
                    break

            if actual_sys_name is None:
                continue

            metrics_data[sys_key] = {}

            for query_id in query_ids:
                qid = query_id.replace("Q", "")
                query_data = aggregated_data[actual_sys_name][qid]

                # Calculate statistics for each metric
                cost_mean, cost_std = self.calculate_statistics(
                    query_data["money_cost"]
                )
                quality_mean, quality_std = self.calculate_statistics(
                    query_data["quality"]
                )
                latency_mean, latency_std = self.calculate_statistics(
                    query_data["execution_time"]
                )

                # Store in format similar to original
                if cost_mean is not None and cost_mean > 0:
                    metrics_data[sys_key][query_id] = {
                        "money_cost": cost_mean,
                        "money_cost_std": cost_std,
                        "execution_time": latency_mean,
                        "execution_time_std": latency_std,
                        "quality": quality_mean,
                        "quality_std": quality_std,
                    }

                    # Add accuracy in the original format
                    if quality_mean is not None:
                        metrics_data[sys_key][query_id][
                            "accuracy"
                        ] = quality_mean

                        # Calculate cost_accuracy_tradeoff
                        cost_accuracy = (
                            cost_mean / quality_mean
                            if quality_mean > 0
                            else float("nan")
                        )

                        # Store for plotting data normalization (similar to original)
                        plotting_data.append(
                            {
                                "system": sys_name,
                                "query_id": query_id,
                                "money_cost": cost_mean,
                                "accuracy": quality_mean,
                                "execution_time": latency_mean,
                                "cost_accuracy_tradeoff": cost_accuracy,
                            }
                        )

        # Convert to DataFrame for easier normalization
        import pandas as pd

        plotting_df = pd.DataFrame(plotting_data)

        # Write LaTeX table
        with open(out_file_path, "w") as tex_file:
            # Write header
            tex_file.write(
                f"%% This table is generated by table_2.py. Do not edit manually. %%\n"
            )

            # Table structure using the new format
            tex_file.write(f"\\begin{{table*}}[t]\n")
            tex_file.write(f"  \\centering\n")
            tex_file.write(f"  \\begin{{threeparttable}}\n")
            tex_file.write(
                f"  \\caption{{Experimental Results of SemBench for the {display_use_case} Scenario. Applied operators include: F - semantic filter, J - semantic join, M - semantic map, R - semantic rank, C - semantic classify, L - LIMIT clause. The colors express relative performance (\\protect\\fancycellGreen{{Better than Average}}, \\protect\\fancycellYellow{{Average}}, \\protect\\fancycellGray{{Worse than Average}}, and \\protect\\fancyCellRed{{...}} for not supported).}}\n"
            )
            tex_file.write(
                f"  \\label{{tab:experimental_results_{use_case}}}\n\n"
            )

            tex_file.write(f"  % Table formatting\n")
            tex_file.write(f"  \\begingroup\n")
            tex_file.write(f"  \\normalsize\n")
            tex_file.write(f"  \\setlength{{\\tabcolsep}}{{3.7pt}}\n")

            tex_file.write(f"  \\setlength{{\\aboverulesep}}{{0.0ex}}\n")
            tex_file.write(f"  \\setlength{{\\belowrulesep}}{{0.0ex}}\n")

            tex_file.write(f"  \\renewcommand{{\\arraystretch}}{{1.15}}\n\n")

            # Calculate column specification
            num_systems = len(available_systems)
            col_spec = (
                "l "
                + " c@{\hspace{0.25em}}c @{\hspace{0.25em}}c @{\hspace{1em}} "
                * (num_systems - 1)
                + "c@{\hspace{0.25em}}c @{\hspace{0.25em}}c"
            )
            tex_file.write(f"  % Force the table to exactly \\textwidth\n")
            tex_file.write(
                f"  \\begin{{tabular*}}{{\\textwidth}}{{@{{\\extracolsep{{\\fill}}}} {col_spec}}}\n"
            )
            tex_file.write(f"    \\toprule\n")

            # Header with system names (bold formatting)
            header_systems = []
            for i, system in enumerate(available_systems):
                header_systems.append(
                    f"\\multicolumn{{3}}{{c}}{{\\textbf{{{system}}}}}"
                )
            tex_file.write(f"      & {' & '.join(header_systems)} \\\\\n")

            # Cmidrule for each system
            cmidrules = []
            for i, system in enumerate(available_systems):
                start = 2 + i * 3
                end = start + 2
                cmidrules.append(f"\\cmidrule(lr){{{start}-{end}}}")
            tex_file.write(f"      {' '.join(cmidrules)}\n")

            # Sub-header with metric names
            subheader = []
            for system in available_systems:
                subheader.extend(
                    ["\\textbf{Cost}", "\\textbf{Quality}", "\\textbf{Latency}"]
                )
            tex_file.write(f"      & {' & '.join(subheader)} \\\\\n")
            tex_file.write(f"    \\midrule\n")
            tex_file.write(f"    \\addlinespace[0.3ex]\n")

            # Store table cells - back to single row per query
            table_cells = [
                ["\\fancyCellRed{n/a}"] * (1 + len(available_systems) * 3)
                for i in range(len(query_ids))
            ]

            # First column contains query ids with operator marks
            for query_idx, query_id in enumerate(query_ids):
                # Extract numeric query ID (e.g., "Q1" -> 1)
                query_num = query_id.replace("Q", "")

                # Get operator marks for this query in the current use case
                operators = ""
                if (
                    use_case in self.operator_mappings
                    and query_num in self.operator_mappings[use_case]
                ):
                    operators = self.operator_mappings[use_case][query_num]

                # Format as "Q1: FL" or just "Q1" if no operators found
                if operators:
                    table_cells[query_idx][
                        0
                    ] = f"\\textbf{{{query_id}:}} {operators}"
                else:
                    table_cells[query_idx][0] = query_id

            # Define color mapping (same as original)
            cmap = colors.LinearSegmentedColormap.from_list(
                "green_red",
                [
                    "limegreen",
                    "khaki",
                    "orange",
                    "crimson",
                ],  # "green_red", ["limegreen", "khaki", "red"]
            )

            cell_size = "3.3em"

            # Generate cells for each system (following original logic)
            for sys_idx, system in enumerate(available_systems):
                if system.lower() not in metrics_data:
                    continue  # there are no metrics for this system
                sys_metrics = metrics_data[system.lower()]

                for query_idx, query_id in enumerate(query_ids):
                    if query_id not in sys_metrics:
                        continue  # there are no metrics for this query
                    query_metrics = sys_metrics[query_id]

                    if (
                        "money_cost" in query_metrics
                        and "accuracy" in query_metrics
                        and not "error" in query_metrics
                    ):
                        cost = query_metrics["money_cost"]
                        cost_std = query_metrics.get("money_cost_std", 0)
                        accuracy = query_metrics["accuracy"]
                        accuracy_std = query_metrics.get("quality_std", 0)
                        latency = query_metrics.get("execution_time")
                        latency_std = query_metrics.get("execution_time_std", 0)

                        cost_accuracy = (
                            cost / accuracy if accuracy > 0 else float("nan")
                        )

                        # Normalize cost for coloring (same as original)
                        query_data_subset = plotting_df[
                            plotting_df["query_id"] == query_id
                        ]

                        def round_ext(f, digits):
                            if round(f, digits) > 0.0:
                                return round(f, digits)
                            else:
                                return f

                        min_cost = round_ext(
                            query_data_subset["money_cost"].min(), 2
                        )
                        max_cost = round_ext(
                            query_data_subset["money_cost"].max(), 2
                        )
                        cost_norm = (
                            (round_ext(cost, 2) - min_cost)
                            / (max_cost - min_cost)
                            if max_cost > min_cost
                            else 0.0
                        )

                        # Normalize accuracy for coloring (same as original)
                        min_accuracy = round_ext(
                            query_data_subset["accuracy"].min(), 2
                        )
                        max_accuracy = round_ext(
                            query_data_subset["accuracy"].max(), 2
                        )
                        accuracy_norm = (
                            (round_ext(accuracy, 2) - min_accuracy)
                            / (max_accuracy - min_accuracy)
                            if max_accuracy > min_accuracy
                            else 1.0
                        )

                        # Normalize latency for coloring
                        if latency is not None:
                            min_latency = round_ext(
                                query_data_subset["execution_time"].min(), 2
                            )
                            max_latency = round_ext(
                                query_data_subset["execution_time"].max(), 2
                            )
                            latency_norm = (
                                (round_ext(latency, 2) - min_latency)
                                / (max_latency - min_latency)
                                if max_latency > min_latency
                                else 0.0
                            )
                        else:
                            latency_norm = 1.0

                        # Generate colors (following original logic)
                        cost_color = colors.to_hex(cmap(cost_norm))

                        accuracy_color = colors.to_hex(
                            cmap.reversed()(accuracy * 2 - 1)
                        )
                        latency_color = colors.to_hex(cmap(latency_norm))

                        # Format values (no std displayed at query level)
                        cost_text = (
                            f"\\${cost:.2f}"
                            if round(cost, 2) > 0.0
                            else f"\\${self.latex_float(cost)}"
                        )
                        fancy_cell_class_accuracy = ""
                        if accuracy >= 0.8:
                            fancy_cell_class_accuracy = "fancycellGreen"
                        elif accuracy >= 0.6:
                            fancy_cell_class_accuracy = "fancycellYellow"
                        else:
                            fancy_cell_class_accuracy = "fancycellGray"


                        fancy_cell_class_cost = ""
                        if max_cost == min_cost:
                            if min_cost < 0.01:
                                fancy_cell_class_cost = "fancycellGreen"
                            elif min_cost < 0.10:
                                fancy_cell_class_cost = "fancycellYellow"
                            else:
                                fancy_cell_class_cost = "fancycellGray"

                        else:
                            if cost_norm <= 0.33:
                                fancy_cell_class_cost = "fancycellGreen"
                            elif cost_norm <= 0.66:
                                fancy_cell_class_cost = "fancycellYellow"
                            else:
                                fancy_cell_class_cost = "fancycellGray" 

                        fancy_cell_class_latency = ""
                        if max_latency == min_latency:
                            if min_latency < 0.01:
                                fancy_cell_class_latency = "fancycellGreen"
                            elif min_latency < 0.10:
                                fancy_cell_class_latency = "fancycellYellow"
                            else:
                                fancy_cell_class_latency = "fancycellGray"

                        else:
                            if latency_norm <= 0.33:
                                fancy_cell_class_latency = "fancycellGreen"
                            elif latency_norm <= 0.66:
                                fancy_cell_class_latency = "fancycellYellow"
                            else:
                                fancy_cell_class_latency = "fancycellGray" 

                        accuracy_text = f"{accuracy:.2f}"

                        if latency is not None:
                            if latency >= 1.0:
                                latency_text = f"{latency:.1f}\\,\\text{{s}}"
                            else:
                                latency_text = f"{latency:.2f}\\,\\text{{s}}"
                        else:
                            # latency_text = "\\text{n/a}"
                            latency_text = "\\fancyCellRed{n/a}"
                            latency_color = colors.to_hex(
                                cmap(1.0)
                            )  # worst color for missing data

                        # Create cells
                        # cost_cell = f"\\fancycell[{cell_size}]{{{{{"rgb:red,"+str(int(cost_color[0]*255))+";"+"green,"+str(int(cost_color[1]*255))+";"+"blue,"+str(int(cost_color[2]*255))}}}}}{{{cost_text}}}"
                        # accuracy_cell = f"\\fancycell[{cell_size}]{{{{{"rgb:red,"+str(int(accuracy_color[0]*255))+";"+"green,"+str(int(accuracy_color[1]*255))+";"+"blue,"+str(int(accuracy_color[2]*255))}}}}}{{{accuracy_text}}}"
                        # latency_cell = f"\\fancycell[{cell_size}]{{{{{"rgb:red,"+str(int(latency_color[0]*255))+";"+"green,"+str(int(latency_color[1]*255))+";"+"blue,"+str(int(latency_color[2]*255))}}}}}{{{latency_text}}}"

                        accuracy_cell = f"\\{fancy_cell_class_accuracy}{{{accuracy_text}}}"
                        cost_cell = f"\\{fancy_cell_class_cost}{{{cost_text}}}"
                        latency_cell = f"\\{fancy_cell_class_latency}{{{latency_text}}}"

                        # Insert into table (3 columns per system)
                        base_col = 1 + sys_idx * 3
                        table_cells[query_idx][base_col] = cost_cell
                        table_cells[query_idx][base_col + 1] = accuracy_cell
                        table_cells[query_idx][base_col + 2] = latency_cell

            # Write out table cells
            for row in table_cells:
                tex_file.write(f"    {' & '.join(row)} \\\\\n")

            # Add summary rows
            tex_file.write(f"    \\addlinespace[0.3ex]\n")
            tex_file.write(f"    \\midrule\n")
            tex_file.write(f"    \\addlinespace[0.3ex]\n")

            # Calculate and write average metrics row
            avg_row = ["\\textbf{Avg}"]

            for system in available_systems:
                if system.lower() not in metrics_data:
                    avg_row.extend(["--", "--", "--"])
                    continue

                sys_metrics = metrics_data[system.lower()]
                costs, qualities, latencies = [], [], []

                for query_id in query_ids:
                    if query_id in sys_metrics:
                        query_metrics = sys_metrics[query_id]
                        if (
                            "money_cost" in query_metrics
                            and query_metrics["money_cost"] is not None
                        ):
                            costs.append(query_metrics["money_cost"])
                        if (
                            "accuracy" in query_metrics
                            and query_metrics["accuracy"] is not None
                        ):
                            qualities.append(query_metrics["accuracy"])
                        if (
                            "execution_time" in query_metrics
                            and query_metrics["execution_time"] is not None
                        ):
                            latencies.append(query_metrics["execution_time"])

                # Calculate averages
                avg_cost = np.mean(costs) if costs else None
                avg_quality = np.mean(qualities) if qualities else None
                avg_latency = np.mean(latencies) if latencies else None

                # Format average values
                if avg_cost is not None:
                    if round(avg_cost, 2) > 0.0:
                        cost_text = (
                            f"\\fancycellNormal"
                            + "{"
                            + f"\\${avg_cost:.2f}"
                            + "}"
                        )
                    else:
                        cost_text = (
                            f"\\fancycellNormal"
                            + "{"
                            + f"\\${self.latex_float(avg_cost)}"
                            + "}"
                        )
                else:
                    cost_text = "--"

                if avg_quality is not None:
                    quality_text = (
                        f"\\fancycellNormal"
                        + "{"
                        + f"{avg_quality:.2f}"
                        + "}"
                    )
                else:
                    quality_text = (
                        f"\\fancycellNormal"
                        + "{"
                        + "--"
                        + "}"
                    )

                if avg_latency is not None:
                    if avg_latency >= 1.0:
                        latency_text = (
                            f"\\fancycellNormal"
                            + "{"
                            + f"{avg_latency:.1f}\\,\\text{{s}}"
                            + "}"
                        )
                    else:
                        latency_text = (
                            f"\\fancycellNormal"
                            + "{"
                            + f"{avg_latency:.2f}\\,\\text{{s}}"
                            + "}"
                        )
                else:
                    latency_text = "--"

                avg_row.extend(
                    [f"{cost_text}", f"{quality_text}", f"{latency_text}"]
                )

            tex_file.write(f"    {' & '.join(avg_row)} \\\\\n")

            # Calculate and write relative variance row (as standard deviation percentages)
            std_row = ["\\textbf{Std Dev}"]

            for system in available_systems:
                if system.lower() not in metrics_data:
                    std_row.extend(["--", "--", "--"])
                    continue

                sys_metrics = metrics_data[system.lower()]
                cost_vars, quality_vars, latency_vars = [], [], []

                for query_id in query_ids:
                    if query_id in sys_metrics:
                        query_metrics = sys_metrics[query_id]

                        # Cost relative variance
                        cost = query_metrics.get("money_cost")
                        cost_std = query_metrics.get("money_cost_std")
                        if (
                            cost is not None
                            and cost_std is not None
                            and cost > 0
                        ):
                            cost_vars.append(cost_std / cost)

                        # Quality relative variance
                        quality = query_metrics.get("accuracy")
                        quality_std = query_metrics.get("quality_std")
                        if (
                            quality is not None
                            and quality_std is not None
                            and quality > 0
                        ):
                            quality_vars.append(quality_std / quality)

                        # Latency relative variance
                        latency = query_metrics.get("execution_time")
                        latency_std = query_metrics.get("execution_time_std")
                        if (
                            latency is not None
                            and latency_std is not None
                            and latency > 0
                        ):
                            latency_vars.append(latency_std / latency)

                # Calculate average relative variances
                avg_cost_var = np.mean(cost_vars) if cost_vars else None
                avg_quality_var = (
                    np.mean(quality_vars) if quality_vars else None
                )
                avg_latency_var = (
                    np.mean(latency_vars) if latency_vars else None
                )

                # Format relative variance values (as percentages)
                if avg_cost_var is not None:
                    cost_var_text = f"{avg_cost_var * 100:.1f}\\%"
                else:
                    cost_var_text = "--"

                if avg_quality_var is not None:
                    quality_var_text = f"{avg_quality_var * 100:.1f}\\%"
                else:
                    quality_var_text = "--"

                if avg_latency_var is not None:
                    latency_var_text = f"{avg_latency_var * 100:.1f}\\%"
                else:
                    latency_var_text = "--"

                std_row.extend(
                    [
                        f"\\(\\pm{cost_var_text}\\)",
                        f"\\(\\pm{quality_var_text}\\)",
                        f"\\(\\pm{latency_var_text}\\)",
                    ]
                )

            tex_file.write(f"    {' & '.join(std_row)} \\\\\n")

            tex_file.write(f"    \\bottomrule\n")
            tex_file.write(f"  \\end{{tabular*}}\n")
            tex_file.write(f"  \\endgroup\n")
            tex_file.write(f"  \n")
            tex_file.write(f"  \\end{{threeparttable}}\n")
            tex_file.write(f"\\end{{table*}}\n")

        print(f"✅ Saved extended heatmap table to {out_file_path}")


def main():
    """Example usage of the table generator."""
    generator = BenchmarkTableGenerator()

    # Example: Generate tables for different use cases and model tags
    use_cases = [
        "movie",
        "detective",
        "animals",
        "medical",
        "ecomm",
        "mmqa"
        "cars"
    ]  # Add more as needed
    model_tag = "2.5flash"  # Or whatever model tag you're using

    for use_case in use_cases:
        if use_case == "mmqa":
            model_tag = "gemini-2.5-flash"
        
        print(f"\nGenerating extended heatmap table for {use_case}...")
        generator.generate_heatmap_table_extended(use_case, model_tag)


if __name__ == "__main__":
    main()
