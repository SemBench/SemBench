

import os
from pathlib import Path

import pandas as pd
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

CARS_FILES_DIR = os.path.abspath(
    Path(__file__).resolve().parents[4] / "files" / "cars" / "data"
)


class ThalamusDBCarsSetup:
    def __init__(self, model_name: str = "gpt-4o-mini", db_name:str = 'cars_database', load_extensions: bool = True, db_folder: str = CARS_FILES_DIR):
        """
        Initializes the ThalamusDB connection using environment variables.
        """
        if os.environ.get('OPENAI_API_KEY') is None:
            raise ValueError("Environment variable OPENAI_API_KEY is not set.")

        self.thalamusdb_conn = duckdb.connect(os.path.join(db_folder, f"{db_name}.duckdb"))

        if load_extensions:
            self.thalamusdb_conn.install_extension("flockmtl", repository="community")
            self.thalamusdb_conn.load_extension("flockmtl")

            self.thalamusdb_conn.execute(
                f"""CREATE SECRET (TYPE OPENAI,API_KEY '{os.environ.get('OPENAI_API_KEY')}');"""
            )

            if not model_name in self.thalamusdb_conn.execute("GET MODELS;").fetchdf()["model"].tolist():
                self.thalamusdb_conn.execute("""
                    CREATE MODEL(
                    'model_name',
                    'model_name',
                    'openai',
                    {"tuple_format": "json", "batch_size": 32, "model_parameters": {"temperature": 0.7}}
                    );
                """.replace("model_name", model_name))


    def _upload_file_to_db(self, csv_path: str, table_name: str):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"File not found at path: {csv_path}. Please run the download script first.")

        self.thalamusdb_conn.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{csv_path}');
            """)


    def setup_data(self, data_dir: str, scale_factor: int = 157376):
        sf_dir = os.path.join(data_dir, "data", f"sf_{scale_factor}")

        self._upload_file_to_db(
            csv_path=os.path.join(sf_dir, f"car_data_{scale_factor}.csv"),
            table_name="cars"
        )

        self._upload_file_to_db(
            csv_path=os.path.join(sf_dir, f"audio_car_data_{scale_factor}.csv"),
            table_name="car_audio"
        )

        self._upload_file_to_db(
            csv_path=os.path.join(sf_dir, f"text_complaints_data_{scale_factor}.csv"),
            table_name="car_complaints"
        )

        self._upload_file_to_db(
            csv_path=os.path.join(sf_dir, f"image_car_data_{scale_factor}.csv"),
            table_name="car_images"
        )

    def get_connection(self):
        """
        Returns the ThalamusDB connection.
        """
        return self.thalamusdb_conn

    def run_query(self, query: str):
        self.thalamusdb_conn.execute(query)
