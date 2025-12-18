"""
Created on May 28, 2025

@author: Jiale Lao

Generic runner base class for all data system runners, you should implement
execute_query(query_id: int) -> GenericQueryMetric in your system
implementations
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class GenericQueryMetric:
    """Base class for query metrics with results."""

    query_id: int
    status: str  # 'success' or 'failed'
    execution_time: float = None
    results: pd.DataFrame = field(default_factory=pd.DataFrame)
    token_usage: int = None
    money_cost: float = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metric to dictionary (excluding DataFrame; instead includes
        row_count).
        """
        data = {
            k: v
            for k, v in asdict(self).items()
            if v is not None and k != "results"
        }
        data["row_count"] = len(self.results) if self.results is not None else 0
        return data


class GenericRunner(ABC):
    """Base class for all system runners."""

    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str,
        concurrent_llm_worker: int,
        skip_setup: bool = False,
    ):
        """
        Initialize the runner.

        Args:
            use_case: The use case to run (e.g., 'movie')
        """
        self.use_case = use_case
        self.system_name = self.get_system_name()

        # Set up paths
        self.base_path = Path(__file__).resolve().parents[2]
        self.files_path = self.base_path / "files" / use_case
        self.data_path = self.files_path / "data" / f"sf_{scale_factor}"
        self.query_path = self.files_path / "query"
        self.results_path = self.files_path / "raw_results" / self.system_name
        self.metrics_path = self.files_path / "metrics"

        # Create directories if they don't exist
        self.results_path.mkdir(parents=True, exist_ok=True)
        self.metrics_path.mkdir(parents=True, exist_ok=True)

        # Initialize metrics storage
        self.metrics: Dict[int, GenericQueryMetric] = {}
        self.model_name = model_name
        self.scale_factor = scale_factor
        self.concurrent_llm_worker = concurrent_llm_worker

        # Manage scenario-specific data
        self.scenario_handler = GenericRunner.get_scenario_handler(
            self.use_case, self.scale_factor
        )
        if not skip_setup and self.scenario_handler is not None:
            self.scenario_handler.setup_scenario([self.get_system_name()])

    @abstractmethod
    def get_system_name(self) -> str:
        """Return the name of the system (e.g., 'lotus', 'bigquery')."""
        raise NotImplementedError("Subclasses must implement get_system_name()")

    def execute_query(self, query_id: int) -> GenericQueryMetric:
        """
        Execute a specific query and return metric object with results.

        Args:
            query_id: ID of the query (e.g., 1 for Q1, 5 for Q5)

        Returns:
            QueryMetric object containing results DataFrame and metrics
        """
        raise NotImplementedError(
            "Subclasses must either implement execute_query() or override execute_queries()"  # noqa: E501
        )

    def execute_queries(
        self, query_ids: List[int]
    ) -> Dict[int, GenericQueryMetric]:
        """
        Execute multiple queries and return metrics.
        Systems can choose to either override this method if it makes more
        sense to do batch execution, or use the default implementation and
        instead override execute_query(query_id: int).

        Args:
            query_ids: List of query IDs to execute

        Returns:
            Dictionary mapping query IDs to GenericQueryMetric objects
        """
        results = {}
        for query_id in query_ids:
            try:
                results[query_id] = self.execute_query(query_id)
            except Exception as e:
                print(f"Error executing query {query_id}: {e}")
                results[query_id] = GenericQueryMetric(
                    query_id=query_id,
                    execution_time=0.0,
                    status="failed",
                    error=str(e),
                )
        return results

    def run_all_queries(
        self, queries: Optional[List[int]] = None
    ) -> Dict[int, GenericQueryMetric]:
        """
        Run all queries for this system.

        Args:
            queries: Optional list of specific query IDs to run

        Returns:
            Dictionary mapping query IDs to metrics
        """
        # If no specific queries provided, discover all available queries
        if queries is None:
            queries = self._discover_queries()

        print(f"\nRunning {len(queries)} queries for {self.system_name}")
        self.metrics = self.execute_queries(queries)
        self.save_metrics()

        return self.metrics

    def get_query_text(
        self, query_id: int, query_type: str = "natural_language"
    ) -> str:
        """
        Read query text from file.

        Args:
            query_id: ID of the query (e.g., 1 for Q1, 5 for Q5)
            query_type: Type of query ('mm_sql', 'natural_language', etc.)

        Returns:
            Query text as string
        """
        query_name = f"Q{query_id}"
        query_file = self.query_path / query_type / f"{query_name}.txt"
        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")

        with open(query_file, "r") as f:
            return f.read().strip()

    def save_results(self, query_id: int, results: pd.DataFrame):
        """
        Save query results to CSV file.

        Args:
            query_id: ID of the query
            results: DataFrame containing results
        """
        query_name = f"Q{query_id}"
        output_file = self.results_path / f"{query_name}.csv"
        results.to_csv(output_file, index=False)
        print(f"Results saved to: {output_file}")

    def save_metrics(self):
        """Save metrics to JSON file."""
        metrics_file = self.metrics_path / f"{self.system_name}.json"

        # Convert metrics to dict format
        metrics_dict = {}
        for query_id, metric in self.metrics.items():
            query_name = f"Q{query_id}"
            metrics_dict[query_name] = metric.to_dict()
            metrics_dict[query_name]["model_name"] = self.model_name
            metrics_dict[query_name][
                "concurrent_llm_worker"
            ] = self.concurrent_llm_worker
            self.save_results(query_id, metric.results)

        # # write query results to csv files
        # for query_id, metric in self.metrics.items():
        #     self.save_results(query_id, metric.results)

        with open(metrics_file, "w") as f:
            json.dump(metrics_dict, f, indent=2)
        print(f"Metrics saved to: {metrics_file}")

    def _get_empty_results_dataframe(self, query_id: int) -> pd.DataFrame:
        """
        Get empty DataFrame with correct columns for a query.
        Override in subclasses for query-specific schemas.

        Args:
            query_id: ID of the query

        Returns:
            Empty DataFrame with correct columns
        """
        return pd.DataFrame()

    def _discover_queries(self) -> List[int]:
        """
        Discover available queries for this system.
        Default implementation looks for query files.

        Returns:
            List of query IDs
        """
        # If we can, go via the scenario handler because it knowns best how
        # queries are structured for the scenario
        scenario_handler = GenericRunner.get_scenario_handler(
            self.use_case, self.scale_factor
        )
        if scenario_handler is not None:
            return scenario_handler.discover_available_queries(
                system_name=self.get_system_name()
            )

        # Look in mm_sql directory by default
        mm_sql_path = self.query_path / "mm_sql"
        if mm_sql_path.exists():
            query_files = list(mm_sql_path.glob("Q*.txt"))
            query_ids = []
            for f in query_files:
                try:
                    # Extract number from filename like Q1.txt
                    query_id = int(f.stem[1:])
                    query_ids.append(query_id)
                except ValueError:
                    continue
            return sorted(query_ids)

        return []

    def _discover_query_text(self, query_id: int) -> str:
        expected_path = os.path.join(
            self.query_path, self.system_name, f"Q{query_id}.sql"
        )
        if not os.path.exists(expected_path):
            expected_path = os.path.join(
                self.query_path, self.system_name, f"q{query_id}.sql"
            )
            if not os.path.exists(expected_path):
                raise FileNotFoundError(
                    f"Query file not found for {self.system_name} q{query_id}"
                )

        with open(expected_path, "r") as f:
            return f.read().strip()

    def _discover_query_impl(self, query_id) -> callable:
        method_name = f"_execute_q{query_id}"
        try:
            query_fn = getattr(self, method_name)
            if not callable(query_fn):
                raise TypeError(f"{method_name} exists but is not callable")
            return query_fn
        except AttributeError:
            raise NotImplementedError(
                f"Query {query_id} not implemented for {self.system_name}."
            )

    def load_data(self, filename: str, **kwargs) -> pd.DataFrame:
        """
        Load data file from the data directory.

        Args:
            filename: Name of the data file

        Returns:
            DataFrame containing the data
        """
        data_file = self.data_path / filename
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {data_file}")

        return pd.read_csv(data_file, **kwargs)

    def get_scenario_handler(use_case: str, scale_factor: int = None):
        """
        Get the scenario handler for a specific use case.
        Dynamically imports the scenario handler based on the use case.
        """
        if use_case == "ecomm":
            from scenario.ecomm.ecomm_scenario import EcommScenario

            return EcommScenario(scale_factor=scale_factor)
        elif use_case == "medical":
            from scenario.medical.medical_scenario import MedicalScenario

            return MedicalScenario(scale_factor=scale_factor)
        elif use_case == "animals":
            from scenario.animals.animals_scenario import AnimalsScenario

            return AnimalsScenario(scale_factor=scale_factor)
        elif use_case == "mmqa":
            from scenario.mmqa.mmqa_scenario import MMQAScenario

            return MMQAScenario(scale_factor=scale_factor)
        elif use_case == "movie":
            from scenario.movie.movie_scenario import MovieScenario

            return MovieScenario(scale_factor=scale_factor)
        elif use_case == "detective":
            return None  # Scenario does not have a specific handler
        elif use_case == "cars":
            from scenario.cars.cars_scenario import CarsScenario

            return CarsScenario(scale_factor=scale_factor)
        else:
            raise ValueError(f"Unknown use case: {use_case}.")
