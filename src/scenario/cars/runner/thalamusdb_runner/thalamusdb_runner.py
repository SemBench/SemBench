"""
ThalamusDB system runner implementation for Cars scenario.
"""

from pathlib import Path
import sys
import duckdb
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from runner.generic_thalamusdb_runner.generic_thalamusdb_runner import GenericThalamusDBRunner


class ThalamusDBRunner(GenericThalamusDBRunner):
    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str = "gemini-2.5-flash",
        concurrent_llm_worker: int = 20,
        skip_setup: bool = False,
    ):
        # Set database path
        db_name = "cars_database.duckdb"
        db_folder = (
            Path(__file__).resolve().parents[5] / "files" / use_case / "data" / f"sf_{scale_factor}"
        )
        db_path = db_folder / db_name

        # Call parent init FIRST to trigger data generation
        super().__init__(
            use_case, scale_factor, model_name, concurrent_llm_worker, db_path,
            skip_setup=skip_setup
        )

        # Now create the tables if they don't exist
        conn = duckdb.connect(str(db_path))
        tables = conn.execute("SHOW TABLES").fetchall()

        if len(tables) == 0:
            # Read CSVs and create tables
            cars_df = pd.read_csv(f"{db_folder}/car_data_{scale_factor}.csv")
            audio_df = pd.read_csv(f"{db_folder}/audio_car_data_{scale_factor}.csv")
            complaints_df = pd.read_csv(f"{db_folder}/text_complaints_data_{scale_factor}.csv")
            images_df = pd.read_csv(f"{db_folder}/image_car_data_{scale_factor}.csv")

            # Convert relative paths to absolute paths
            # The paths in CSVs are relative to the repository root
            repo_root = Path(__file__).resolve().parents[5]

            if 'audio_path' in audio_df.columns:
                audio_df['audio_path'] = audio_df['audio_path'].apply(
                    lambda x: str(repo_root / x) if pd.notna(x) and not Path(x).is_absolute() else x
                )

            if 'image_path' in images_df.columns:
                images_df['image_path'] = images_df['image_path'].apply(
                    lambda x: str(repo_root / x) if pd.notna(x) and not Path(x).is_absolute() else x
                )

            # Create tables
            conn.execute("CREATE TABLE cars AS SELECT * FROM cars_df")
            conn.execute("CREATE TABLE car_audio AS SELECT * FROM audio_df")
            conn.execute("CREATE TABLE car_complaints AS SELECT * FROM complaints_df")
            conn.execute("CREATE TABLE car_images AS SELECT * FROM images_df")

            # Create intermediate table for Q6 (XOR logic query)
            # This table contains cars with at least 2 modalities
            create_two_more_modalities = """
            CREATE OR REPLACE TABLE two_more_modalities AS (
                SELECT
                    cars.car_id,
                    cars.year,
                    car_complaints.complaint_id,
                    car_complaints.summary,
                    car_images.image_id,
                    car_images.image_path,
                    car_audio.audio_id,
                    car_audio.audio_path
                FROM cars
                LEFT JOIN car_images ON cars.car_id = car_images.car_id
                LEFT JOIN car_audio ON cars.car_id = car_audio.car_id
                LEFT JOIN car_complaints ON cars.car_id = car_complaints.car_id
                WHERE (car_audio.audio_id IS NOT NULL AND car_complaints.complaint_id IS NOT NULL) OR
                      (car_images.image_id IS NOT NULL AND car_complaints.complaint_id IS NOT NULL) OR
                      (car_images.image_id IS NOT NULL AND car_audio.audio_id IS NOT NULL)
            )
            """
            conn.execute(create_two_more_modalities)

        conn.close()
