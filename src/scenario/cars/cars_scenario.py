import os
from typing import List

from scenario.cars.preparation.generate_data import prepare_data
import glob


CARS_FILES_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "files", "cars"
    )
)


class CarsScenario:
    """
    Medical scenario handler.

    This class:
     * downloads and prepares data
     * retrievs queries
    """

    def __init__(self, scale_factor: int = 157376):
        self.data_dir = CARS_FILES_DIR
        self.scale_factor = scale_factor

    def setup_scenario(self, systems: List[str]) -> None:
        # Download and prepare data if not already done
        prepare_data(scaling_factor=self.scale_factor)

        # Load data into the specified systems
        for system in systems:
            if system == "bigquery":
                from scenario.cars.setup.bigquery import BigQueryCarsSetup

                setup = BigQueryCarsSetup()
                setup.setup_data(data_dir=os.path.join(self.data_dir, "data"), scale_factor=self.scale_factor)

            elif system == "lotus":
                pass  # Nothing to do. LOTUS works on raw files.

            elif system == "palimpzest":
                pass  # Nothing to do. Palimpzest works on raw files.
            
            elif system == "thalamusdb":
                pass

            else:
                raise ValueError(f"Unsupported system: {system}")

    def get_query_text(self, query_id: int, system_name: str) -> str:
        """
        Get the SQL query text for a given query ID and system name.

        Args:
            query_id: ID of the query
            system_name: Name of the system
        Returns:
            SQL query text as a string
        """
        system_query_dir = os.path.abspath(
            os.path.join(CARS_FILES_DIR, "query", system_name)
        )
        matching_files = glob.glob(
            os.path.join(system_query_dir, f"Q{query_id}.*")
        )

        if not matching_files:
            print(os.path.join(system_query_dir, f"Q{query_id}.*"))
            raise FileNotFoundError(
                f"No query implementation found for query {query_id} and system '{system_name}'"
            )
        if len(matching_files) > 1:
            raise ValueError(
                f"Multiple query files found for query {query_id} and system '{system_name}': {matching_files}"
            )

        with open(matching_files[0], "r") as f:
            return f.read()

    def get_data_dir(self) -> str:
        return self.data_dir
