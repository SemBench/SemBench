import os
from google.cloud import bigquery, storage
from google.cloud.storage import transfer_manager
import glob

SCHEMA_NAME = "FASHION_PRODUCT_IMAGES"

class BigQueryEcommSetup:
    def __init__(self):
        """
        Initializes the BigQuery client.
        Assumes GOOGLE_APPLICATION_CREDENTIALS is set in the environment.
        """
        self.bq_client = bigquery.Client()


    def _upload_parquet_to_bigquery(self, dataset_id: str, parquet_file_path: str, table_name: str):
        print(f"Uploading data into table {table_name} from {parquet_file_path}...")

        table_id = f"{dataset_id}.{table_name}"

        with open(parquet_file_path, "rb") as source_file:
            load_job = self.bq_client.load_table_from_file(
            source_file,
            table_id,
            job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.PARQUET,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            )
            )
        load_job.result()
    

    def _upload_images_to_gcs(self, dataset_id, table_name, bucket_name: str, images_dir: str):
        print(f"Uploading images from {images_dir} to GCS bucket {bucket_name}...")
        storage_client = storage.Client()
        bucket = storage_client.lookup_bucket(bucket_name)
        if bucket is None:
            print(f"Bucket {bucket_name} not found. Creating it...")
            bucket = storage_client.create_bucket(bucket_name)
        else:
            # Clear existing images in bucket to ensure clean state for new scale factor
            print(f"Clearing existing images from bucket {bucket_name}...")
            blobs = list(bucket.list_blobs())
            bucket.delete_blobs(blobs)
            print(f"Deleted {len(blobs)} existing images from bucket.")

        string_paths = [os.path.basename(f) for f in glob.glob(os.path.join(images_dir, '*.jpg'))]

        results = transfer_manager.upload_many_from_filenames(
            bucket, string_paths, source_directory=images_dir, max_workers=16
        )

        for name, result in zip(string_paths, results):
            if isinstance(result, Exception):
                print("Failed to upload {} due to exception: {}".format(name, result))
        
        # Create external table in BigQuery for images in GCS
        print(f"Creating external table {dataset_id}.{table_name} for images in GCS...")
        query_job = self.bq_client.query(f"""
            CREATE OR REPLACE EXTERNAL TABLE {dataset_id}.{table_name}
            WITH CONNECTION `us.connection`
            OPTIONS(
                object_metadata = 'SIMPLE',
                uris = ['gs://{bucket_name}/*.jpg']
            );
        """)
        query_job.result()
        

    def setup_data(self, data_dir: str):
        dataset_id = f"{self.bq_client.project}.fashion_product_images"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        self.bq_client.create_dataset(dataset, exists_ok=True)

        # TODO: also create the 'us.mmb-bigquery-storage-connection' BigQuery external connection

        self._upload_parquet_to_bigquery(dataset_id, parquet_file_path=os.path.join(data_dir, "styles.parquet"),  table_name='STYLES')
        self._upload_parquet_to_bigquery(dataset_id, parquet_file_path=os.path.join(data_dir, "styles_details.parquet"),  table_name='STYLES_DETAILS')
        self._upload_parquet_to_bigquery(dataset_id, parquet_file_path=os.path.join(data_dir, "image_mapping.parquet"),  table_name='IMAGE_MAPPING')

        # Upload images to Google Cloud Storage
        BUCKET_NAME = f"{self.bq_client.project}-mmb-fashion-product-images-bucket"
        images_dir = os.path.join(data_dir, 'images')
        self._upload_images_to_gcs(dataset_id, table_name='IMAGES', bucket_name=BUCKET_NAME, images_dir=images_dir)
