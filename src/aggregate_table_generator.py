#!/usr/bin/env python3
"""
Aggregate Table Generator for SemBench

Combines logic from aggregate_analysis.py and table_brick_design.py to generate
LaTeX tables with:
- Rows: Operator types (SEM_FILTER, SEM_JOIN, SEM_MAP, SEM_SCORE, SEM_CLASSIFY)
- Columns: For each system, two sub-columns (Quality/Latency, Quality/Money)

Created by combining existing modules and enhancing functionality.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Tuple
from matplotlib import colors
from natsort import natsorted


class AggregateTableGenerator:
    def __init__(self, base_path: str = "./files", only_common_queries: bool = True, use_repeat_folders: bool = False):
        self.base_path = Path(base_path)
        self.figures_dir = Path("./figures")
        self.figures_dir.mkdir(exist_ok=True)

        # Snowflake and BigQuery inclusion settings
        self.include_snowflake = False
        self.include_bigquery = True

        # Only use queries supported by all systems
        self.only_common_queries = only_common_queries

        # Use repeat folders (across_system_{tag}_{sf}_repeat{i}) vs original (_i)
        self.use_repeat_folders = use_repeat_folders

        # Scale factor mappings for repeat folder mode
        self.sf_mappings = {
            "animals": "sf200",
            "cars": "sf19672",
            "ecomm": "sf500",
            "mmqa": "sf200",
            "movie": "sf2000",
        }

        # Define query groupings by operator type (from aggregate_analysis.py)
        
        # all queries, excluding multi-semantic-operator queries
        self.operator_queries = {
            'SEM_CLASSIFY': {
                'ecomm': ['Q5', 'Q6'],
                'cars': ['Q10'],
                'mmqa': ['Q4']
            },
            'SEM_FILTER': {
                'ecomm': ['Q1', 'Q13', 'Q2'],
                'cars': ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9'],
                'mmqa': ['Q3a', 'Q3f', 'Q6a', 'Q6b', 'Q6c'],
                'movie': ['Q1', 'Q2', 'Q3', 'Q4', 'Q8'],
                'animals': ['Q1', 'Q10', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9']
            },
            'SEM_JOIN': {
                'ecomm': ['Q7', 'Q8', 'Q9'],
                'mmqa': ['Q2a', 'Q2b', 'Q7'],
                'movie': ['Q5', 'Q6', 'Q7']
            },
            'SEM_MAP': {
                'ecomm': ['Q3', 'Q4'],
                'mmqa': ['Q1', 'Q4', 'Q5']
            },
            'SEM_SCORE': {
                'movie': ['Q10', 'Q9']
            }
        }
        
        # queries without limit
        # self.operator_queries = {
        #     'SEM_CLASSIFY': {
        #         'ecomm': ['Q5', 'Q6'],
        #         'cars': ['Q10'],
        #         'mmqa': ['Q4']
        #     },
        #     'SEM_FILTER': {
        #         'ecomm': ['Q1', 'Q13', 'Q2'],
        #         'cars': ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9'],
        #         'mmqa': ['Q3a', 'Q3f', 'Q6a', 'Q6b', 'Q6c'],
        #         'movie': ['Q3', 'Q4', 'Q8'],
        #         'animals': ['Q1', 'Q2', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9']
        #     },
        #     'SEM_JOIN': {
        #         'ecomm': ['Q7', 'Q8', 'Q9'],
        #         'mmqa': ['Q2a', 'Q2b', 'Q7'],
        #         'movie': ['Q7']
        #     },
        #     'SEM_MAP': {
        #         'ecomm': ['Q3', 'Q4'],
        #         'mmqa': ['Q1', 'Q4', 'Q5']
        #     },
        #     'SEM_SCORE': {
        #         'movie': ['Q10', 'Q9']
        #     }
        # }

        # System colors
        self.system_colors = {
            "lotus": "#1f77b4",
            "palimpzest": "#ff7f0e",
            "thalamusdb": "#2ca02c",
            "caesura": "#d62728",
            "bigquery": "#9467bd",
            "snowflake": "#8c564b",
        }

        # Available scenarios and systems (will be populated by scanning)
        self.scenarios = []
        self.systems = []
        self.data = {}  # scenario -> system -> query -> metrics

    def scan_available_data(self, model_tag="2.5flash"):
        """Scan the file system to determine available scenarios and systems.

        Looks for repeat directories like across_system_2.5flash_1, _2, ..., _5
        Also handles alternative naming like across_system_gemini-2.5-flash_1, etc.
        """
        self.scenarios = []
        self.systems = set()
        self.repeat_dirs = {}  # scenario -> list of repeat directory paths

        # Define model tag variants to search for
        # Some scenarios use "gemini-2.5-flash" instead of "2.5flash"
        model_tag_variants = [model_tag]
        if model_tag == "2.5flash":
            model_tag_variants.append("gemini-2.5-flash")

        for scenario_dir in self.base_path.iterdir():
            if scenario_dir.is_dir():
                metrics_base = scenario_dir / "metrics"
                if not metrics_base.exists():
                    continue

                # Look for repeat directories with any of the model tag variants
                repeat_dirs = []
                scenario_name = scenario_dir.name

                if self.use_repeat_folders:
                    sf = self.sf_mappings.get(scenario_name)
                    if sf is None:
                        continue  # skip scenarios without sf mapping in repeat mode
                    for tag_variant in model_tag_variants:
                        for i in range(1, 10):
                            repeat_dir = metrics_base / f"across_system_{tag_variant}_{sf}_repeat{i}"
                            if repeat_dir.exists():
                                repeat_dirs.append(repeat_dir)
                        if repeat_dirs:
                            break
                else:
                    for tag_variant in model_tag_variants:
                        for i in range(1, 10):  # Check _1 through _9
                            repeat_dir = metrics_base / f"across_system_{tag_variant}_{i}"
                            if repeat_dir.exists():
                                repeat_dirs.append(repeat_dir)
                        # Stop if we found repeats with this variant
                        if repeat_dirs:
                            break

                    # Also check for standard directory without suffix as fallback
                    if not repeat_dirs:
                        for tag_variant in model_tag_variants:
                            standard_metrics = metrics_base / f"across_system_{tag_variant}"
                            if standard_metrics.exists():
                                repeat_dirs.append(standard_metrics)
                                break

                if repeat_dirs:
                    self.scenarios.append(scenario_dir.name)
                    self.repeat_dirs[scenario_dir.name] = repeat_dirs

                    # Check available systems from first repeat dir
                    for system_file in repeat_dirs[0].glob("*.json"):
                        system_name = system_file.stem
                        # Skip memory files
                        if "_memory" in system_name:
                            continue
                        if system_name == "snowflake" and not self.include_snowflake:
                            pass
                        elif system_name == "bigquery" and not self.include_bigquery:
                            pass
                        else:
                            self.systems.add(system_name)

        self.systems = sorted(list(self.systems))
        self.scenarios = sorted(self.scenarios)

        print(f"Found scenarios: {self.scenarios}")
        print(f"Found systems: {self.systems}")
        for scenario, dirs in self.repeat_dirs.items():
            print(f"  {scenario}: {len(dirs)} repeat(s)")

    def load_data(self, model_tag="2.5flash"):
        """Load all metrics data from JSON files and average across repeats.

        For each query, averages execution_time, money_cost, and quality metrics
        across all available repeats. Only includes repeats where all three metrics
        are valid (time > 0, cost > 0, quality >= 0).
        """
        self.data = defaultdict(lambda: defaultdict(dict))

        for scenario in self.scenarios:
            repeat_dirs = self.repeat_dirs.get(scenario, [])
            if not repeat_dirs:
                continue

            for system in self.systems:
                # Collect data from all repeats
                all_repeats_data = []
                for repeat_dir in repeat_dirs:
                    json_file = repeat_dir / f"{system}.json"
                    if json_file.exists():
                        try:
                            with open(json_file, 'r') as f:
                                repeat_data = json.load(f)
                                all_repeats_data.append(repeat_data)
                        except Exception as e:
                            print(f"Error loading {json_file}: {e}")

                if not all_repeats_data:
                    continue

                # Average metrics across repeats for each query
                averaged_data = self._average_metrics_across_repeats(all_repeats_data)
                self.data[scenario][system] = averaged_data

        print(f"Loaded data for {len(self.data)} scenarios")

    def _average_metrics_across_repeats(self, all_repeats_data: List[Dict]) -> Dict:
        """Average metrics across multiple repeat runs for each query.

        Args:
            all_repeats_data: List of dicts, each containing query -> metrics

        Returns:
            Dict of query -> averaged metrics
        """
        # Collect all queries across all repeats
        all_queries = set()
        for repeat_data in all_repeats_data:
            all_queries.update(repeat_data.keys())

        averaged_data = {}

        for query in all_queries:
            # Collect metrics from all repeats for this query
            execution_times = []
            money_costs = []
            qualities = []  # Will store (metric_name, value) tuples
            quality_metric_name = None
            statuses = []

            for repeat_data in all_repeats_data:
                if query not in repeat_data:
                    continue

                query_metrics = repeat_data[query]
                statuses.append(query_metrics.get('status', 'unknown'))

                # Only collect metrics from successful runs
                if query_metrics.get('status') != 'success':
                    continue

                # Extract all three metrics for this repeat
                exec_time = query_metrics.get('execution_time', 0)
                money = query_metrics.get('money_cost', 0)

                # Determine quality value and metric name
                quality_value = None
                current_quality_metric_name = None
                if 'f1_score' in query_metrics and query_metrics['f1_score'] is not None:
                    quality_value = query_metrics['f1_score']
                    current_quality_metric_name = 'f1_score'
                elif 'accuracy' in query_metrics and query_metrics['accuracy'] is not None:
                    quality_value = query_metrics['accuracy']
                    current_quality_metric_name = 'accuracy'
                elif 'relative_error' in query_metrics and query_metrics['relative_error'] is not None:
                    quality_value = query_metrics['relative_error']
                    current_quality_metric_name = 'relative_error'
                elif 'spearman_correlation' in query_metrics and query_metrics['spearman_correlation'] is not None:
                    quality_value = query_metrics['spearman_correlation']
                    current_quality_metric_name = 'spearman_correlation'

                # Only include this repeat if ALL three metrics are valid:
                # - execution_time must be > 0
                # - money_cost must be > 0
                # - quality must not be None (quality can be 0, which is valid)
                # This ensures consistent averaging across all metrics
                has_valid_time = exec_time and exec_time > 0
                has_valid_cost = money and money > 0
                has_valid_quality = quality_value is not None

                if has_valid_time and has_valid_cost and has_valid_quality:
                    execution_times.append(exec_time)
                    money_costs.append(money)
                    qualities.append(quality_value)
                    quality_metric_name = current_quality_metric_name

            # Determine overall status (success if any repeat succeeded)
            overall_status = 'success' if 'success' in statuses else (statuses[0] if statuses else 'unknown')

            # Build averaged metrics
            averaged_query = {'status': overall_status}

            if execution_times:
                averaged_query['execution_time'] = np.mean(execution_times)

            if money_costs:
                averaged_query['money_cost'] = np.mean(money_costs)

            if qualities and quality_metric_name:
                averaged_query[quality_metric_name] = np.mean(qualities)

            averaged_data[query] = averaged_query

        return averaged_data

    def filter_queries_by_support(self, operator_queries: Dict, systems: List[str]) -> Dict:
        """
        For each operator, filter queries to only include those supported by all systems
        that support at least one query for that operator.

        Returns: filtered operator_queries dict
        """
        if not self.only_common_queries:
            return operator_queries

        filtered_operator_queries = {}

        for operator_type, operator_scenarios in operator_queries.items():
            # First, find which systems support at least one query for this operator
            supporting_systems_for_operator = self.get_systems_supporting_operator(
                operator_type, operator_scenarios
            )

            filtered_operator_queries[operator_type] = {}

            for scenario, queries in operator_scenarios.items():
                if scenario not in self.data:
                    continue

                scenario_systems = self.data[scenario]
                common_queries = []

                for query in queries:
                    # Check if this query is successfully supported by all systems
                    # that support this operator (not all systems in general)
                    supported_by_all_relevant = True
                    for system in supporting_systems_for_operator:
                        if system not in scenario_systems:
                            supported_by_all_relevant = False
                            break
                        if query not in scenario_systems[system]:
                            supported_by_all_relevant = False
                            break
                        if scenario_systems[system][query].get('status') != 'success':
                            supported_by_all_relevant = False
                            break

                    if supported_by_all_relevant:
                        common_queries.append(query)

                if common_queries:
                    filtered_operator_queries[operator_type][scenario] = common_queries

        return filtered_operator_queries

    def extract_metrics(self, query_data: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Extract the three main metrics: execution_time, money_cost, quality
        For quality, use f1_score, transformed relative_error, or spearman_correlation
        """
        execution_time = query_data.get('execution_time', float('inf'))
        money_cost = query_data.get('money_cost', float('inf'))

        # Determine quality metric
        quality = 0.0
        if 'f1_score' in query_data:
            quality = query_data['f1_score']
        elif 'accuracy' in query_data:
            quality = query_data['accuracy']
        elif 'relative_error' in query_data:
            # Transform relative error: 1/(1 + relative_error)
            relative_error = query_data['relative_error']
            quality = 1.0 / (1.0 + relative_error)
        elif 'spearman_correlation' in query_data:
            # Assume correlation is positive
            quality = max(0.0, query_data['spearman_correlation'])

        return execution_time, money_cost, quality

    def get_systems_supporting_operator(self, operator_type: str, operator_scenarios: Dict) -> List[str]:
        """
        Get list of systems that support at least one query for this operator type.
        Returns: List of system names
        """
        supporting_systems = set()

        for scenario, queries in operator_scenarios.items():
            if scenario not in self.data:
                continue

            scenario_systems = self.data[scenario]

            for query in queries:
                for system in self.systems:
                    if system in scenario_systems and query in scenario_systems[system]:
                        if scenario_systems[system][query].get('status') == 'success':
                            supporting_systems.add(system)

        return sorted(list(supporting_systems))

    def calculate_operator_aggregates(self, filtered_queries: Dict = None) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Calculate aggregated metrics for each operator type and system.
        Returns: {operator_type: {system: {metric: avg_value, supporting_systems: [list]}}}
        """
        operator_queries_to_use = filtered_queries if filtered_queries else self.operator_queries
        operator_stats = {}

        for operator_type, operator_scenarios in operator_queries_to_use.items():
            operator_stats[operator_type] = {}

            # Get systems that support this operator
            supporting_systems = self.get_systems_supporting_operator(operator_type, operator_scenarios)

            for system in self.systems:
                operator_stats[operator_type][system] = {
                    'execution_time': [],
                    'money_cost': [],
                    'quality': [],
                    'is_supported': system in supporting_systems
                }

            # Collect values for each system in this operator type
            for scenario, queries in operator_scenarios.items():
                if scenario not in self.data:
                    continue

                scenario_systems = self.data[scenario]

                for query in queries:
                    for system in self.systems:
                        if system in scenario_systems and query in scenario_systems[system]:
                            query_data = scenario_systems[system][query]
                            if query_data.get('status') == 'success':
                                execution_time, money_cost, quality = self.extract_metrics(query_data)

                                # Only include query if ALL three metrics are valid:
                                # - execution_time must be > 0 (finite and positive)
                                # - money_cost must be > 0 (finite and positive)
                                # - quality can be >= 0 (including 0, which is a valid quality score)
                                # This ensures consistent averaging across all metrics
                                has_valid_time = execution_time != float('inf') and execution_time > 0
                                has_valid_cost = money_cost != float('inf') and money_cost > 0
                                has_valid_quality = quality >= 0  # quality can be 0

                                if has_valid_time and has_valid_cost and has_valid_quality:
                                    operator_stats[operator_type][system]['execution_time'].append(execution_time)
                                    operator_stats[operator_type][system]['money_cost'].append(money_cost)
                                    operator_stats[operator_type][system]['quality'].append(quality)

        # Calculate averages
        for operator_type in operator_stats:
            for system in self.systems:
                for metric in ['execution_time', 'money_cost', 'quality']:
                    values = operator_stats[operator_type][system][metric]
                    if values:
                        operator_stats[operator_type][system][f'{metric}_avg'] = np.mean(values)
                        operator_stats[operator_type][system][f'{metric}_std'] = np.std(values)
                    else:
                        operator_stats[operator_type][system][f'{metric}_avg'] = None
                        operator_stats[operator_type][system][f'{metric}_std'] = None

        return operator_stats

    def latex_float(self, f):
        """Format float for LaTeX scientific notation."""
        float_str = "{0:.0e}".format(f)
        if "e" in float_str:
            base, exponent = float_str.split("e")
            return r"{0}{{\cdot\scriptstyle 10^{{{1}}}}}".format(
                base, int(exponent)
            )
        else:
            return float_str

    def get_operators_supported_by_all_systems(self, operator_stats: Dict, available_systems: List[str]) -> List[str]:
        """
        Get list of operators supported by all systems.
        Returns: List of operator names
        """
        common_operators = []

        for operator_type in operator_stats:
            # Check if all systems support this operator
            supported_by_all = True
            for system in available_systems:
                if not operator_stats[operator_type][system].get('is_supported', False):
                    supported_by_all = False
                    break

            if supported_by_all:
                common_operators.append(operator_type)

        return common_operators

    def calculate_efficiency_metrics(self, operator_stats: Dict) -> Dict:
        """
        Calculate Quality/Latency and Quality/Money metrics.
        Returns: {operator_type: {system: {quality_per_second, quality_per_dollar}}}
        """
        efficiency_metrics = {}

        for operator_type, systems_data in operator_stats.items():
            efficiency_metrics[operator_type] = {}

            for system, metrics in systems_data.items():
                quality_avg = metrics.get('quality_avg')
                execution_time_avg = metrics.get('execution_time_avg')
                money_cost_avg = metrics.get('money_cost_avg')

                quality_per_second = None
                quality_per_dollar = None

                # Quality can be 0 (valid score), time and cost must be > 0 to avoid division by zero
                if quality_avg is not None and quality_avg >= 0:
                    if execution_time_avg is not None and execution_time_avg > 0:
                        quality_per_second = quality_avg / execution_time_avg

                    if money_cost_avg is not None and money_cost_avg > 0:
                        quality_per_dollar = quality_avg / money_cost_avg

                efficiency_metrics[operator_type][system] = {
                    'quality_per_second': quality_per_second,
                    'quality_per_dollar': quality_per_dollar,
                    'quality_avg': quality_avg,
                    'execution_time_avg': execution_time_avg,
                    'money_cost_avg': money_cost_avg
                }

        return efficiency_metrics

    def count_operator_queries(self, filtered_queries: Dict, available_systems: List[str]) -> Dict[str, Dict]:
        """
        Count total queries and supported queries per operator and system.

        Args:
            filtered_queries: The filtered operator_queries dict
            available_systems: List of system names to count for

        Returns: {operator_type: {'total': int, 'by_system': {system: int}}}
        """
        counts = {}

        for operator_type, operator_scenarios in filtered_queries.items():
            total_queries = 0
            by_system = {system: 0 for system in available_systems}

            for scenario, queries in operator_scenarios.items():
                total_queries += len(queries)

                if scenario not in self.data:
                    continue

                scenario_systems = self.data[scenario]

                for query in queries:
                    for system in available_systems:
                        if system in scenario_systems and query in scenario_systems[system]:
                            query_data = scenario_systems[system][query]
                            if query_data.get('status') == 'success':
                                by_system[system] += 1

            counts[operator_type] = {
                'total': total_queries,
                'by_system': by_system
            }

        return counts

    def generate_latex_table(self, model_tag="2.5flash", output_filename="aggregate_operator_table.tex"):
        """
        Generate LaTeX table with operator types as rows and systems with metrics as columns.
        Shows Queries (X/Y), Quality, Latency, and Cost for each system.
        """
        # Scan and load data
        self.scan_available_data(model_tag)
        self.load_data(model_tag)

        # Define system display order
        selected_systems = ["lotus", "palimpzest", "thalamusdb", "bigquery"]
        available_systems = [s for s in selected_systems if s in self.systems]

        # Filter queries if needed
        filtered_queries = self.operator_queries
        if self.only_common_queries:
            filtered_queries = self.filter_queries_by_support(self.operator_queries, available_systems)
            print(f"Filtered to common queries only")

        # Calculate aggregates
        operator_stats = self.calculate_operator_aggregates(filtered_queries)
        efficiency_metrics = self.calculate_efficiency_metrics(operator_stats)

        # Count queries per operator and system
        query_counts = self.count_operator_queries(filtered_queries, available_systems)

        # Operator order
        operator_order = ['SEM_FILTER', 'SEM_JOIN', 'SEM_MAP', 'SEM_SCORE', 'SEM_CLASSIFY']

        # Get operators supported by all systems
        common_operators = self.get_operators_supported_by_all_systems(operator_stats, available_systems)

        print(f"\nOperators supported by all systems: {common_operators}")
        print(f"All operators: {[op for op in operator_order if op in efficiency_metrics]}")

        # Print which systems support each operator
        if self.only_common_queries:
            print("\nPer-operator system support (filtering queries to common ones):")
            for operator_type in operator_order:
                if operator_type in operator_stats:
                    supporting = [s for s in available_systems if operator_stats[operator_type][s].get('is_supported', False)]
                    print(f"  {operator_type}: {supporting}")

        # Create output file
        output_path = self.figures_dir / output_filename

        with open(output_path, 'w') as tex_file:
            # Write header
            tex_file.write("%% This table is generated by aggregate_table_generator.py. Do not edit manually. %%\n")
            tex_file.write("\\begin{table*}[t]\n")
            tex_file.write("  \\centering\n")
            tex_file.write("  \\begin{threeparttable}\n")

            caption = "Aggregated Results by Operator Type. Each cell shows: Quality, Latency (seconds), and Cost (dollars). "
            caption += "Colors indicate relative performance within each row (\\protect\\fancycellGreen{Best 33\\%}, \\protect\\fancycellYellow{Middle 33\\%}, \\protect\\fancycellGray{Worst 33\\%})."
            if self.only_common_queries:
                caption += " For each operator, only queries supported by all systems that support that operator are included."

            tex_file.write(f"  \\caption{{{caption}}}\n")
            tex_file.write("  \\label{tab:aggregate_operator_results}\n\n")

            tex_file.write("  % Table formatting\n")
            tex_file.write("  \\begingroup\n")
            tex_file.write("  \\small\n")
            tex_file.write("  \\setlength{\\tabcolsep}{2pt}\n")
            tex_file.write("  \\setlength{\\aboverulesep}{0.0ex}\n")
            tex_file.write("  \\setlength{\\belowrulesep}{0.0ex}\n")
            tex_file.write("  \\renewcommand{\\arraystretch}{1.2}\n\n")

            # System names display mapping
            system_names_display = {
                'lotus': 'LOTUS',
                'palimpzest': 'Palimpzest',
                'thalamusdb': 'ThalamusDB',
                'bigquery': 'BigQuery',
                'snowflake': 'Snowflake'
            }

            # Shorter operator names for compact display
            operator_names_display = {
                'SEM_FILTER': 'Filter',
                'SEM_JOIN': 'Join',
                'SEM_MAP': 'Map',
                'SEM_SCORE': 'Score',
                'SEM_CLASSIFY': 'Classify'
            }

            # Calculate column specification: 3 columns per system (Quality, Latency, Cost)
            num_systems = len(available_systems)
            col_spec = "l " + " c c c " * num_systems

            # Start table
            tex_file.write("  \\begin{tabular*}{\\textwidth}{@{\\extracolsep{\\fill}} " + col_spec + "}\n")
            tex_file.write("    \\toprule\n")

            # Header with system names (spanning 3 columns each)
            header_systems = []
            for system in available_systems:
                display_name = system_names_display.get(system, system.capitalize())
                header_systems.append(f"\\multicolumn{{3}}{{c}}{{\\textbf{{{display_name}}}}}")

            tex_file.write(f"      & {' & '.join(header_systems)} \\\\\n")

            # Cmidrule for each system (3 columns each)
            cmidrules = []
            for i in range(num_systems):
                start = 2 + i * 3
                end = start + 2
                cmidrules.append(f"\\cmidrule(lr){{{start}-{end}}}")
            tex_file.write(f"      {' '.join(cmidrules)}\n")

            # Sub-header with metric names
            subheader = []
            for _ in available_systems:
                subheader.extend(["\\textbf{Quality}", "\\textbf{Latency}", "\\textbf{Cost}"])
            tex_file.write(f"      & {' & '.join(subheader)} \\\\\n")
            tex_file.write("    \\midrule\n")
            tex_file.write("    \\addlinespace[0.3ex]\n")

            # Generate rows for each operator
            for operator_type in operator_order:
                if operator_type not in efficiency_metrics:
                    continue

                # Collect all metric values for this row (operator)
                row_quality_values = []
                row_latency_values = []
                row_cost_values = []

                for system in available_systems:
                    metrics = efficiency_metrics[operator_type][system]
                    quality = metrics['quality_avg']
                    latency = metrics['execution_time_avg']
                    cost = metrics['money_cost_avg']

                    if quality is not None:
                        row_quality_values.append((system, quality))
                    if latency is not None:
                        row_latency_values.append((system, latency))
                    if cost is not None:
                        row_cost_values.append((system, cost))

                # Sort and assign color ranks:
                # Quality: higher is better (descending sort)
                # Latency: lower is better (ascending sort)
                # Cost: lower is better (ascending sort)
                row_quality_values.sort(key=lambda x: x[1], reverse=True)  # higher is better
                row_latency_values.sort(key=lambda x: x[1], reverse=False)  # lower is better
                row_cost_values.sort(key=lambda x: x[1], reverse=False)  # lower is better

                # Create color mapping for this row based on ranking
                quality_color_map = {}
                latency_color_map = {}
                cost_color_map = {}

                # Assign colors based on thirds
                num_quality = len(row_quality_values)
                num_latency = len(row_latency_values)
                num_cost = len(row_cost_values)

                for i, (system, _) in enumerate(row_quality_values):
                    if i < num_quality / 3:
                        quality_color_map[system] = "fancycellGreen"
                    elif i < 2 * num_quality / 3:
                        quality_color_map[system] = "fancycellYellow"
                    else:
                        quality_color_map[system] = "fancycellGray"

                for i, (system, _) in enumerate(row_latency_values):
                    if i < num_latency / 3:
                        latency_color_map[system] = "fancycellGreen"
                    elif i < 2 * num_latency / 3:
                        latency_color_map[system] = "fancycellYellow"
                    else:
                        latency_color_map[system] = "fancycellGray"

                for i, (system, _) in enumerate(row_cost_values):
                    if i < num_cost / 3:
                        cost_color_map[system] = "fancycellGreen"
                    elif i < 2 * num_cost / 3:
                        cost_color_map[system] = "fancycellYellow"
                    else:
                        cost_color_map[system] = "fancycellGray"

                # Now generate the row cells with proper colors
                op_display_name = operator_names_display.get(operator_type, operator_type)
                row_cells = [f"\\textbf{{{op_display_name}}}"]

                for system in available_systems:
                    metrics = efficiency_metrics[operator_type][system]
                    quality = metrics['quality_avg']
                    latency = metrics['execution_time_avg']
                    cost = metrics['money_cost_avg']

                    # Format Quality (3 decimal places to show differences)
                    if quality is not None:
                        color_class_quality = quality_color_map[system]
                        quality_text = f"{quality:.3f}"
                        quality_cell = f"\\{color_class_quality}{{{quality_text}}}"
                    else:
                        quality_cell = "\\fancyCellRed{n/a}"

                    # Format Latency (1 decimal place, seconds)
                    if latency is not None:
                        color_class_latency = latency_color_map[system]
                        latency_text = f"{latency:.1f}s"
                        latency_cell = f"\\{color_class_latency}{{{latency_text}}}"
                    else:
                        latency_cell = "\\fancyCellRed{n/a}"

                    # Format Cost (2 decimal places, dollars)
                    if cost is not None:
                        color_class_cost = cost_color_map[system]
                        cost_text = f"\\${cost:.2f}"
                        cost_cell = f"\\{color_class_cost}{{{cost_text}}}"
                    else:
                        cost_cell = "\\fancyCellRed{n/a}"

                    row_cells.extend([quality_cell, latency_cell, cost_cell])

                tex_file.write(f"    {' & '.join(row_cells)} \\\\\n")

            tex_file.write("    \\addlinespace[0.3ex]\n")
            tex_file.write("    \\midrule\n")
            tex_file.write("    \\addlinespace[0.3ex]\n")

            # Add average row across ALL operators
            avg_all_row = ["\\textbf{Avg}"]

            for system in available_systems:
                quality_values = []
                latency_values = []
                cost_values = []

                for operator_type in operator_order:
                    if operator_type in efficiency_metrics:
                        metrics = efficiency_metrics[operator_type][system]
                        if metrics['quality_avg'] is not None:
                            quality_values.append(metrics['quality_avg'])
                        if metrics['execution_time_avg'] is not None:
                            latency_values.append(metrics['execution_time_avg'])
                        if metrics['money_cost_avg'] is not None:
                            cost_values.append(metrics['money_cost_avg'])

                # Calculate averages
                avg_quality = np.mean(quality_values) if quality_values else None
                avg_latency = np.mean(latency_values) if latency_values else None
                avg_cost = np.mean(cost_values) if cost_values else None

                # Format average values
                if avg_quality is not None:
                    quality_text = f"\\fancycellNormal{{{avg_quality:.3f}}}"
                else:
                    quality_text = "--"

                if avg_latency is not None:
                    latency_text = f"\\fancycellNormal{{{avg_latency:.1f}s}}"
                else:
                    latency_text = "--"

                if avg_cost is not None:
                    cost_text = f"\\fancycellNormal{{\\${avg_cost:.2f}}}"
                else:
                    cost_text = "--"

                avg_all_row.extend([quality_text, latency_text, cost_text])

            tex_file.write(f"    {' & '.join(avg_all_row)} \\\\\n")

            # Add average row across COMMON operators (supported by all systems) if applicable
            if common_operators and len(common_operators) < len([op for op in operator_order if op in efficiency_metrics]):
                avg_common_row = ["\\textit{Avg*}"]

                for system in available_systems:
                    quality_values = []
                    latency_values = []
                    cost_values = []

                    for operator_type in common_operators:
                        if operator_type in efficiency_metrics:
                            metrics = efficiency_metrics[operator_type][system]
                            if metrics['quality_avg'] is not None:
                                quality_values.append(metrics['quality_avg'])
                            if metrics['execution_time_avg'] is not None:
                                latency_values.append(metrics['execution_time_avg'])
                            if metrics['money_cost_avg'] is not None:
                                cost_values.append(metrics['money_cost_avg'])

                    # Calculate averages
                    avg_quality = np.mean(quality_values) if quality_values else None
                    avg_latency = np.mean(latency_values) if latency_values else None
                    avg_cost = np.mean(cost_values) if cost_values else None

                    # Format average values
                    if avg_quality is not None:
                        quality_text = f"\\fancycellNormal{{{avg_quality:.3f}}}"
                    else:
                        quality_text = "--"

                    if avg_latency is not None:
                        latency_text = f"\\fancycellNormal{{{avg_latency:.1f}s}}"
                    else:
                        latency_text = "--"

                    if avg_cost is not None:
                        cost_text = f"\\fancycellNormal{{\\${avg_cost:.2f}}}"
                    else:
                        cost_text = "--"

                    avg_common_row.extend([quality_text, latency_text, cost_text])

                tex_file.write(f"    {' & '.join(avg_common_row)} \\\\\n")

            tex_file.write("    \\bottomrule\n")
            tex_file.write("  \\end{tabular*}\n")
            tex_file.write("  \\endgroup\n")
            tex_file.write("  \\end{threeparttable}\n")
            tex_file.write("\\end{table*}\n")

        print(f"✅ Saved aggregate operator table to {output_path}")

    def print_summary(self, model_tag="2.5flash"):
        """Print summary statistics to console"""
        # Scan and load data
        self.scan_available_data(model_tag)
        self.load_data(model_tag)

        # Define system display order
        selected_systems = ["lotus", "palimpzest", "thalamusdb", "bigquery"]
        available_systems = [s for s in selected_systems if s in self.systems]

        # Filter queries if needed
        filtered_queries = self.operator_queries
        if self.only_common_queries:
            filtered_queries = self.filter_queries_by_support(self.operator_queries, available_systems)

        # Calculate aggregates
        operator_stats = self.calculate_operator_aggregates(filtered_queries)
        efficiency_metrics = self.calculate_efficiency_metrics(operator_stats)

        # Count queries per operator and system
        query_counts = self.count_operator_queries(filtered_queries, available_systems)

        print("\n" + "=" * 90)
        print("AGGREGATE OPERATOR ANALYSIS")
        print("=" * 90)

        operator_order = ['SEM_FILTER', 'SEM_JOIN', 'SEM_MAP', 'SEM_SCORE', 'SEM_CLASSIFY']

        for operator_type in operator_order:
            if operator_type not in efficiency_metrics:
                continue

            op_counts = query_counts.get(operator_type, {'total': 0, 'by_system': {}})
            total_queries = op_counts['total']

            print(f"\n{operator_type} (Total queries: {total_queries}):")
            print("-" * 90)
            print(f"{'System':<15} {'Queries':<10} {'Quality':<10} {'Latency(s)':<12} {'Cost($)':<12}")
            print("-" * 90)

            for system in available_systems:
                metrics = efficiency_metrics[operator_type][system]
                quality = metrics.get('quality_avg')
                latency = metrics.get('execution_time_avg')
                cost = metrics.get('money_cost_avg')
                supported = op_counts['by_system'].get(system, 0)

                # Print if all three metrics are valid (quality can be 0)
                if quality is not None and latency is not None and cost is not None:
                    print(f"{system:<15} {supported}/{total_queries:<7} {quality:>8.3f}   {latency:>10.1f}     ${cost:>8.4f}")

        print("\n" + "=" * 90 + "\n")


def main(only_common_queries=True, use_repeat_folders=True):
    """Main function to generate aggregate operator table

    Args:
        only_common_queries: If True, only include queries supported by all systems (default: True)
        use_repeat_folders: If True, use across_system_{tag}_{sf}_repeat{i} folders (default: True)
    """
    print("Starting aggregate operator table generation...")
    if only_common_queries:
        print("Mode: Only queries supported by all systems")
    else:
        print("Mode: All queries")
    if use_repeat_folders:
        print("Mode: Using repeat folders (sf-based)")
    else:
        print("Mode: Using original folders")

    generator = AggregateTableGenerator(only_common_queries=only_common_queries, use_repeat_folders=use_repeat_folders)

    # Generate table
    model_tag = "2.5flash"
    output_filename = "aggregate_operator_table_common.tex" if only_common_queries else "aggregate_operator_table.tex"
    generator.generate_latex_table(model_tag=model_tag, output_filename=output_filename)

    # Print summary to console
    generator.print_summary(model_tag=model_tag)

    print("\nGeneration complete!")


if __name__ == "__main__":
    main()
