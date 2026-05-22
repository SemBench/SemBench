import argparse
import os

import pandas as pd


RANDOM_SEED = 42
FIXED_FILES = ["ben_piazza.csv", "ap_warrior.csv"]
BASE_BEN_PIAZZA_TEXT_DATA_FILENAME = "base_ben_piazza_text_data.csv"
BASE_LIZZY_CAPLAN_TEXT_DATA_FILENAME = "base_lizzy_caplan_text_data.csv"
BASE_TAMPA_AIRPORT_FILENAME = "base_tampa_international_airport.csv"
ADDITIONAL_MOVIES_FILENAME = "additional_movies.csv"
ADDITIONAL_AIRPORTS_FILENAME = "additional_airports.csv"
IMAGE_DIR_NAME = "mmqa_1k_images"
FIXED_IMAGE_FILENAMES = [
    "1sz0kf8wcmj0q8n3pu6mg61gl158vvz1.png",
    "6zpijbg5jv4jftpftpmla6xbizne28d9.png",
    "42c88eafedfab5203c72e1d2ec1c2f37.jpg",
    "117d500aaa630023c4038b8268b309c0.png",
    "5588a1833b8fa95fe1b0ed520e447d64.jpg",
    "antbx4oxst0z5o6pe2g1thrjr0dz073j.png",
    "cwncgabxti09zmf36t4phvaz1xzv10wu.png",
    "nqr1pjql5qs3dp8rz2a4zzq7rn0xyp6k.png",
]


class MMQADataGenerator:
    def __init__(
        self, working_dir: str, scale_factor: int, skip_download: bool = False
    ):
        assert scale_factor in range(
            25, 1001
        ), "Scale factor must be in the range [25, 1000]."

        self.working_dir = working_dir
        self.scale_factor = scale_factor
        self.source_data_dir = os.path.join(
            self.working_dir, "files/mmqa/source_data"
        )
        self.output_data_dir = os.path.join(
            self.working_dir, "files/mmqa/data", f"sf_{self.scale_factor}"
        )

        if skip_download:
            assert os.path.exists(
                self.source_data_dir
            ), f"Source data directory '{self.source_data_dir}' does not exist while skip_download is set to True."  # noqa: E501
        else:
            os.makedirs(self.source_data_dir, exist_ok=True)
            self._download_source_data()

        os.makedirs(self.output_data_dir, exist_ok=True)

    def _download_source_data(self):
        # Check if data is already extracted
        # MMQA source data should have these fixed files
        required_files = [
            os.path.join(self.source_data_dir, BASE_BEN_PIAZZA_TEXT_DATA_FILENAME),
            os.path.join(self.source_data_dir, ADDITIONAL_MOVIES_FILENAME),
        ]

        if all(os.path.exists(f) for f in required_files):
            print(f"Source data already available at: {self.source_data_dir}")
            print("Skipping download and extraction.")
            return

        zip_file = os.path.join(self.source_data_dir, "mmqa_source_data.zip")

        if not os.path.exists(zip_file):
            print(f"Downloading source data to {self.source_data_dir}...")
            os.system(
                f"gdown 'https://drive.google.com/uc?id=1oHXq5oxIfsyoNy9aCQ0V9G3W4puqHC6i' -O {zip_file}"  # noqa: E501
            )
        else:
            print(f"Archive file already exists at: {zip_file}")
            print("Skipping download.")

        os.system(
            f"unzip {zip_file} -d {self.source_data_dir}"  # noqa: E501
        )
        os.system(f"rm {zip_file}")
        os.system(f"rm -r {self.source_data_dir}/__MACOSX 2>/dev/null || true")
        os.system(
            f"mv {self.source_data_dir}/mmqa_data/* {self.source_data_dir}/ 2>/dev/null || true"
        )
        os.system(f"rm -r {self.source_data_dir}/mmqa_data 2>/dev/null || true")

        print("Download completed.")

    def _copy_fixed_files(self):
        for filename in FIXED_FILES:
            src = os.path.join(self.source_data_dir, filename)
            dst = os.path.join(self.output_data_dir, filename)
            if os.path.exists(src):
                os.system(f"cp {src} {dst}")
            else:
                raise FileNotFoundError(
                    f"Source data file '{filename}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
                )

    def _generate_ben_piazza_text_data_per_scale_factor(self):
        base_filepath = os.path.join(
            self.source_data_dir, BASE_BEN_PIAZZA_TEXT_DATA_FILENAME
        )
        if not os.path.exists(base_filepath):
            raise FileNotFoundError(
                f"Source data file '{BASE_BEN_PIAZZA_TEXT_DATA_FILENAME}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
            )

        additional_filepath = os.path.join(
            self.source_data_dir, ADDITIONAL_MOVIES_FILENAME
        )
        if not os.path.exists(additional_filepath):
            raise FileNotFoundError(
                f"Source data file '{ADDITIONAL_MOVIES_FILENAME}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
            )

        base_df = pd.read_csv(base_filepath)
        additional_df = pd.read_csv(additional_filepath)
        num_rows = len(base_df)
        num_rows_to_add = self.scale_factor - num_rows

        rows_to_add = additional_df.sample(
            n=num_rows_to_add, replace=False, random_state=RANDOM_SEED
        )
        final_df = pd.concat([base_df, rows_to_add], ignore_index=True)
        final_df = final_df.sample(
            frac=1, random_state=RANDOM_SEED
        ).reset_index(drop=True)

        final_df.index.name = "row_id"
        final_df.to_csv(
            os.path.join(self.output_data_dir, "ben_piazza_text_data.csv"),
            index=True,
        )

    def _generate_lizzy_caplan_text_data_per_scale_factor(self):
        base_filepath = os.path.join(
            self.source_data_dir, BASE_LIZZY_CAPLAN_TEXT_DATA_FILENAME
        )
        if not os.path.exists(base_filepath):
            raise FileNotFoundError(
                f"Source data file '{BASE_LIZZY_CAPLAN_TEXT_DATA_FILENAME}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
            )

        additional_filepath = os.path.join(
            self.source_data_dir, ADDITIONAL_MOVIES_FILENAME
        )
        if not os.path.exists(additional_filepath):
            raise FileNotFoundError(
                f"Source data file '{ADDITIONAL_MOVIES_FILENAME}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
            )

        base_df = pd.read_csv(base_filepath)
        additional_df = pd.read_csv(additional_filepath)
        additional_df = additional_df.drop("id", axis=1)
        num_rows = len(base_df)
        num_rows_to_add = self.scale_factor - num_rows

        rows_to_add = additional_df.sample(
            n=num_rows_to_add, replace=False, random_state=RANDOM_SEED
        )
        final_df = pd.concat([base_df, rows_to_add], ignore_index=True)
        final_df = final_df.sample(
            frac=1, random_state=RANDOM_SEED
        ).reset_index(drop=True)

        final_df.index.name = "row_id"
        final_df.to_csv(
            os.path.join(self.output_data_dir, "lizzy_caplan_text_data.csv"),
            index=True,
        )

    def _generate_airport_text_data_per_scale_factor(self):
        base_filepath = os.path.join(
            self.source_data_dir, BASE_TAMPA_AIRPORT_FILENAME
        )
        if not os.path.exists(base_filepath):
            raise FileNotFoundError(
                f"Source data file '{BASE_TAMPA_AIRPORT_FILENAME}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
            )

        additional_filepath = os.path.join(
            self.source_data_dir, ADDITIONAL_AIRPORTS_FILENAME
        )
        if not os.path.exists(additional_filepath):
            raise FileNotFoundError(
                f"Source data file '{ADDITIONAL_AIRPORTS_FILENAME}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
            )

        base_df = pd.read_csv(base_filepath)
        base_df = base_df.drop("ID", axis=1)
        base_df = base_df.drop("Seasonal Destinations", axis=1)
        additional_df = pd.read_csv(additional_filepath)
        num_rows = len(base_df)
        num_rows_to_add = self.scale_factor - num_rows

        rows_to_add = additional_df.sample(
            n=num_rows_to_add, replace=False, random_state=RANDOM_SEED
        )
        final_df = pd.concat([base_df, rows_to_add], ignore_index=True)
        final_df = final_df.sample(
            frac=1, random_state=RANDOM_SEED
        ).reset_index(drop=True)

        final_df.index.name = "row_id"
        final_df.to_csv(
            os.path.join(
                self.output_data_dir, "tampa_international_airport.csv"
            ),
            index=True,
        )

    def _generate_images_per_scale_factor(self):
        source_image_dir = os.path.join(self.source_data_dir, IMAGE_DIR_NAME)
        if not os.path.exists(source_image_dir):
            raise FileNotFoundError(
                f"Source image directory '{IMAGE_DIR_NAME}' not found in source data directory: {self.source_data_dir}"  # noqa: E501
            )

        output_image_dir = os.path.join(self.output_data_dir, "images")
        os.makedirs(output_image_dir, exist_ok=True)

        for filename in FIXED_IMAGE_FILENAMES:
            src = os.path.join(source_image_dir, filename)
            dst = os.path.join(output_image_dir, filename)
            if os.path.exists(src):
                os.system(f"cp {src} {dst}")
            else:
                raise FileNotFoundError(
                    f"Source image file '{filename}' not found in source image directory: {source_image_dir}."  # noqa: E501
                )

        num_images_to_add = self.scale_factor - len(FIXED_IMAGE_FILENAMES)
        additional_images = [
            f
            for f in os.listdir(source_image_dir)
            if f not in FIXED_IMAGE_FILENAMES and f.endswith((".png", ".jpg"))
        ]
        if num_images_to_add > 0:
            if num_images_to_add > len(additional_images):
                raise ValueError(
                    f"Not enough additional images to reach the desired scale factor of {self.scale_factor}."  # noqa: E501
                )
            selected_images = pd.Series(additional_images).sample(
                n=num_images_to_add, replace=False, random_state=RANDOM_SEED
            )
            for filename in selected_images:
                src = os.path.join(source_image_dir, filename)
                dst = os.path.join(output_image_dir, filename)
                os.system(f"cp {src} {dst}")

        # Generate a csv file of image metadata needed for ThalamusDB
        all_images = FIXED_IMAGE_FILENAMES + selected_images.tolist()
        all_image_filepaths = [
            os.path.join(output_image_dir, f) for f in all_images
        ]
        image_df = pd.DataFrame(
            {
                "image_filename": all_images,
                "image_filepath": all_image_filepaths,
            }
        )
        image_df.index.name = "row_id"
        image_df.to_csv(
            os.path.join(self.output_data_dir, "thalamusdb_images.csv"),
            index=True,
        )

    def _generate_data_per_scale_factor(self):
        self._generate_ben_piazza_text_data_per_scale_factor()
        self._generate_lizzy_caplan_text_data_per_scale_factor()
        self._generate_airport_text_data_per_scale_factor()
        self._generate_images_per_scale_factor()

    def generate_data(self):
        print(f"Generating data with scale factor: {self.scale_factor}...")

        self._copy_fixed_files()
        self._generate_data_per_scale_factor()

        print("Data generation completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--working_dir",
        type=str,
        required=True,
        help="The working directory containing SemBench code. E.g., /home/<user>/MMBench-System",  # noqa: E501
    )

    parser.add_argument(
        "--scale_factor",
        type=int,
        required=True,
        help="The scale factor for the generated data. Valid range: [25, 1000]",
    )

    parser.add_argument(
        "--skip_download",
        action="store_true",
        help="Skip downloading source data.",
    )

    args = parser.parse_args()

    data_generator = MMQADataGenerator(
        working_dir=args.working_dir,
        scale_factor=args.scale_factor,
        skip_download=False,
    )
    data_generator.generate_data()
