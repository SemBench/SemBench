"""
Created on Jun 28, 2025

@author: OlgaOvcharenko

Creates test database from the following Kaggle datasets:
- https://www.kaggle.com/datasets/niyarrbarman/symptom2disease/
- https://www.kaggle.com/datasets/fernando2rad/x-ray-lung-diseases-images-9-classes
- https://www.kaggle.com/datasets/datasetengineer/lungcanc2024?select=LungCanC2024_Dataset.csv
- https://www.kaggle.com/datasets/arashnic/lung-dataset
- https://www.kaggle.com/datasets/fanconic/skin-cancer-malignant-vs-benign


To download only the X-ray and audio datasets, call this script with default arguments or use Google Drive link:
https://drive.google.com/file/d/1P4V_RWWDMxz4X-oG65Ph5-K2gmNGFpP-/view?usp=sharing

To download only the X-ray and audio datasets, call this script with default arguments or use Google Drive link:
https://drive.google.com/file/d/1v4--C7PE_SQDNZj6hZ8wNn4OvswIyu2s/view?usp=sharing
"""

import argparse
from genericpath import isfile
import glob
import time
import numpy as np
import pandas as pd
import random
import os
import shutil
from pathlib import Path
from os import listdir
from os.path import isdir, join


def replace_multiple(text, replacements):
    for key, val in replacements.items():
        text = text.replace(key, val)
    return text


def _download_from_drive(id: str, file_name: str = "raw_data.zip", folder: str = None):
    """Download and extract data from Google Drive.

    Args:
        id: Google Drive file ID
        file_name: Name of the zip file
        folder: Target folder for extraction. If None, uses appropriate default based on file_name.
    """
    # Use absolute path if folder not specified
    if folder is None:
        base_path = Path(__file__).resolve().parents[4]
        # medical_data.zip contains processed CSVs, goes to files/medical/
        # raw_data.zip contains raw source data, goes to files/medical/source_data/
        if file_name == "medical_data.zip":
            folder = str(base_path / "files" / "medical")
        else:
            folder = str(base_path / "files" / "medical" / "source_data")

    # Check if data is already extracted
    raw_data_dir = os.path.join(folder, "raw_data")
    # Check for key subdirectories that should exist after extraction
    expected_dirs = [
        os.path.join(raw_data_dir, "lung-dataset"),
        os.path.join(raw_data_dir, "x-ray"),
    ]

    if os.path.exists(raw_data_dir) and all(os.path.exists(d) for d in expected_dirs):
        print(f"Data already available at: {raw_data_dir}")
        print("Skipping download and extraction.")
        return

    # Ensure folder exists
    os.makedirs(folder, exist_ok=True)

    # Download to the target folder
    zip_path = os.path.join(folder, file_name)

    if not os.path.exists(zip_path):
        print(f"Downloading {file_name} from Google Drive to {folder}...")
        os.system(f"gdown 'https://drive.google.com/uc?id={id}' -O {zip_path}")
    else:
        print(f"Archive file already exists at: {zip_path}")
        print("Skipping download.")

    # Use -o flag to overwrite files without prompting
    print(f"Extracting {zip_path} to {folder}...")
    os.system(
        f"unzip -o {zip_path} -d {folder}"
    )
    os.system(f"rm {zip_path}")


def _download_kaggle_datasets():
    """Downloads the required Kaggle datasets.

    Note: For the X-ray dataset, there can be error when trying to fully download the dataset via cURL.
    Solution is to download the dataset manually from Kaggle and place it in the correct folder.
    """
    # Use absolute paths
    base_path = Path(__file__).resolve().parents[4]
    source_data_path = base_path / "files" / "medical" / "source_data" / "raw_data"

    if not os.path.exists(source_data_path):
        os.makedirs(source_data_path, exist_ok=True)

    lung_dataset_path = source_data_path / "lung-dataset"
    if not os.path.exists(lung_dataset_path):
        os.system(
            f"curl -L -o {source_data_path}/lung-dataset.zip https://www.kaggle.com/api/v1/datasets/download/arashnic/lung-dataset"
        )
        os.system(
            f"unzip {source_data_path}/lung-dataset.zip -d {lung_dataset_path}"
        )
        os.system(f"rm {source_data_path}/lung-dataset.zip")

    lungcanc_path = source_data_path / "lungcanc2024"
    if not os.path.exists(lungcanc_path):
        os.system(
            f"curl -L -o {source_data_path}/lungcanc2024.zip https://www.kaggle.com/api/v1/datasets/download/datasetengineer/lungcanc2024"
        )
        os.system(
            f"unzip {source_data_path}/lungcanc2024.zip -d {lungcanc_path}"
        )
        os.system(f"rm {source_data_path}/lungcanc2024.zip")

    xray_path = source_data_path / "x-ray"
    if not os.path.exists(xray_path):
        os.system(
            f"curl -L -o {source_data_path}/x-ray-lung-diseases-images-9-classes.zip https://www.kaggle.com/api/v1/datasets/download/fernando2rad/x-ray-lung-diseases-images-9-classes"
        )
        os.system(
            f"unzip {source_data_path}/x-ray-lung-diseases-images-9-classes.zip -d {xray_path}"
        )
        os.system(
            f"rm {source_data_path}/x-ray-lung-diseases-images-9-classes.zip"
        )

    diagnosis_path = source_data_path / "diagnosis"
    if not os.path.exists(diagnosis_path):
        os.system(
            f"curl -L -o {source_data_path}/symptom2disease.zip https://www.kaggle.com/api/v1/datasets/download/niyarrbarman/symptom2disease"
        )
        os.system(
            f"unzip {source_data_path}/symptom2disease.zip -d {diagnosis_path}"
        )
        os.system(f"rm {source_data_path}/symptom2disease.zip")

    skin_cancer_path = source_data_path / "skin_cancer"
    if not os.path.exists(skin_cancer_path):
        os.system(
            f"curl -L -o {source_data_path}/skin_cancer.zip https://www.kaggle.com/api/v1/datasets/download/fanconic/skin-cancer-malignant-vs-benign"
        )
        os.system(
            f"unzip {source_data_path}/skin_cancer.zip -d {skin_cancer_path}"
        )
        os.system(f"rm {source_data_path}/skin_cancer.zip")

def _add_random_patient_history(
    df: pd.DataFrame, smoking, family_cancer
) -> pd.DataFrame:
    """Adds random locations to the DataFrame.

    Args:
        df: DataFrame to which random locations are added.

    Returns:
        DataFrame with additional columns for city and station ID.
    """
    # Add columns with random smoking history and family cancer history to add to patient data
    df["smoking_history"] = [random.choice(smoking) for _ in range(len(df))]
    df["did_family_have_cancer"] = [
        random.choice(family_cancer) for _ in range(len(df))
    ]
    return df


def _create_patient_audio_tables(
    lung_patient_table: pd.DataFrame, lung_patient_audio_table: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Creates and returns two DataFrames:
      1. A patient table with unique patient IDs and audio diagnosis.
      2. An audio table with unwrapped audio files, one per row.

    Args:
        lung_patient_table: DataFrame with patient data.
        lung_patient_audio_table: DataFrame with audio data linked to patients.

    Returns:
        Tuple containing:
            - patient_table (pd.DataFrame): Patient records with diagnoses and IDs.
            - audio_table (pd.DataFrame): One row per audio recording with metadata.
    """
    # Enrich audio table with synthetic patient history
    lung_patient_audio_table = _add_random_patient_history(
        lung_patient_audio_table,
        smoking=lung_patient_table["smoking_history"].unique(),
        family_cancer=lung_patient_table["did_family_have_cancer"].unique(),
    )

    # Add dummy diagnosis to patient table
    lung_patient_table = lung_patient_table.copy()
    lung_patient_table["diagnosis"] = "none"

    # Combine both tables and assign patient_id
    combined = pd.concat(
        [lung_patient_table, lung_patient_audio_table],
        axis=0,
        ignore_index=True,
        copy=True,
    )
    combined["patient_id"] = combined.index

    # Separate into patient and audio tables
    patient_columns = list(lung_patient_table.columns) + ["patient_id"]
    patient_table = combined[patient_columns].copy()
    patient_table.rename(columns={"diagnosis": "audio_diagnosis"}, inplace=True)

    # Get audio entries with valid audio file paths
    audio_mask = combined["diaphragm_filtration_path"].notna()
    audio_columns = list(
        set(lung_patient_audio_table.columns) - set(lung_patient_table.columns)
    ) + ["patient_id"]

    audio_table = combined.loc[audio_mask, audio_columns].copy()
    audio_table.rename(
        columns={
            "diaphragm_filtration_path": "diaphragm",
            "extended_filtration_path": "extended",
            "bell_filtration_path": "bell",
        },
        inplace=True,
    )

    # Unpivot audio paths into single 'path' column
    audio_table = audio_table.melt(
        id_vars=["patient_id", "location"],
        var_name="filtration_type",
        value_name="path",
    )

    # Assign unique audio_id
    audio_table["audio_id"] = audio_table.index

    return patient_table, audio_table


def _prepare_lung_audio_data(data_path: str) -> pd.DataFrame:
    """
    Prepares a tables with patients and their audio from Kaggle.

    Args:
        audio_path: Path to Kaggle data with audio files recordings.

    Returns:
        DataFrame with audio data.
    """

    lung_audio_table = pd.read_csv(f"{data_path}/data_annotation.csv")
    lung_audio_table["bell_filtration_path"] = ""
    lung_audio_table["diaphragm_filtration_path"] = ""
    lung_audio_table["extended_filtration_path"] = ""

    onlyfiles = [f for f in listdir(join(data_path, "Audio Files")) if isfile(join(join(data_path, "Audio Files"), f))]
    for filename in onlyfiles:
        id_type = filename.split("_")[0]
        type, id = id_type[0:2], int(id_type[2:])

        path_col = ''
        if type == "BP":
            path_col = "bell_filtration_path"
        elif type == "DP":
            path_col = "diaphragm_filtration_path"
        elif type == "EP":
            path_col = "extended_filtration_path"

        lung_audio_table.loc[id-1, path_col] = os.path.join(data_path, "Audio Files", filename)

    # Decode location acronyms
    loc_map_0 = {"A": "Anterior", "P": "Posterior"}
    loc_map_1 = {"L": "Left", "R": "Right"}
    loc_map_2 = {"L": "Lower", "U": "Upper", "M": "Middle"}

    lung_audio_table["location"] = (
        lung_audio_table["location"].str.get(0).map(loc_map_0).fillna("Unknown")
        + " "
        + lung_audio_table["location"].str.get(2).map(loc_map_1).fillna("Unknown")
        + " "
        + lung_audio_table["location"].str.get(4).map(loc_map_2).fillna("Unknown")
    )

    # Recode gender
    lung_audio_table["gender"] = (
        lung_audio_table["gender"]
        .str.slice(start=0, stop=1)
        .replace({"M": "Male", "F": "Female"})
    )

    lung_audio_table.drop(columns=["sound_type"], inplace=True)

    # Recode diagnosis
    lung_audio_table["diagnosis"] = (
        lung_audio_table["diagnosis"]
        .str.lower()
        .replace("n", "normal")
        .replace("asthma and lung fibrosis", "asthma + lung fibrosis")
    )

    return lung_audio_table


def _prepare_lung_patient_data(data_path: str, seed: int) -> pd.DataFrame:
    """
    Prepares a table referencing annotations table and audio data from Kaggle.

    Args:
        data_path: Path to Kaggle data with cancer patients.

    Returns:
        DataFrame with patient data.
    """

    lung_patient_table = pd.read_csv(f"{data_path}/LungCanC2024_Dataset.csv")
    lung_patient_table = lung_patient_table[
        ["patient_age", "patient_gender", "smoking_history", "family_history"]
    ]
    lung_patient_table.rename(
        columns={
            "patient_age": "age",
            "patient_gender": "gender",
            "family_history": "did_family_have_cancer",
        },
        inplace=True,
    )

    # FIXME Is needed?
    lung_patient_table = lung_patient_table.sample(
        n=11000, random_state=seed, ignore_index=True
    )

    return lung_patient_table


def _prepare_xray_data(data_path: str) -> pd.DataFrame:
    """
    Prepares a x-ray images.

    Args:
        data_path: Path to Kaggle data.

    Returns:
        DataFrame with X-ray data.
    """
    desease_image = [
        [img_path.split("/")[-2], img_path]
        for img_path in glob.glob(f"{data_path}/**/*", recursive=True)
        if isfile(img_path) and img_path.endswith((".jpg", ".jpeg", ".png"))
    ]
    x_rays = pd.DataFrame(desease_image, columns=["diagnosis", "image_path_orig"])
    x_rays["diagnosis"] = x_rays["diagnosis"].str.lower()

    # Create nested directory with all images together
    base_path = Path(__file__).resolve().parents[4]
    new_folder_path = str(base_path / 'files' / 'medical' / 'source_data' / 'raw_data' / 'all_x_rays')
    is_created = False
    try:
        os.makedirs(new_folder_path)
    except FileExistsError:
        print(f"Directory '{new_folder_path}' already exists.")
        is_created = True

    x_rays["image_path"] = ""
    for i, image_path in zip(x_rays.index, x_rays["image_path_orig"]):    
        src_image = image_path
        dst_image = new_folder_path + str(i) + "_" + image_path.split("/")[-2] + "_" + image_path.split("/")[-1]
        
        if not is_created:
            shutil.copy(src_image, dst_image)
        
        x_rays.loc[i, "image_path"] = dst_image

    return x_rays[["diagnosis", "image_path"]]

def _prepare_skin_image_data(data_path: str) -> pd.DataFrame:
    """
    Prepares a skin cancer images.

    Args:
        data_path: Path to Kaggle data.

    Returns:
        DataFrame with data.
    """
    desease_image = [
        [img_path.split("/")[-2], img_path]
        for img_path in glob.glob(f"{data_path}/**/*", recursive=True)
        if isfile(img_path) and img_path.endswith((".jpg", ".jpeg", ".png"))
    ]

    cancer_images = pd.DataFrame(desease_image, columns=["diagnosis", "image_path_orig"])
    cancer_images["diagnosis"] = cancer_images["diagnosis"].str.lower()

    # Create nested directory with all images together
    base_path = Path(__file__).resolve().parents[4]
    new_folder_path = str(base_path / 'files' / 'medical' / 'source_data' / 'raw_data' / 'all_skin_images')
    is_created = False
    try:
        os.makedirs(new_folder_path)
    except FileExistsError:
        print(f"Directory '{new_folder_path}' already exists.")
        is_created = True

    cancer_images["image_path"] = ""
    for i, image_path in zip(cancer_images.index, cancer_images["image_path_orig"]):    
        src_image = image_path
        dst_image = new_folder_path + str(i) + "_" + image_path.split("/")[-3] + "_" + image_path.split("/")[-2] + "_" + image_path.split("/")[-1]

        if not is_created:
            shutil.copy(src_image, dst_image)

        cancer_images.loc[i, "image_path"] = dst_image
    
    return cancer_images[["diagnosis", "image_path"]]


def _prepare_text_data(data_path: str) -> pd.DataFrame:
    """
    Prepares a diagnosis texts.

    Args:
        data_path: Path to Kaggle data with symptoms.

    Returns:
        DataFrame with patient data.
    """
    # all_classes = [f for f in listdir(data_path) if isdir(join(data_path, f))]

    lung_audio_table = pd.read_csv(f"{data_path}/Symptom2Disease.csv")[
        ["label", "text"]
    ]
    lung_audio_table.rename(
        columns={"label": "diagnosis", "text": "symptoms"}, inplace=True
    )
    lung_audio_table["diagnosis"] = lung_audio_table["diagnosis"].str.lower()

    return lung_audio_table


def _shuffle_tables(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sample(frac=1).reset_index(drop=True)
    return df


def _create_xray_table(
    patient_table: pd.DataFrame, lung_x_ray_data: pd.DataFrame, seed: int
) -> pd.DataFrame:
    """
    Prepares an x-ray table with patients and their x-ray images from Kaggle.

    Returns:
        DataFrame with patient data.
    """

    lung_x_ray_data["patient_id"] = None

    corespondance_dict = {
        "00_normal": ["normal"],
        "01_inflammatory_processes": ["pneumonia"],
        "05_degenerative_infectious_diseases": ["lung fibrosis"],
        "02_higher_density": ["plueral effusion"],
        "04_obstructive_pulmonary_diseases": ["bron", "copd", "asthma"],
    }

    patient_table["x_ray_diagnosis"] = "none"

    xray_classes_counts = lung_x_ray_data["diagnosis"].value_counts()

    for diagnosis_xray, count in xray_classes_counts.items():
        if diagnosis_xray in corespondance_dict:
            condition = (
                patient_table["audio_diagnosis"]
                .isin(corespondance_dict[diagnosis_xray] + ["none"])
                .to_numpy()
                & (patient_table["x_ray_diagnosis"] == "none").to_numpy()
            )
        else:
            condition = (patient_table["audio_diagnosis"] == "none").to_numpy() & (
                patient_table["x_ray_diagnosis"] == "none"
            ).to_numpy()

        ids = patient_table.loc[condition, "patient_id"].sample(
            n=count, random_state=seed
        )
        lung_x_ray_data.loc[
            lung_x_ray_data["diagnosis"] == diagnosis_xray, "patient_id"
        ] = ids.index
        patient_table.loc[ids.index, "x_ray_diagnosis"] = diagnosis_xray

    lung_x_ray_data = lung_x_ray_data[["image_path", "patient_id"]]
    lung_x_ray_data["xray_id"] = lung_x_ray_data.index

    return patient_table, lung_x_ray_data


def _create_text_symptoms_table(
    patient_table: pd.DataFrame, text_symptoms_data: pd.DataFrame, seed: int
) -> pd.DataFrame:
    """
    Prepares an x-ray table with patients and their x-ray images from Kaggle.

    Args:
        patient_table: Table with patient data.
        text_symptoms_data: Table with symptoms texts.

    Returns:
        DataFrame with patient data.
    """

    text_symptoms_data["patient_id"] = None

    corespondance_dict = {
        "pneumonia": ["01_inflammatory_processes", "pneumonia"],
        "bronchial asthma": [
            "04_obstructive_pulmonary_diseases",
            "04_obstructive_pulmonary_diseases",
            "bron",
            "asthma",
            "copd",
        ],
        "hypertension": ["heart failure"],
    }

    patient_table["text_diagnosis"] = "none"

    symptoms_classes_counts = text_symptoms_data["diagnosis"].value_counts()

    for diagnosis, count in symptoms_classes_counts.items():
        if diagnosis in corespondance_dict:
            condition = (
                patient_table["audio_diagnosis"].isin(
                    corespondance_dict[diagnosis] + ["none", "normal"]
                )
                & patient_table["x_ray_diagnosis"].isin(
                    corespondance_dict[diagnosis] + ["none", "00_normal"]
                )
                & (patient_table["text_diagnosis"] == "none")
            )

        else:
            condition = (
                patient_table["audio_diagnosis"].isin(["none", "normal"])
                & patient_table["x_ray_diagnosis"].isin(["none", "00_normal"])
                & (patient_table["text_diagnosis"] == "none")
            )

        ids = patient_table.loc[condition, "patient_id"].sample(
            n=count, random_state=seed
        )
        text_symptoms_data.loc[
            text_symptoms_data["diagnosis"] == diagnosis, "patient_id"
        ] = ids.index

        patient_table.loc[ids.index, "text_diagnosis"] = diagnosis

    text_symptoms_data = text_symptoms_data[["symptoms", "patient_id"]]
    text_symptoms_data["symptom_id"] = text_symptoms_data.index

    return patient_table, text_symptoms_data

def _create_skin_cancer_table(
    patient_table: pd.DataFrame, cancer_data: pd.DataFrame, seed: int
) -> pd.DataFrame:
    """
    Prepares a skin cancer table with patients and their mole images from Kaggle.

    Returns:
        DataFrame with patient data.
    """

    cancer_data["patient_id"] = None
    
    corespondance_list = [
        "05_degenerative_infectious_diseases", 
        "01_inflammatory_processes", 
        "06_encapsulated_lesions"
        "07_mediastinal_changes", 
        "08_chest_changes", 
        "drug reaction", "fungal infection", "impetigo", "chicken pox",
        "allergy", "acne", "diabetes"
        # "00_normal", "normal", 
    ]

    patient_table["skin_cancer_diagnosis"] = "none"

    condition = (
        patient_table["audio_diagnosis"].isin(["none", "normal"])   
        & patient_table["x_ray_diagnosis"].isin(corespondance_list + ["none", "00_normal"])
        & patient_table["text_diagnosis"].isin(corespondance_list + ["none"])
        & (patient_table["skin_cancer_diagnosis"] == "none")
    )

    sampled = patient_table.loc[condition, "patient_id"].sample(
        n=len(cancer_data), random_state=seed
    )
    cancer_data["patient_id"] = sampled.values
    patient_table.loc[sampled.index, "skin_cancer_diagnosis"] = cancer_data["diagnosis"].values

    cancer_data = cancer_data[["image_path", "patient_id"]]
    cancer_data["skin_image_id"] = cancer_data.index

    return patient_table, cancer_data


def scale_down_data(
    patient_table: pd.DataFrame,
    audio_table: pd.DataFrame,
    image_table: pd.DataFrame,
    text_table: pd.DataFrame,
    cancer_table: pd.DataFrame,
    scaling_factor: int,
    seed: int=42,
) -> tuple:
    """Scales down all tables to the necessary size."""
    none_add_modalities = (
        (patient_table["text_diagnosis"] == "none")
        & (patient_table["audio_diagnosis"] == "none")
        & (patient_table["x_ray_diagnosis"] == "none")
        & (patient_table["skin_cancer_diagnosis"] == "none")
    )
    num_none = sum(none_add_modalities)

    num_none_to_drop = (
        patient_table.shape[0] - scaling_factor
        if num_none >= (patient_table.shape[0] - scaling_factor)
        else num_none
    )
    drop_indices = (
        patient_table[none_add_modalities]
        .sample(n=num_none_to_drop, random_state=seed)
        .index
    )
    # patient_table = patient_table.drop(index=drop_indices)

    if patient_table.shape[0] > scaling_factor:
        patient_table = (
            patient_table.sample(
                n=scaling_factor,
                # weights="is_sick",
                random_state=seed,
            )
            .reset_index(drop=True)
            .copy()
        )
        audio_table = audio_table[
            audio_table["patient_id"].isin(patient_table["patient_id"].tolist())
        ].copy()
        image_table = image_table[
            image_table["patient_id"].isin(patient_table["patient_id"].tolist())
        ].copy()
        text_table = text_table[
            text_table["patient_id"].isin(patient_table["patient_id"].tolist())
        ].copy()

        cancer_table = cancer_table[
            cancer_table["patient_id"].isin(patient_table["patient_id"].tolist())
        ].copy()

    return patient_table, audio_table, image_table, text_table, cancer_table


def _prepare_data_from_scratch(args: argparse.Namespace) -> None:
    """Prepares the medical data from scratch by downloading datasets and creating tables."""
    if args.download_prepared_data:
        if not all(
            [
                os.path.exists(
                    Path(__file__).resolve().parents[4]
                    / "files"
                    / "medical"
                    / "data"
                    / f"{file_name}_data.csv"
                )
                for file_name in [
                    "patient",
                    "audio_lung",
                    "image_x_ray",
                    "text_symptoms",
                ]
            ]
        ):
            _download_from_drive(id="1v4--C7PE_SQDNZj6hZ8wNn4OvswIyu2s", file_name="medical_data.zip")
    else:
        _download_kaggle_datasets()

    # Read and prepare datasets
    lung_patient_data = _prepare_lung_patient_data(args.lung_patient, args.seed)
    lung_patient_audio_data = _prepare_lung_audio_data(args.lung_audio)
    lung_x_ray_data = _prepare_xray_data(args.x_ray)
    text_symptoms_data = _prepare_text_data(args.text_diagnosis)
    skin_image_data = _prepare_skin_image_data(args.skin_cancer)

    # Create patient table and audio table
    patient_table, audio_table = _create_patient_audio_tables(
        lung_patient_data, lung_patient_audio_data
    )

    # Create X-ray table
    patient_table, lung_x_ray_table = _create_xray_table(
        patient_table, lung_x_ray_data, args.seed
    )

    # Create texts table
    patient_table, text_symptoms_table = _create_text_symptoms_table(
        patient_table, text_symptoms_data, args.seed
    )

    patient_table, skin_image_table = _create_skin_cancer_table(
        patient_table, skin_image_data, args.seed
    )

    # Store labels in patient table
    patient_table["is_sick"] = ~(
        (patient_table["text_diagnosis"] == "none")
        & patient_table["audio_diagnosis"].isin(["normal", "none"])
        & patient_table["x_ray_diagnosis"].isin(["none", "00_normal"])
        & patient_table["skin_cancer_diagnosis"].isin(["benign", "none"])
    )

    # Check a folder for saving
    base_folder = Path(__file__).resolve().parents[4] / "files" / "medical" / "data"
    folder = base_folder / f"sf_{args.scaling_factor}"
    os.makedirs(folder, exist_ok=True)

    # Scale down tables
    if args.scaling_factor < 11112:
        patient_table_sf, audio_table_sf, lung_x_ray_table_sf, text_symptoms_table_sf, skin_image_table_sf = (
            scale_down_data(
                patient_table,
                audio_table,
                lung_x_ray_table,
                text_symptoms_table,
                skin_image_table,
                scaling_factor=args.scaling_factor,
            )
        )

        # Save patient table with labels
        patient_table_sf.to_csv(f"{folder}/patient_data_with_labels.csv", index=False)
        patient_table_sf.drop(
            columns=["audio_diagnosis", "x_ray_diagnosis", "text_diagnosis", "skin_cancer_diagnosis", "is_sick"],
            inplace=True,
        )

        # Save tables to CSV files
        patient_table_sf.to_csv(f"{folder}/patient_data.csv", index=False)
        audio_table_sf.to_csv(f"{folder}/audio_lung_data.csv", index=False)
        lung_x_ray_table_sf.to_csv(f"{folder}/image_x_ray_data.csv", index=False)
        text_symptoms_table_sf.to_csv(f"{folder}/text_symptoms_data.csv", index=False)
        skin_image_table_sf.to_csv(f"{folder}/image_skin_data.csv", index=False)

    patient_table, audio_table, lung_x_ray_table, text_symptoms_table, skin_image_table = (
        _shuffle_tables(patient_table),
        _shuffle_tables(audio_table),
        _shuffle_tables(lung_x_ray_table),
        _shuffle_tables(text_symptoms_table),
        _shuffle_tables(skin_image_table),
    )

    # Save patient table with labels
    patient_table.to_csv(f"{folder}/patient_data_with_labels.csv", index=False)
    patient_table.drop(
        columns=["audio_diagnosis", "x_ray_diagnosis", "text_diagnosis", "skin_cancer_diagnosis", "is_sick"],
        inplace=True,
    )

    # Save tables to CSV files
    patient_table.to_csv(f"{folder}/patient_data.csv", index=False)
    audio_table.to_csv(f"{folder}/audio_lung_data.csv", index=False)
    lung_x_ray_table.to_csv(f"{folder}/image_x_ray_data.csv", index=False)
    text_symptoms_table.to_csv(f"{folder}/text_symptoms_data.csv", index=False)
    skin_image_table.to_csv(f"{folder}/image_skin_data.csv", index=False)


def prepare_data(scaling_factor: int = 11112) -> None:
    if 1 > scaling_factor or scaling_factor > 11112:
        raise "Scaling_factor should be between 1 and 11112. scaling_factor is number of rows in the dataset."

    csv_files_exists = all(
        [
            os.path.exists(
                Path(__file__).resolve().parents[4]
                / "files"
                / "medical"
                / "data"
                / f"{file_name}_data.csv"
            )
            for file_name in [
                "patient",
                "audio_lung",
                "image_x_ray",
                "text_symptoms",
                "image_skin",
            ]
        ]
    )

    raw_data_exists = os.path.exists(
        Path(__file__).resolve().parents[4]
        / "files"
        / "medical"
        / "data"
        / f"raw_data"
    )
    
    if csv_files_exists and raw_data_exists and scaling_factor == 11112:
        print("Data already exists, skipping preparation.")
        return

    if csv_files_exists and not raw_data_exists:
        _download_from_drive(id="1P4V_RWWDMxz4X-oG65Ph5-K2gmNGFpP-", file_name="raw_data.zip")

    if not csv_files_exists:
        _download_from_drive(id="1v4--C7PE_SQDNZj6hZ8wNn4OvswIyu2s", file_name="medical_data.zip")

    folder = Path(__file__).resolve().parents[4] / "files" / "medical" / "data"

    patient_table = pd.read_csv(join(folder, "patient_data_with_labels.csv"))
    audio_table = pd.read_csv(join(folder, "audio_lung_data.csv"))
    lung_x_ray_table = pd.read_csv(join(folder, "image_x_ray_data.csv"))
    text_symptoms_table = pd.read_csv(join(folder, "text_symptoms_data.csv"))
    skin_image_table = pd.read_csv(join(folder, "image_skin_data.csv"))

    patient_table, audio_table, lung_x_ray_table, text_symptoms_table, skin_image_table = (
        _shuffle_tables(patient_table),
        _shuffle_tables(audio_table),
        _shuffle_tables(lung_x_ray_table),
        _shuffle_tables(text_symptoms_table),
        _shuffle_tables(skin_image_table),
    )

    # Scale down tables
    if scaling_factor < 11112:
        patient_table_sf, audio_table_sf, lung_x_ray_table_sf, text_symptoms_table_sf, skin_image_table_sf = (
            scale_down_data(
                patient_table,
                audio_table,
                lung_x_ray_table,
                text_symptoms_table,
                skin_image_table,
                scaling_factor=scaling_factor,
            )
        )

        # Save patient table with labels
        patient_table_sf.to_csv(f"{folder}/patient_data_with_labels_{scaling_factor}.csv", index=False)
        patient_table_sf.drop(
            columns=["audio_diagnosis", "x_ray_diagnosis", "text_diagnosis", "skin_cancer_diagnosis", "is_sick"],
            inplace=True,
        )

        # Save tables to CSV files
        patient_table_sf.to_csv(f"{folder}/patient_data_{scaling_factor}.csv", index=False)
        audio_table_sf.to_csv(f"{folder}/audio_lung_data_{scaling_factor}.csv", index=False)
        lung_x_ray_table_sf.to_csv(f"{folder}/image_x_ray_data_{scaling_factor}.csv", index=False)
        text_symptoms_table_sf.to_csv(f"{folder}/text_symptoms_data_{scaling_factor}.csv", index=False)
        skin_image_table_sf.to_csv(f"{folder}/image_skin_data_{scaling_factor}.csv", index=False)

    # Save patient table with labels
    patient_table.to_csv(f"{folder}/patient_data_with_labels.csv", index=False)
    patient_table.drop(
        columns=["audio_diagnosis", "x_ray_diagnosis", "text_diagnosis", "skin_cancer_diagnosis", "is_sick"],
        inplace=True,
    )

    # Save tables to CSV files
    patient_table.to_csv(f"{folder}/patient_data.csv", index=False)
    audio_table.to_csv(f"{folder}/audio_lung_data.csv", index=False)
    lung_x_ray_table.to_csv(f"{folder}/image_x_ray_data.csv", index=False)
    text_symptoms_table.to_csv(f"{folder}/text_symptoms_data.csv", index=False)
    skin_image_table.to_csv(f"{folder}/image_skin_data.csv", index=False)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--download_prepared_data",
        type=int,
        nargs="?",
        default=1,
        help="1 to download prepared image and audio data from Google Drive, 0 to download/reuse existing Kaggle data and prepare from scratch.",
    )

    parser.add_argument(
        "--scaling_factor",
        type=int,
        nargs="?",
        default=11112,
        help="The number of rows in the patient table. Default value is 11112",
    )

    if parser.parse_args().download_prepared_data == 1 and all(
        [
            os.path.exists(
                Path(__file__).resolve().parents[4]
                / "files"
                / "medical"
                / "data"
                / f"{file_name}_data.csv"
            )
            for file_name in ["patient", "audio_lung", "image_x_ray", "text_symptoms", "image_skin"]
        ]
    ):
        _download_from_drive(id="1P4V_RWWDMxz4X-oG65Ph5-K2gmNGFpP-", file_name="raw_data.zip")
        
    else:
        # Use absolute paths for default arguments
        base_path = Path(__file__).resolve().parents[4]
        source_data = base_path / "files" / "medical" / "source_data" / "raw_data"

        parser.add_argument(
            "--lung_audio",
            type=str,
            nargs="?",
            default=str(source_data / "lung-dataset"),
            help="Path to the downloaded Kaggle lung audio dataset.",
        )

        parser.add_argument(
            "--lung_patient",
            type=str,
            nargs="?",
            default=str(source_data / "lungcanc2024"),
            help="Path to the downloaded Kaggle lung audio dataset.",
        )

        parser.add_argument(
            "--x_ray",
            type=str,
            nargs="?",
            default=str(source_data / "x-ray"),
            help="Path to the downloaded Kaggle lung X-ray dataset.",
        )

        parser.add_argument(
            "--text_diagnosis",
            type=str,
            nargs="?",
            default=str(source_data / "diagnosis"),
            help="Path to the downloaded Kaggle symptoms dataset.",
        )

        parser.add_argument(
            "--skin_cancer",
            type=str,
            nargs="?",
            default=str(source_data / "skin_cancer" / "archive" / "data"),
            help="Path to the downloaded Kaggle skin cancer dataset.",
        )

        parser.add_argument(
            "--seed", type=int, nargs="?", default=42, help="Random seed."
        )

        args = parser.parse_args()
    
        if 1 > args.scaling_factor or args.scaling_factor > 11112:
            raise "Scaling_factor should be between 1 and 11112. scaling_factor is number of rows in the dataset."

        # Prepare data from scratch
        _prepare_data_from_scratch(args)

if __name__ == "__main__":
    main()
