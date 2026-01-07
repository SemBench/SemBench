import pandas as pd
from google.cloud import storage, bigquery
from google.api_core.exceptions import NotFound
import os
import uuid
import concurrent.futures
import hashlib


PROJECT_ID = "bq-mm-benchmark"
BQ_DATASET_ID = "cars_dataset"
BQ_TABLE_LOCATION = "US"

class BigQueryCarsSetup:
    def __init__(self):
        """
        Initializes the BigQuery client.
        Assumes GOOGLE_APPLICATION_CREDENTIALS is set in the environment.
        """
        self.gcs_client = storage.Client(project=PROJECT_ID)
        self.bq_client = bigquery.Client(project=PROJECT_ID)
        self.gcs_bucket_name = f"{self.bq_client.project}-cars_dataset"

    def upload_file_to_gcs(self, bucket_name, local_file_path, gcs_destination_blob_name, add_cols):
        try:
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(gcs_destination_blob_name)

            blob.upload_from_filename(local_file_path)

            gcs_uri = f"gs://{bucket_name}/{gcs_destination_blob_name}"

            return [gcs_uri] + add_cols
        except Exception as e:
            print(f"  Error uploading '{local_file_path}': {e}")
            return None 

    def create_bq_dataset_and_table(self, dataset_id, table_id, location, schema):
        """Creates the BigQuery dataset and table if they don't exist."""
        dataset_ref = self.bq_client.dataset(dataset_id)
        table_ref = dataset_ref.table(table_id)

        try:
            self.bq_client.get_dataset(dataset_ref)
            print(f"BigQuery Dataset '{dataset_id}' already exists.")
        except NotFound:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = location
            self.bq_client.create_dataset(dataset, timeout=30)
            print(f"BigQuery Dataset '{dataset_id}' created in {dataset.location}.")

        try:
            self.bq_client.get_table(table_ref)
            print(f"BigQuery Table '{table_id}' already exists.")
        except NotFound:
            table = bigquery.Table(table_ref, schema=schema)
            self.bq_client.create_table(table)
            print(f"BigQuery Table '{table_id}' created.")
        return table_ref


    def upload_df_to_bigquery(self, dataframe, table_ref, schema):
        """Uploads a pandas DataFrame to the specified BigQuery table."""
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        job = self.bq_client.load_table_from_dataframe(
            dataframe, table_ref, job_config=job_config
        )
        job.result()


    def upload_images(self, local_path: str, gcs_folder: str, path_col: str, table_id: str):
        if not os.path.exists(local_path):
            print(f"No files found in '{local_path}'. Skipping.")
            return

        full_df = pd.read_csv(local_path)
        all_files_to_upload = []
        for _, row in full_df.iterrows():
            local_file_path = row[path_col]
            if not os.path.exists(local_file_path):
                print(f"Warning: File {local_file_path} does not exist. Skipping.")
                continue
            blob_file_name = os.path.join(gcs_folder, local_file_path.split("/")[-1])
            all_files_to_upload.append((row[full_df.columns[full_df.columns != path_col].tolist()].to_list(), local_file_path, blob_file_name))

        # Create a bucket if it doesn't exist
        bucket = self.gcs_client.lookup_bucket(self.gcs_bucket_name)
        if bucket is None:
            print(f"Bucket {self.gcs_bucket_name} not found. Creating it...")
            bucket = self.gcs_client.create_bucket(self.gcs_bucket_name)

        # Clean up old files in the GCS folder to ensure fresh upload
        print(f"Cleaning up old files in gs://{self.gcs_bucket_name}/{gcs_folder}/...")
        blobs_to_delete = list(bucket.list_blobs(prefix=f"{gcs_folder}/"))
        if blobs_to_delete:
            print(f"  Deleting {len(blobs_to_delete)} old files in parallel...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as delete_executor:
                delete_futures = [delete_executor.submit(blob.delete) for blob in blobs_to_delete]
                concurrent.futures.wait(delete_futures)
            print(f"  Cleanup completed!")
        else:
            print(f"  No old files to delete.")

        # Write images to GCS
        records = []
        total_files = len(all_files_to_upload)
        print(f"Uploading {total_files} files to GCS with 20 concurrent workers...")
        completed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_file = {
                executor.submit(self.upload_file_to_gcs, self.gcs_bucket_name, local_path, gcs_blob_name, add_cols):
                local_path for add_cols, local_path, gcs_blob_name in all_files_to_upload
            }
            for future in concurrent.futures.as_completed(future_to_file):
                local_path = future_to_file[future]
                try:
                    res = future.result()
                    if res:
                        record_dict = {col_name: val for col_name, val in zip(full_df.columns[full_df.columns != path_col], res[1:])}
                        record_dict[path_col] = res[0]
                        records.append(record_dict)
                    completed += 1
                    if completed % 10 == 0 or completed == total_files:
                        print(f"  Progress: {completed}/{total_files} files uploaded ({100*completed//total_files}%)")
                except Exception as exc:
                    print(f"'{local_path}' generated an exception: {exc}")
                    completed += 1

        if not records:
            print("No images were uploaded to GCS. Skipping BigQuery upload.")
            return

        df_image_data = pd.DataFrame(records)

        if "audio" not in table_id:
            bq_schema = [
                bigquery.SchemaField("car_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("image_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("image_path", "STRING", mode="REQUIRED"),
            ]
        else:
            bq_schema = [
                bigquery.SchemaField("car_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("audio_path", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("audio_id", "INTEGER", mode="REQUIRED"),
            ]

        bq_table_ref = self.create_bq_dataset_and_table(BQ_DATASET_ID, table_id, BQ_TABLE_LOCATION, bq_schema)

        try:
            self.upload_df_to_bigquery(df_image_data, bq_table_ref, bq_schema)
            print(f"Files uploaded to GCS and metadata loaded into BigQuery table {table_id}!")
        except Exception as e:
            print(f"An error occurred during BigQuery upload: {e}")

    def upload_csv_to_bigquery(self, dataset_id: str, csv_file_path: str, table_name: str):
            print(f"Uploading data into table {table_name} from {csv_file_path}...")

            table_id = f"{dataset_id}.{table_name}"

            with open(csv_file_path, "rb") as source_file:
                load_job = self.bq_client.load_table_from_file(
                source_file,
                table_id,
                job_config=bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.CSV,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    skip_leading_rows=1,  # Skip header row
                    autodetect=True,  # Automatically detect schema
                )
                )
            load_job.result()

    def finalize_image_upload(self, table_name, table_name_multimodal, image_url_table, url_col, bucket="gs://bq-mm-benchmark-cars_dataset/car_images/*"):
        # Create an external images table
        query = f"""
                CREATE OR REPLACE EXTERNAL TABLE {BQ_DATASET_ID}.{table_name}
                WITH CONNECTION `us.connection`
                OPTIONS (
                object_metadata = 'SIMPLE',
                uris = ['{bucket}'],
                max_staleness = INTERVAL 30 MINUTE,
                metadata_cache_mode = AUTOMATIC);
                """
        self.bq_client.query_and_wait(query)

        # Join table to get images and tabular data in one table
        query = f"""
                CREATE OR REPLACE TABLE {BQ_DATASET_ID}.{table_name_multimodal}
                AS
                SELECT {image_url_table}.* EXCEPT ({url_col}), ot.ref AS image FROM cars_dataset.{image_url_table}
                INNER JOIN {BQ_DATASET_ID}.{table_name} ot
                ON ot.uri = {image_url_table}.{url_col}
                """
        self.bq_client.query_and_wait(query)

    def table_exists(self, table_id):
        table_full_id = f"{PROJECT_ID}.{BQ_DATASET_ID}.{table_id}"

        try:
            self.bq_client.get_table(table_full_id)
            return True
        except NotFound:
            return False
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    def get_table_row_count(self, table_id):
        """Get the number of rows in a BigQuery table."""
        table_full_id = f"{PROJECT_ID}.{BQ_DATASET_ID}.{table_id}"
        try:
            query = f"SELECT COUNT(*) as row_count FROM `{table_full_id}`"
            result = self.bq_client.query(query).result()
            return next(result).row_count
        except Exception as e:
            print(f"Error getting row count for {table_id}: {e}")
            return -1

    def get_local_csv_hash(self, file_path):
        """Get hash of local CSV file content."""
        if not os.path.exists(file_path):
            return None

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def is_data_synchronized(self, local_csv_path, table_id):
        """Check if local CSV data matches cloud table data."""
        if not os.path.exists(local_csv_path):
            print(f"Local file {local_csv_path} not found")
            return False

        if not self.table_exists(table_id):
            return False

        # Quick check: compare row counts
        local_df = pd.read_csv(local_csv_path)
        local_row_count = len(local_df)
        cloud_row_count = self.get_table_row_count(table_id)

        if local_row_count != cloud_row_count:
            print(f"Row count mismatch for {table_id}: local={local_row_count}, cloud={cloud_row_count}")
            return False

        # Additional check: file modification time vs last upload
        # Store hash for future comparison
        hash_file = f"{local_csv_path}.hash"
        current_hash = self.get_local_csv_hash(local_csv_path)

        if os.path.exists(hash_file):
            with open(hash_file, 'r') as f:
                stored_hash = f.read().strip()
            if current_hash != stored_hash:
                print(f"Local file {local_csv_path} has changed since last upload")
                return False
        else:
            # First time, assume sync needed
            return False

        return True

    def mark_data_synchronized(self, local_csv_path):
        """Mark local data as synchronized by storing its hash."""
        current_hash = self.get_local_csv_hash(local_csv_path)
        if current_hash:
            hash_file = f"{local_csv_path}.hash"
            with open(hash_file, 'w') as f:
                f.write(current_hash)

    def setup_data(self, scale_factor: int = 157376, data_dir: str = "files/cars/data/"):
        """Setup BigQuery tables for cars scenario.

        Args:
            scale_factor: The scale factor used to generate the data (determines subfolder)
            data_dir: Base data directory (will look in data_dir/sf_{scale_factor}/)
        """
        # Use scale-factor-specific subdirectory
        actual_data_dir = os.path.join(data_dir, f"sf_{scale_factor}")

        dataset_id = f"{self.bq_client.project}.{BQ_DATASET_ID}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        self.bq_client.create_dataset(dataset, exists_ok=True)

        # Upload car images
        image_csv_path = os.path.join(actual_data_dir, f"image_car_data_{scale_factor}.csv")
        needs_upload = not self.is_data_synchronized(image_csv_path, "car_images")

        if needs_upload:
            print(f"Uploading/updating car images to BigQuery (SF={scale_factor})...")
            self.upload_images(
                local_path=image_csv_path,
                gcs_folder="car_images",
                path_col="image_path",
                table_id="car_images"
            )
            self.finalize_image_upload(
                table_name="cars_images",
                table_name_multimodal="car_mm",
                image_url_table="car_images",
                url_col="image_path",
                bucket="gs://bq-mm-benchmark-cars_dataset/car_images/*"
            )
            self.mark_data_synchronized(image_csv_path)
        else:
            print(f"Car images tables exist and are synchronized (SF={scale_factor}), skipping upload.")

        # Upload car audio
        audio_csv_path = os.path.join(actual_data_dir, f"audio_car_data_{scale_factor}.csv")
        needs_upload = not self.is_data_synchronized(audio_csv_path, "car_audio")

        if needs_upload:
            print(f"Uploading/updating car audio to BigQuery (SF={scale_factor})...")
            self.upload_images(
                local_path=audio_csv_path,
                gcs_folder="car_audios",
                path_col="audio_path",
                table_id="car_audio"
            )
            self.finalize_image_upload(
                table_name="cars_audios",
                table_name_multimodal="audio_mm",
                image_url_table="car_audio",
                url_col="audio_path",
                bucket="gs://bq-mm-benchmark-cars_dataset/car_audios/*"
            )
            self.mark_data_synchronized(audio_csv_path)
        else:
            print(f"Car audio tables exist and are synchronized (SF={scale_factor}), skipping upload.")

        # Upload car metadata (cars table)
        cars_csv_path = os.path.join(actual_data_dir, f"car_data_{scale_factor}.csv")
        if not os.path.exists(cars_csv_path):
            print(f"Warning: {cars_csv_path} not found, skipping cars table upload")
        else:
            needs_upload = not self.is_data_synchronized(cars_csv_path, "cars")
            if needs_upload or not self.table_exists("cars"):
                print(f"Uploading/updating cars data to BigQuery (SF={scale_factor})...")
                self.upload_csv_to_bigquery(BQ_DATASET_ID, csv_file_path=cars_csv_path, table_name='cars')
                self.mark_data_synchronized(cars_csv_path)
            else:
                print(f"Cars table exists and is synchronized (SF={scale_factor}), skipping upload.")

        # Upload complaints
        complaints_csv_path = os.path.join(actual_data_dir, f"text_complaints_data_{scale_factor}.csv")
        if not os.path.exists(complaints_csv_path):
            print(f"Warning: {complaints_csv_path} not found, skipping complaints table upload")
        else:
            needs_upload = not self.is_data_synchronized(complaints_csv_path, "complaints")
            if needs_upload or not self.table_exists("complaints"):
                print(f"Uploading/updating complaints data to BigQuery (SF={scale_factor})...")
                self.upload_csv_to_bigquery(BQ_DATASET_ID, csv_file_path=complaints_csv_path, table_name='complaints')
                self.mark_data_synchronized(complaints_csv_path)
            else:
                print(f"Complaints table exists and is synchronized (SF={scale_factor}), skipping upload.")

        print("Data setup completed successfully!")
