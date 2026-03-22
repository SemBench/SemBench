import os
from typing import Any, Dict, List
import pandas as pd
from .preparation.generate_data import prepare_data
import glob
import tomli
import duckdb


ECOMM_FILES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "files", "ecomm")
)


class EcommScenario:
    """
    E-commerce scenario for benchmarking SQL query performance.

    This class handles scenario-specficic things like:
     * downloading and setting up the dataset
     * discovering available queries
     * retrieving query text for specific systems
     * retrieving ground truth results for queries
    """

    def __init__(self, scale_factor: int = None):
        # Path to the directory where the dataset is stored. This depends on various factors like the scale factor.
        self.data_dir = None
        self.queries = self._load_queries()
        self.scale_factor = scale_factor

    def _load_queries(self) -> Dict[int, Any]:
        """
        Load queries from the e-commerce scenario directory.

        Returns:
            List of query definitions.
        """
        query_files = glob.glob(
            os.path.join(ECOMM_FILES_DIR, "queries", "*.toml")
        )
        queries = {}
        for file in query_files:
            with open(file, "rb") as f:
                try:
                    query_data = tomli.load(f)
                except tomli.TOMLDecodeError as e:
                    raise ValueError(f"Error decoding TOML file {file}: {e}")

                if "query_id" in query_data["metadata"]:
                    queries[query_data["metadata"]["query_id"]] = query_data

                    # The file name should be of the format q1.toml, q2.toml, etc.
                    # Double-check the file name here and print a warning if it doesn't match (no need to enforce strict naming).
                    # This constraint can be relaxed if needed.
                    expected_file_name = (
                        f"q{query_data['metadata']['query_id']}.toml"
                    )
                    if os.path.basename(file) != expected_file_name:
                        print(
                            f"Warning: File {file} does not match expected naming convention {expected_file_name}."
                        )
                else:
                    print(
                        f"Warning: 'metadata.query_id' key not found in {file}. Skipping this query."
                    )
        return queries

    def get_data_dir(self) -> str:
        if self.data_dir:
            return self.data_dir
        else:
            return os.path.abspath(
                os.path.join(
                    ECOMM_FILES_DIR,
                    "data",
                    f"sf_{str(self.scale_factor)}",
                )
            )

    def setup_scenario(self, systems: List[str]) -> None:
        # Download and prepare data
        self.data_dir = prepare_data(scale_factor=self.scale_factor)

        # Load data into the specified systems
        for system in systems:
            if system == "bigquery":
                from .setup.bigquery import BigQueryEcommSetup

                setup = BigQueryEcommSetup()
                setup.setup_data(self.data_dir)
            elif system == "snowflake":
                from .setup.snowflake import SnowflakeEcommSetup

                setup = SnowflakeEcommSetup()
                setup.setup_data(self.data_dir)
            elif system == "thalamusdb":
                from .setup.thalamusdb import ThalamusDBEcommSetup

                setup = ThalamusDBEcommSetup()
                setup.setup_data(self.data_dir)
            elif system == "lotus":
                pass  # Nothing to do. LOTUS works on raw files.
            elif system == "palimpzest":
                pass  # Nothing to do. Palimpzest works on raw files.
            else:
                raise ValueError(f"Unsupported system: {system}")

    def discover_available_queries(self, system_name: str = None) -> List[int]:
        """
        Discover available queries for the e-commerce scenario.

        Returns:
            List of query IDs.
        """
        all_queries = self.queries.keys()
        if system_name is None:
            return all_queries

        system_query_dir = os.path.abspath(
            os.path.join(ECOMM_FILES_DIR, "queries", "dialects", system_name)
        )
        system_queries = []
        for query_id in all_queries:
            matching_files = glob.glob(
                os.path.join(system_query_dir, f"q{query_id}.*")
            )
            if matching_files:
                system_queries.append(query_id)
        return system_queries

    def get_query_text(self, query_id: int, system_name: str) -> str:
        """
        Get the SQL query text for a given query ID and system name.

        Args:
            query_id: ID of the query
            system_name: Name of the system (e.g., "bigquery", "snowflake")
        Returns:
            SQL query text as a string
        """
        system_query_dir = os.path.abspath(
            os.path.join(ECOMM_FILES_DIR, "queries", "dialects", system_name)
        )
        matching_files = glob.glob(
            os.path.join(system_query_dir, f"q{query_id}.*")
        )
        if not matching_files:
            raise FileNotFoundError(
                f"No query implementation found for query {query_id} and system '{system_name}'"
            )
        if len(matching_files) > 1:
            raise ValueError(
                f"Multiple query files found for query {query_id} and system '{system_name}': {matching_files}"
            )

        with open(matching_files[0], "r") as f:
            return f.read()

    def get_ground_truth(self, query_id: int) -> pd.DataFrame:
        """
        Get the ground truth result for a given query ID.

        Args:
            query_id: ID of the query
        Returns:
            DataFrame containing the ground truth result
        """
        ground_truth_sql = self.queries[int(query_id)]["definition"][
            "ground_truth"
        ]

        con = duckdb.connect()
        con.execute(f"set file_search_path = '{self.get_data_dir()}'")
        result_df = con.execute(ground_truth_sql).df()
        con.close()

        # Save ground truth CSV
        gt_path = os.path.join(
            ECOMM_FILES_DIR, "raw_results", "ground_truth", f"Q{query_id}.csv"
        )
        os.makedirs(os.path.dirname(gt_path), exist_ok=True)
        result_df.to_csv(gt_path, index=False)

        return result_df

    def get_accuracy_measure_for_query(self, query_id: int) -> str:
        """
        Get the accuracy measure for a given query ID.

        Args:
            query_id: ID of the query

        Returns:
            String representing the accuracy measure (e.g., "precision", "f1-score", etc.)
        """
        try:
            return self.queries[int(query_id)]["definition"]["accuracy_metric"]
        except KeyError as e:
            raise KeyError(f"Missing key {e} for query ID {query_id}.")
