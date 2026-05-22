#!/usr/bin/env python3

"""
Standalone script for downloading and processing the Fashion Product Images dataset.
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import duckdb
import pyarrow.parquet as pq


def download_from_google_drive():
    """Download ecomm.tar.gz from Google Drive and extract it."""
    base_dir = Path(__file__).resolve().parents[3]
    source_data_dir = base_dir / "files" / "ecomm" / "source_data"
    source_data_dir.mkdir(parents=True, exist_ok=True)

    # The fashion-dataset folder should be in source_data after extraction
    data_path = source_data_dir / "fashion-dataset"

    # Check if data is already extracted
    if data_path.exists():
        print(f"Data already available at: {data_path}")
        print("Skipping download and extraction.")
        return str(data_path)

    # Download ecomm.tar.gz directly using file ID
    tar_file = source_data_dir / "ecomm.tar.gz"

    if not tar_file.exists():
        print("Downloading ecomm data from Google Drive...")
        print("Downloading ecomm.tar.gz...")
        # File ID: 1fVV9PLgIMT-e-zxFM5ksdnN8xQlfgnmb
        file_id = "1fVV9PLgIMT-e-zxFM5ksdnN8xQlfgnmb"

        # Try multiple download methods
        success = False

        # Method 1: Try gdown (handles large files better)
        print("Attempting download with gdown (handles large files)...")
        result = os.system(f"gdown 'https://drive.google.com/uc?id={file_id}' -O {tar_file}")
        if result == 0 and tar_file.exists() and tar_file.stat().st_size > 1000000:  # At least 1MB
            success = True
            print(f"Download successful with gdown (size: {tar_file.stat().st_size / 1024 / 1024:.1f}MB)")
        else:
            if tar_file.exists():
                os.remove(tar_file)

        # Method 2: Try wget with cookie handling for large files
        if not success:
            print("Attempting download with wget (handling Google Drive large file)...")
            cookie_file = source_data_dir / "cookie.txt"
            # First get the confirmation token
            os.system(f"wget --save-cookies {cookie_file} --keep-session-cookies --no-check-certificate 'https://drive.google.com/uc?export=download&id={file_id}' -O- 2>&1 | grep -o 'confirm=[^&]*' | sed 's/confirm=//' > {source_data_dir}/confirm.txt")

            # Read confirm token if exists
            confirm_file = source_data_dir / "confirm.txt"
            if confirm_file.exists():
                with open(confirm_file, 'r') as f:
                    confirm = f.read().strip()
                if confirm:
                    result = os.system(f"wget --load-cookies {cookie_file} --no-check-certificate 'https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}' -O {tar_file}")
                    # Clean up
                    os.remove(cookie_file)
                    os.remove(confirm_file)

                    if result == 0 and tar_file.exists() and tar_file.stat().st_size > 1000000:
                        success = True
                        print(f"Download successful with wget (size: {tar_file.stat().st_size / 1024 / 1024:.1f}MB)")
                    else:
                        if tar_file.exists():
                            os.remove(tar_file)

        # Method 3: Try curl with redirect handling
        if not success:
            print("Attempting download with curl...")
            result = os.system(f"curl -L -o {tar_file} 'https://drive.google.com/uc?export=download&id={file_id}'")
            if result == 0 and tar_file.exists() and tar_file.stat().st_size > 1000000:
                success = True
                print(f"Download successful with curl (size: {tar_file.stat().st_size / 1024 / 1024:.1f}MB)")
            else:
                if tar_file.exists():
                    os.remove(tar_file)

        if not success:
            raise RuntimeError(
                f"Failed to download ecomm.tar.gz from Google Drive using all methods.\n"
                f"The file might be too large for automated download.\n"
                f"Please manually download from: https://drive.google.com/file/d/{file_id}/view\n"
                f"And save it to: {tar_file}"
            )
    else:
        print(f"Archive file already exists at: {tar_file}")
        print("Skipping download.")

    print(f"Extracting {tar_file}...")
    os.system(f"tar -xzf {tar_file} -C {source_data_dir}")

    # Clean up tar file after extraction
    os.system(f"rm {tar_file}")

    # The tar file extracts to source_data/1/fashion-dataset
    # Move it to source_data/fashion-dataset for consistency
    extracted_path = source_data_dir / "1" / "fashion-dataset"
    if extracted_path.exists() and not data_path.exists():
        print(f"Moving data from {extracted_path} to {data_path}...")
        os.system(f"mv {extracted_path} {data_path}")
        # Clean up the intermediate directory
        os.system(f"rm -rf {source_data_dir / '1'}")

    if not data_path.exists():
        raise RuntimeError(
            f"Extraction completed but expected data not found at {data_path}"
        )

    print(f"Download and extraction completed. Data available at: {data_path}")
    return str(data_path)


def _download_fashion_product_images():
    """
    Downloads the Fashion Product Images dataset from Kaggle and returns the path to the downloaded dataset in the Kaggle system cache.
    This method is deprecated. Use download_from_google_drive() instead.
    """
    try:
        import kagglehub
        dataset_path = kagglehub.dataset_download(
            "paramaggarwal/fashion-product-images-dataset"
        )
        print(f"Download complete. Dataset available at: {dataset_path}")
        return dataset_path
    except ImportError:
        raise ImportError(
            "kagglehub is not installed. Please use --download-from-drive option instead."
        )


def _create_sample(target_dir: str, scale_factor: int, seed: int) -> str:
    """
    Creates a deterministic sample of the Fashion Product Images dataset based on the specified sampling factor.

    Args:
        target_dir: Base data directory (will create target_dir/sf_{scale_factor}/)
        scale_factor: The number of rows that will be included in the dataset.

    Returns:
        The path to the directory containing the sampled dataset.
    """
    input_dir = os.path.join(target_dir, "fashion_product_images")
    out_dir = os.path.abspath(
        os.path.join(target_dir, f"sf_{scale_factor}")
    )
    if os.path.exists(out_dir):
        print(
            f"Sample directory {out_dir} already exists. Skipping sample creation."
        )
        return out_dir

    os.makedirs(out_dir, exist_ok=True)
    print(f"Creating sample with size: {scale_factor} at: {out_dir}")

    num_extra_rows = 43  # Number of rows that are definitely included and bypass the random sampling such that certain queries have a solution
    if scale_factor <= num_extra_rows:
        raise ValueError(
            f"Scale factor must be greater than {num_extra_rows} to ensure query solutions."
        )

    # Create a sample from one table; the others can then be joined to it.
    duckdb.sql(
        f"""
        COPY (
            SELECT *
            FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}')
            USING SAMPLE {scale_factor - num_extra_rows} (reservoir, {seed})
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (5299, 5300, 5301, 1623, 1624, 5303, 5314)  -- Ensure solution for Q1
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (10037, 10102, 3312, 41825, 3462) -- Ensure solution for Q2
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (3351, 30292, 10689, 8419) -- Ensure solution for Q7
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (12799, 2048, 2606, 2607, 3479, 4038, 4800, 4805, 4817, 2045, 43047, 4811) -- Ensure solution for Q8
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (6241, 1891, 53126, 1563, 15779, 47525) -- Ensure solution for Q9
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (6100, 7935, 10579) -- Ensure solution for Q10
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (8103, 13112, 8402, 3470) -- Ensure solution for Q11
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (43047, 12799, 4811) -- Ensure solution for Q13
            UNION
            SELECT * FROM read_parquet('{os.path.join(input_dir, 'styles.parquet')}') WHERE id IN (18345, 29202) -- Ensure solution for Q14
        )
        TO '{os.path.join(out_dir, 'styles.parquet')}' (FORMAT PARQUET)
    """
    )

    duckdb.sql(
        f"""
        COPY (
            SELECT styles_details.*
            FROM read_parquet('{os.path.join(out_dir, 'styles.parquet')}') AS styles
            JOIN read_parquet('{os.path.join(input_dir, 'styles_details.parquet')}') AS styles_details
            ON styles_details.id = styles.id
        )
        TO '{os.path.join(out_dir, 'styles_details.parquet')}' (FORMAT PARQUET)
    """
    )

    duckdb.sql(
        f"""
        COPY (
            SELECT image_mapping.*
            FROM read_parquet('{os.path.join(out_dir, 'styles.parquet')}') AS styles
            JOIN read_parquet('{os.path.join(input_dir, 'image_mapping.parquet')}') AS image_mapping
            ON image_mapping.id = styles.id
        )
        TO '{os.path.join(out_dir, 'image_mapping.parquet')}' (FORMAT PARQUET)
    """
    )

    # Symlink necessary image files
    os.makedirs(os.path.join(out_dir, "images"), exist_ok=True)
    table = pq.read_table(os.path.join(out_dir, "image_mapping.parquet"))
    for filename in table["filename"]:
        src = os.path.join(input_dir, "images", filename.as_py())
        dst = os.path.join(out_dir, "images", filename.as_py())
        if not os.path.islink(dst) and not os.path.exists(dst):
            os.symlink(os.path.realpath(src), dst)

    return out_dir


def download_and_postprocess_data(
    target_dir: str, scale_factor: int = None, use_google_drive: bool = False
) -> str:
    """
    Downloads the Fashion Product Images dataset into the specified target directory and processes it into Parquet files.
    Optionally creates a sample of the dataset based on the provided sampling factor.

    Args:
        target_dir: The directory where the dataset will be downloaded to.
        scale_factor: Number of rows that will be included in the dataset or None if the maximum dataset size should be used.
        use_google_drive: If True, download from Google Drive instead of Kaggle.

    Returns:
        The path to the directory containing the processed dataset.
    """
    if use_google_drive:
        source_path = download_from_google_drive()
    else:
        kaggle_cache_path = _download_fashion_product_images()
        source_path = os.path.join(kaggle_cache_path, 'fashion-dataset')

    out_dir = os.path.join(target_dir, "fashion_product_images")
    os.makedirs(out_dir, exist_ok=True)

    # Process styles.csv
    output_path = os.path.join(out_dir, "styles.parquet")
    print(f"Creating {output_path}")
    if not os.path.exists(output_path):
        duckdb.sql(
            f"""
            COPY (
                SELECT *
                FROM read_csv('{os.path.join(source_path, 'styles.csv')}', header=true, delim=',', quote='"', ignore_errors=true)
            )
            TO '{output_path}' (FORMAT PARQUET)
        """
        )

    # Process images.csv
    output_path = os.path.join(out_dir, "image_mapping.parquet")
    if not os.path.exists(output_path):
        print(f"Creating {output_path}")
        duckdb.sql(
            f"""
            COPY (
                SELECT split_part(filename, '.', 1) as id, filename, link
                FROM read_csv('{os.path.join(source_path, 'images.csv')}', header=true)
            )
            TO '{output_path}' (FORMAT PARQUET)
        """
        )

    # Process styles/*.json files
    output_path = os.path.join(out_dir, "styles_details.parquet")
    if not os.path.exists(output_path):
        print(f"Creating {output_path}")
        with duckdb.connect() as con:
            con.execute("SET threads = 2;")
            con.execute("SET preserve_insertion_order=false;")
            con.execute(
                f"""
            COPY (
                SELECT unnest(data)
                FROM read_json('{os.path.join(source_path, 'styles', '*.json')}', union_by_name=true)
            )
            TO '{output_path}' (FORMAT PARQUET)
            """
            )
        print(f"Parquet file created at: {output_path}")

    # Process images/*.jpg files
    output_path = os.path.join(out_dir, "images")
    if not os.path.exists(output_path):
        print(f"Linking images to {output_path}")
        os.symlink(
            os.path.join(source_path, "images"),
            output_path,
            target_is_directory=True,
        )

    if scale_factor is not None:
        sample_dir = _create_sample(target_dir, scale_factor, 12345600)
        return sample_dir
    else:
        return out_dir


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Download and process Fashion Product Images dataset'
    )
    parser.add_argument(
        '--download-from-drive',
        action='store_true',
        help='Download data from Google Drive instead of Kaggle'
    )
    parser.add_argument(
        '--scale-factor',
        type=int,
        default=None,
        help='Number of rows to include in the dataset (None for full dataset)'
    )
    args = parser.parse_args()

    target_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "files",
            "ecomm",
            "data",
        )
    )

    download_and_postprocess_data(
        target_dir=target_dir,
        scale_factor=args.scale_factor,
        use_google_drive=args.download_from_drive
    )

    # TODO:
    # maybe filter some data, e.g.:
    # * baseColour should not be 'NA' or ''
    # * description should have at least x characters
