import pandas as pd
from google.cloud import storage, bigquery
from google.api_core.exceptions import NotFound
import os
import uuid
import concurrent.futures 


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

            # print(f"  Uploading '{local_file_path}' to 'gs://{bucket_name}/{gcs_destination_blob_name}'...")
            blob.upload_from_filename(local_file_path)

            gcs_uri = f"gs://{bucket_name}/{gcs_destination_blob_name}"
            # print(f"  Uploaded successfully: {gcs_uri}")

            return [gcs_uri] + add_cols
        except Exception as e:
            print(f"  Error uploading '{local_file_path}': {e}")
            return None, None, None 

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
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        # print(f"Uploading data to {PROJECT_ID}.{table_ref.dataset_id}.{table_ref.table_id}...")
        job = self.bq_client.load_table_from_dataframe(
            dataframe, table_ref, job_config=job_config
        )
        job.result() 

        # print(f"Loaded {job.output_rows} rows into {table_ref.table_id}.")


    def upload_images(self, local_path: str, gcs_folder: str, path_col: str, table_id: str):
        if not os.path.exists(local_path):
            print(f"No files found in '{local_path}'.")
            exit()

        full_df = pd.read_csv(local_path)
        all_files_to_upload = []
        for _, row in full_df.iterrows():
            local_file_path = row[path_col]
            blob_file_name = os.path.join(gcs_folder, local_file_path.split("/")[-1])
            all_files_to_upload.append((row[full_df.columns[full_df.columns != path_col].tolist()].to_list(), local_file_path, blob_file_name))

        # Create a bucket if it doesn't exist
        bucket = self.gcs_client.lookup_bucket(self.gcs_bucket_name)
        if bucket is None:
            print(f"Bucket {self.gcs_bucket_name} not found. Creating it...")
            bucket = self.gcs_client.create_bucket(self.gcs_bucket_name)

        # Write images to GCS
        records = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(self.upload_file_to_gcs, self.gcs_bucket_name, local_path, gcs_blob_name, add_cols):
                local_path for add_cols, local_path, gcs_blob_name in all_files_to_upload
            }
            for future in concurrent.futures.as_completed(future_to_file):
                local_path = future_to_file[future]
                try:
                    res = future.result()
                    record_dict = {col_name: val for col_name, val in zip(full_df.columns[full_df.columns != path_col], res[1:])}
                    record_dict[path_col] = res[0]
                    records.append(record_dict)
                except Exception as exc:
                    print(f"'{local_path}' generated an exception: {exc}")

        if not records:
            print("No images were uploaded to GCS. Exiting BigQuery upload.")
            exit()

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

        print(bq_schema)

        bq_table_ref = self.create_bq_dataset_and_table(BQ_DATASET_ID, table_id, BQ_TABLE_LOCATION, bq_schema)

        try:
            self.upload_df_to_bigquery(df_image_data, bq_table_ref, bq_schema)
            print("Script finished successfully: Images uploaded to GCS and metadata loaded into BigQuery!")
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

    def setup_data(self, scale_factor: int = 157376, data_dir: str = "files/cars/data/"):
        """Setup BigQuery tables for cars scenario.

        Args:
            scale_factor: The scale factor used to generate the data (determines subfolder)
            data_dir: Base data directory (will look in data_dir/sf_{scale_factor}/)
        """
        # Use scale-factor-specific subdirectory
        print(f"Setting up data for scale factor {scale_factor}")
        
        actual_data_dir = os.path.join(data_dir, f"sf_{scale_factor}")

        dataset_id = f"{self.bq_client.project}.cars_dataset"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        self.bq_client.create_dataset(dataset, exists_ok=True)

        if not self.table_exists("cars") or scale_factor != 157376: # FIXME potentially disable to work with sf
            print("Uploading cars data to BigQuery...")
            self.upload_csv_to_bigquery(BQ_DATASET_ID, csv_file_path=os.path.join(actual_data_dir, f"car_data_{scale_factor}.csv"),  table_name='cars')

        if not self.table_exists("complaints") or scale_factor != 157376:
            print("Uploading complaints data to BigQuery...")
            self.upload_csv_to_bigquery(BQ_DATASET_ID, csv_file_path=os.path.join(actual_data_dir, f"text_complaints_data_{scale_factor}.csv"),  table_name='complaints')

        if not self.table_exists("car_images") or not self.table_exists("car_mm"):
            print("Uploading car images to BigQuery...")
            self.upload_images(local_path=os.path.join(actual_data_dir, f"image_car_data_{scale_factor}.csv"), 
                            gcs_folder="car_images", 
                            path_col="image_path", 
                            table_id="car_images")
            self.finalize_image_upload(
                table_name="cars_images", 
                table_name_multimodal="car_mm", 
                image_url_table="car_images", 
                url_col="image_path", 
                bucket="gs://bq-mm-benchmark-cars_dataset/car_images/*")

        if not self.table_exists("car_audio") or not self.table_exists("audio_mm"):
            print("Uploading car audio data to BigQuery...")
            self.upload_images(local_path=os.path.join(actual_data_dir, f"audio_car_data_{scale_factor}.csv"), 
                            gcs_folder="car_audios", 
                            path_col="audio_path", 
                            table_id="car_audio")

            self.finalize_image_upload(
                table_name="cars_audios", 
                table_name_multimodal="audio_mm", 
                image_url_table="car_audio", 
                url_col="audio_path", 
                bucket="gs://bq-mm-benchmark-cars_dataset/car_audios/*")  
        
        print("Data setup completed successfully!")
