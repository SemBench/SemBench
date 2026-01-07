import os

from google.cloud import bigquery, storage
from google.cloud.storage import transfer_manager


class BigQueryMMQASetup:
    def __init__(self):
        """
        Initializes the BigQuery client.
        Assumes GOOGLE_APPLICATION_CREDENTIALS is set in the environment.
        """
        self.bq_client = bigquery.Client(project="bq-mm-benchmark")

    def _upload_csv_to_bigquery(
        self, dataset_id: str, csv_file_path: str, table_name: str
    ):
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
                ),
            )
        load_job.result()

    def _upload_images_to_gcs(
        self, dataset_id, table_name, bucket_name: str, images_dir: str
    ):
        print(
            f"Uploading images from {images_dir} to GCS bucket {bucket_name}..."
        )
        storage_client = storage.Client()
        bucket = storage_client.lookup_bucket(bucket_name)
        if bucket is None:
            print(f"Bucket {bucket_name} not found. Creating it...")
            bucket = storage_client.create_bucket(bucket_name)
        else:
            # Clear existing images in bucket to ensure clean state for new scale factor
            print(f"Clearing existing images from bucket {bucket_name}...")
            blobs = list(bucket.list_blobs())
            if blobs:
                bucket.delete_blobs(blobs)
                print(f"Deleted {len(blobs)} existing images from bucket.")

        string_paths = []
        for f in os.listdir(images_dir):
            if f.endswith(".jpg") or f.endswith(".png"):
                string_paths.append(f)

        results = transfer_manager.upload_many_from_filenames(
            bucket, string_paths, source_directory=images_dir, max_workers=16
        )

        for name, result in zip(string_paths, results):
            if isinstance(result, Exception):
                print(
                    "Failed to upload {} due to exception: {}".format(
                        name, result
                    )
                )

        # Create external table in BigQuery for images in GCS
        print(
            f"Creating external table {dataset_id}.{table_name} for images in GCS..."  # noqa: E501
        )
        query_job = self.bq_client.query(
            f"""
            CREATE OR REPLACE EXTERNAL TABLE {dataset_id}.{table_name}
            WITH CONNECTION `us.connection`
            OPTIONS(
                object_metadata = 'SIMPLE',
                uris = ['gs://{bucket_name}/*.jpg']
            );
        """
        )
        query_job.result()

    def setup_data(self, data_dir: str):
        dataset_id = f"{self.bq_client.project}.mmqa"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        self.bq_client.create_dataset(dataset, exists_ok=True)

        self._upload_csv_to_bigquery(
            dataset_id,
            csv_file_path=os.path.join(data_dir, "ap_warrior.csv"),
            table_name="ap_warrior",
        )
        self._upload_csv_to_bigquery(
            dataset_id,
            csv_file_path=os.path.join(data_dir, "ben_piazza.csv"),
            table_name="ben_piazza",
        )
        self._upload_csv_to_bigquery(
            dataset_id,
            csv_file_path=os.path.join(data_dir, "ben_piazza_text_data.csv"),
            table_name="ben_piazza_text_data",
        )
        self._upload_csv_to_bigquery(
            dataset_id,
            csv_file_path=os.path.join(data_dir, "lizzy_caplan_text_data.csv"),
            table_name="lizzy_caplan_text_data",
        )
        self._upload_csv_to_bigquery(
            dataset_id,
            csv_file_path=os.path.join(
                data_dir, "tampa_international_airport.csv"
            ),
            table_name="tampa_international_airport",
        )

        BUCKET_NAME = f"{self.bq_client.project}-mmqa-images"
        images_dir = os.path.join(data_dir, "images")
        self._upload_images_to_gcs(
            dataset_id,
            table_name="images",
            bucket_name=BUCKET_NAME,
            images_dir=images_dir,
        )
