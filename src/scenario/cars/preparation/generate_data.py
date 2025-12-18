"""
Created on Dec 3, 2025

@author: OlgaOvcharenko

Creates test database from the following Kaggle datasets:
- https://www.kaggle.com/datasets/hendrichscullen/vehide-dataset-automatic-vehicle-damage-detection
- https://www.kaggle.com/datasets/jutrera/stanford-car-dataset-by-classes-folder 
- https://www.kaggle.com/datasets/malakragaie/car-diagnostics-dataset 
- https://www.kaggle.com/datasets/alshival/nhtsa-complaints?select=complaints.csv
"""

import argparse
from calendar import c
from genericpath import isfile
import glob
import json
import numpy as np
import pandas as pd
import random
import os
import shutil
from pathlib import Path
from os import listdir
from os.path import isdir, join


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
        # raw_data.zip contains raw source data, goes to files/medical/raw_data/
        if file_name == "cars_data.zip":
            folder = str(base_path / "files" / "cars")
        elif file_name == "nhtsa-dataset.zip":
            folder = str(base_path / "files" / "cars" / "data" / "raw_data" / "nhtsa-dataset")
        elif file_name == "full_data.zip":
            folder = str(base_path / "files" / "cars" / "data" / "full_data")
        elif file_name == "all_car_images.zip":
            folder = str(base_path / "files" / "cars" / "data" / "all_car_images")
        elif file_name == "all_car_audio.zip":
            folder = str(base_path / "files" / "cars" / "data" / "all_car_audio")
        else:
            folder = str(base_path / "files" / "cars" / "raw_data")
    
    # Check if data is already extracted
    raw_data_dir = os.path.join(base_path, "files", "cars", "data", "raw_data")
    # Check for key subdirectories that should exist after extraction
    expected_dirs = [
        os.path.join(raw_data_dir, "nhtsa-dataset"),
        os.path.join(raw_data_dir, "vehicle-damage-detection"),
        os.path.join(raw_data_dir, "stanford-cars"),
        os.path.join(raw_data_dir, "car-diagnostics"),
        os.path.join(base_path, "files", "cars", "data", "all_car_images"),
        os.path.join(base_path, "files", "cars", "data", "all_car_audio"),
        os.path.join(base_path, "files", "cars", "data", "full_data"),
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
        os.system(f"gdown --id {id} -O {zip_path}")
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
    """Downloads the required Kaggle datasets."""
    # Use absolute paths
    base_path = Path(__file__).resolve().parents[4]
    raw_data_path = base_path / "files" / "cars" / "data" / "raw_data"

    if not os.path.exists(raw_data_path):
        os.makedirs(raw_data_path, exist_ok=True)

    # Download vehicle damage detection dataset
    damage_path = raw_data_path / "vehicle-damage-detection"
    if not os.path.exists(damage_path):
        print("Downloading vehicle damage detection dataset...")
        os.system(
            f"curl -L -o {raw_data_path}/vehicle-damage-detection.zip https://www.kaggle.com/api/v1/datasets/download/hendrichscullen/vehide-dataset-automatic-vehicle-damage-detection"
        )
        os.system(
            f"unzip -o {raw_data_path}/vehicle-damage-detection.zip -d {damage_path}"
        )
        os.system(f"rm {raw_data_path}/vehicle-damage-detection.zip")

    # Download Stanford car dataset
    stanford_cars_path = raw_data_path / "stanford-cars"
    if not os.path.exists(stanford_cars_path):
        print("Downloading Stanford car dataset...")
        os.system(
            f"curl -L -o {raw_data_path}/stanford-cars.zip https://www.kaggle.com/api/v1/datasets/download/jutrera/stanford-car-dataset-by-classes-folder"
        )
        os.system(
            f"unzip -o {raw_data_path}/stanford-cars.zip -d {stanford_cars_path}"
        )
        os.system(f"rm {raw_data_path}/stanford-cars.zip")

    # Download car diagnostics dataset
    diagnostics_path = raw_data_path / "car-diagnostics"
    if not os.path.exists(diagnostics_path):
        print("Downloading car diagnostics dataset...")
        os.system(
            f"curl -L -o {raw_data_path}/car-diagnostics.zip https://www.kaggle.com/api/v1/datasets/download/malakragaie/car-diagnostics-dataset"
        )
        os.system(
            f"unzip -o {raw_data_path}/car-diagnostics.zip -d {diagnostics_path}"
        )
        os.system(f"rm {raw_data_path}/car-diagnostics.zip")

    # Download NHTSA complaints dataset
    nhtsa_path = raw_data_path / "nhtsa-dataset"
    if not os.path.exists(nhtsa_path):
        print("Downloading NHTSA complaints dataset...")
        _download_from_drive(id="1ER5pooCIi2q6ZTYUrJw_ha_X3byNQB9M/", file_name="nhtsa-dataset.zip")


def _generate_synthetic_car_data(num_cars: int, seed: int = 42) -> pd.DataFrame:
    """
    Generates synthetic car data with various attributes.
    Only includes attributes that cannot be determined from images.
    
    Args:
        num_cars: Number of cars to generate
        seed: Random seed
        
    Returns:
        DataFrame with car attributes
    """
    np.random.seed(seed)
    random.seed(seed)
    
    fuel_types = ['Gasoline', 'Diesel', 'Hybrid', 'Electric', 'Plug-in Hybrid']
    transmission_types = ['Automatic', 'Manual', 'CVT']
    
    countries = ['USA', 'Canada', 'Mexico', 'Germany', 'Japan', 'UK', 'France', 
                 'Italy', 'South Korea', 'China', 'Australia', 'Brazil', 'India',
                 'Spain', 'Netherlands', 'Belgium', 'Switzerland', 'Austria', 'Sweden',
                 'Norway', 'Denmark', 'Finland', 'Poland', 'Czech Republic', 'Portugal',
                 'Greece', 'Turkey', 'Ukraine', 'Argentina', 'Chile', 'Colombia', 'Peru',
                 'Venezuela', 'New Zealand', 'South Africa', 'Egypt', 'Saudi Arabia',
                 'UAE', 'Thailand', 'Malaysia', 'Singapore', 'Indonesia', 'Philippines',
                 'Vietnam', 'Taiwan', 'Hong Kong', 'Israel', 'Ireland', 'Romania', 'Bulgaria',
                 'Hungary', 'Bangladesh', 'Pakistan', 'Sri Lanka']
    
    # Generate number plate formats (varies by country)
    plate_formats = {
        'USA': lambda: f"{random.choice(['A', 'B', 'C', 'D', 'E', 'F'])}{random.randint(100, 999)}{random.choice(['A', 'B', 'C', 'D'])}",
        'Canada': lambda: f"{random.choice(['A', 'B', 'C'])}{random.randint(1000, 9999)}{random.choice(['A', 'B'])}",
        'Mexico': lambda: f"{random.choice(['A', 'B', 'C'])}{random.randint(100, 999)}{random.choice(['A', 'B', 'C'])}",
        'Germany': lambda: f"{random.choice(['B', 'M', 'H', 'K'])}{random.choice(['A', 'B', 'C'])}{random.randint(100, 9999)}",
        'Japan': lambda: f"{random.choice(['あ', 'い', 'う'])}{random.randint(10, 99)}{random.choice(['A', 'B', 'C'])}{random.randint(1000, 9999)}",
        'UK': lambda: f"{random.choice(['AB', 'CD', 'EF', 'GH'])}{random.randint(10, 99)}{random.choice(['A', 'B', 'C'])}{random.randint(100, 999)}",
        'France': lambda: f"{random.randint(100, 999)}{random.choice(['AB', 'CD', 'EF'])}{random.randint(10, 99)}",
        'Italy': lambda: f"{random.choice(['AB', 'CD', 'EF'])}{random.randint(100, 999)}{random.choice(['A', 'B', 'C'])}",
        'South Korea': lambda: f"{random.choice(['가', '나', '다'])}{random.randint(10, 99)}{random.choice(['A', 'B', 'C'])}{random.randint(1000, 9999)}",
        'China': lambda: f"{random.choice(['京', '沪', '粤'])}{random.choice(['A', 'B', 'C', 'D', 'E'])}{random.randint(1000, 9999)}",
        'Australia': lambda: f"{random.choice(['ABC', 'DEF', 'GHI'])}{random.randint(100, 999)}",
        'Brazil': lambda: f"{random.choice(['ABC'])}{random.randint(1000, 9999)}{random.choice(['A', 'B', 'C'])}",
        'India': lambda: f"{random.choice(['DL', 'MH', 'KA', 'TN'])}{random.randint(10, 99)}{random.choice(['A', 'B', 'C'])}{random.randint(1000, 9999)}",
        'Spain': lambda: f"{random.randint(1000, 9999)}{random.choice(['ABC', 'DEF', 'GHI'])}",
        'Netherlands': lambda: f"{random.randint(10, 99)}-{random.choice(['ABC', 'DEF', 'GHI'])}-{random.randint(1, 9)}",
        'Belgium': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(100, 999)}",
        'Switzerland': lambda: f"{random.choice(['AB', 'CD', 'EF'])} {random.randint(10000, 99999)}",
        'Austria': lambda: f"{random.choice(['A', 'B', 'C', 'D', 'E'])} {random.randint(10000, 99999)} {random.choice(['AB', 'CD'])}",
        'Sweden': lambda: f"{random.choice(['ABC', 'DEF', 'GHI'])} {random.randint(100, 999)}",
        'Norway': lambda: f"{random.choice(['AB', 'CD', 'EF'])} {random.randint(10000, 99999)}",
        'Denmark': lambda: f"{random.choice(['AB', 'CD', 'EF'])} {random.randint(10, 99)} {random.randint(100, 999)}",
        'Finland': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(100, 999)}",
        'Poland': lambda: f"{random.choice(['ABC', 'DEF', 'GHI'])} {random.randint(10000, 99999)}",
        'Czech Republic': lambda: f"{random.randint(1, 9)}{random.choice(['A', 'B', 'C'])}{random.randint(1, 9)} {random.randint(1000, 9999)}",
        'Portugal': lambda: f"{random.randint(10, 99)}-{random.choice(['AB', 'CD', 'EF'])}-{random.randint(10, 99)}",
        'Greece': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(1000, 9999)}",
        'Turkey': lambda: f"{random.randint(10, 99)} {random.choice(['ABC', 'DEF'])} {random.randint(100, 999)}",
        'Ukraine': lambda: f"{random.choice(['AB', 'CD', 'EF'])} {random.randint(1000, 9999)} {random.choice(['AB', 'CD'])}",
        'Argentina': lambda: f"{random.choice(['ABC', 'DEF'])} {random.randint(100, 999)}",
        'Chile': lambda: f"{random.choice(['ABCD', 'EFGH'])}-{random.randint(10, 99)}",
        'Colombia': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(100, 999)}",
        'Peru': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(1000, 9999)}",
        'Venezuela': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(100, 999)}{random.choice(['AB', 'CD'])}",
        'New Zealand': lambda: f"{random.choice(['ABC', 'DEF', 'GHI'])}{random.randint(100, 999)}",
        'South Africa': lambda: f"{random.choice(['ABC', 'DEF'])} {random.randint(100, 999)} {random.choice(['GP', 'WC', 'KZN'])}",
        'Egypt': lambda: f"{random.randint(10000, 99999)}",
        'Saudi Arabia': lambda: f"{random.randint(1000, 9999)}-{random.randint(10, 99)}",
        'UAE': lambda: f"{random.randint(10000, 99999)}",
        'Thailand': lambda: f"{random.choice(['ก', 'ข', 'ค'])}{random.choice(['ก', 'ข'])} {random.randint(1000, 9999)}",
        'Malaysia': lambda: f"{random.choice(['ABC', 'DEF'])} {random.randint(1000, 9999)}",
        'Singapore': lambda: f"{random.choice(['ABC', 'DEF', 'GHI'])}{random.randint(1000, 9999)}{random.choice(['A', 'B', 'C'])}",
        'Indonesia': lambda: f"{random.choice(['A', 'B', 'C', 'D'])} {random.randint(1000, 9999)} {random.choice(['ABC', 'DEF'])}",
        'Philippines': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(1000, 9999)}",
        'Vietnam': lambda: f"{random.randint(10, 99)}{random.choice(['A', 'B', 'C'])}-{random.randint(10000, 99999)}",
        'Taiwan': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(1000, 9999)}",
        'Hong Kong': lambda: f"{random.choice(['AB', 'CD', 'EF'])}{random.randint(1000, 9999)}",
        'Israel': lambda: f"{random.randint(10, 99)}-{random.randint(100, 999)}-{random.randint(10, 99)}",
        'Ireland': lambda: f"{random.randint(10, 99)}-{random.choice(['AB', 'CD', 'EF'])}-{random.randint(10000, 99999)}",
        'Romania': lambda: f"{random.choice(['AB', 'CD', 'EF'])}-{random.randint(10, 99)}-{random.choice(['ABC', 'DEF'])}",
        'Bulgaria': lambda: f"{random.choice(['AB', 'CD', 'EF'])} {random.randint(1000, 9999)} {random.choice(['AB', 'CD'])}",
        'Hungary': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(100, 999)}",
        'Bangladesh': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
        'Pakistan': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(1000, 9999)}",
        'Sri Lanka': lambda: f"{random.choice(['ABC', 'DEF'])}-{random.randint(1000, 9999)}",
    }
    
    cars = []
    for i in range(num_cars):
        year = random.randint(2000, 2025)
        mileage = random.randint(0, 200000)
        fuel_type = random.choice(fuel_types)
        transmission = random.choice(transmission_types)
        country = random.choice(countries)
        
        # Generate VIN (17 characters, alphanumeric)
        vin_chars = 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789'
        vin = ''.join(random.choice(vin_chars) for _ in range(17))
        
        # Generate registration date (between year of manufacture and current date)
        registration_year = random.randint(year, 2025)
        registration_month = random.randint(1, 12)
        # Handle different month lengths properly
        days_in_month = [31, 29 if registration_year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        max_day = days_in_month[registration_month - 1]
        registration_day = random.randint(1, max_day)
        registration_date = f"{registration_year}-{registration_month:02d}-{registration_day:02d}"
        
        # Generate number plate based on country
        if country in plate_formats:
            number_plate = plate_formats[country]()
        else:
            # Generic format for other countries
            number_plate = f"{random.choice(['A', 'B', 'C'])}{random.randint(1000, 9999)}{random.choice(['A', 'B', 'C'])}"
        # Generate number of previous owners
        # Logic: newer cars with low mileage are more likely to have 0-1 owners
        # Older cars or high mileage cars are more likely to have multiple owners
        car_age = 2025 - year
        age_factor = min(car_age / 10.0, 1.0)  # Normalize to 0-1, max at 10 years
        mileage_factor = min(mileage / 200000.0, 1.0)  # Normalize to 0-1, max at 200k miles
        
        # Base probability distribution for number of owners
        # Weighted towards fewer owners for newer/low-mileage cars
        combined_factor = (age_factor + mileage_factor) / 2.0
        
        if combined_factor < 0.2:  # Very new/low mileage
            # Mostly 0 owners (new from dealer), some 1 owner
            num_owners = random.choices([0, 1], weights=[70, 30])[0]
        elif combined_factor < 0.4:  # Relatively new
            # Mostly 0-1 owners
            num_owners = random.choices([0, 1, 2], weights=[40, 50, 10])[0]
        elif combined_factor < 0.6:  # Moderate age/mileage
            # Mostly 1-2 owners
            num_owners = random.choices([0, 1, 2, 3], weights=[10, 50, 30, 10])[0]
        elif combined_factor < 0.8:  # Older/higher mileage
            # Mostly 2-3 owners
            num_owners = random.choices([1, 2, 3, 4], weights=[20, 40, 30, 10])[0]
        else:  # Very old/high mileage
            # 2-5 owners, occasionally more
            num_owners = random.choices([2, 3, 4, 5, 6], weights=[20, 30, 25, 15, 10])[0]
        
        cars.append({
            'year': year,
            'mileage': mileage,
            'fuel_type': fuel_type,
            'transmission': transmission,
            'vin': vin,
            'registration_date': registration_date,
            'country': country,
            'number_plate': number_plate,
            'previous_owners': num_owners
        })
    
    return pd.DataFrame(cars)


def _prepare_car_images_damage(data_path: str) -> pd.DataFrame:
    """
    Prepares car damage images from the vehicle damage detection dataset.
    
    Args:
        data_path: Path to the damage detection dataset
        
    Returns:
        DataFrame with damage images and labels
    """
    # Load JSON annotation files
    train_json_path = os.path.join(data_path, "0Train_via_annos.json")
    val_json_path = os.path.join(data_path, "0Val_via_annos.json")

    class_translation = {
        'mat_bo_phan': 'lost_parts',
        'rach': 'torn',
        'mop_lom': 'dented',
        'tray_son': 'paint_scratches',
        'thung': 'puncture',
        'vo_kinh': 'broken_glass',
        'be_den': 'broken_lamp'
    }
    
    # Read JSON files 
    with open(train_json_path, 'r') as f:
        train_annos = json.load(f)
    with open(val_json_path, 'r') as f:
        val_annos = json.load(f)

    def get_images_and_classes(annos):
        image_classes_dict = {}
        for image_name, image_data in annos.items():
            classes_list = []
            if "regions" in image_data:
                for region in image_data["regions"]:
                    if "class" in region:
                        classes_list.append(class_translation[region["class"]])
            image_classes_dict[image_name] = ';'.join(list(set(classes_list)))
        return pd.DataFrame([
            {'filename': image_name, 'damage_status': classes_list}
            for image_name, classes_list in image_classes_dict.items()
        ])
    
    train_df = get_images_and_classes(train_annos)
    val_df = get_images_and_classes(val_annos)

    # Create consolidated image directory
    base_path = Path(__file__).resolve().parents[4]
    new_folder_path = str(base_path / 'files' / 'cars' / 'data' / 'all_car_images')
    os.makedirs(new_folder_path, exist_ok=True)
    
    # Get current working directory to make paths relative
    cwd = os.getcwd()
    
    train_df["image_path"] = ""
    val_df["image_path"] = ""

    def copy_image(image_path):
        src_image = image_path
        filename = os.path.basename(image_path)

        # Generate unique random string (8 characters: 4 random letters + 4 random digits)
        unique_id = ''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ', k=4)) + ''.join(random.choices('0123456789', k=4))
        dst_image_abs = os.path.join(new_folder_path, f"{i}_{unique_id}_{filename}")

        if not os.path.exists(dst_image_abs):
            shutil.copy(src_image, dst_image_abs)
        
        # Convert to relative path from current working directory
        dst_image_rel = os.path.relpath(dst_image_abs, cwd)
        return dst_image_rel

    for i, image_path in zip(train_df.index, train_df["filename"]):
        dst_image = copy_image(os.path.join(data_path, "image", "image", image_path))
        train_df.loc[i, "image_path"] = dst_image 

    for i, image_path in zip(val_df.index, val_df["filename"]):
        dst_image = copy_image(os.path.join(data_path, "validation", "validation", image_path))
        val_df.loc[i, "image_path"] = dst_image

    return pd.concat([train_df, val_df])[["image_path", "damage_status"]]


def _prepare_car_images_stanford(data_path: str) -> pd.DataFrame:
    """
    Prepares car images from the Stanford car dataset.
    
    Args:
        data_path: Path to the Stanford car dataset
        
    Returns:
        DataFrame with car images and make/model information
    """
    car_images = []
    
    # Look for images in common directory structures
    possible_paths = [
        f"{data_path}/car_data/car_data/train/**/*",
        f"{data_path}/car_data/car_data/test/**/*",
    ]
    
    for pattern in possible_paths:
        for img_path in glob.glob(pattern, recursive=True):
            if isfile(img_path) and img_path.endswith((".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG")):
                # Extract make/model from path
                car_images.append({
                    'image_path_orig': img_path
                })

    if not car_images:
        raise Exception(f"Warning: No car images found in {data_path}")
    

    car_df = pd.DataFrame(car_images)
    
    # Create consolidated image directory
    base_path = Path(__file__).resolve().parents[4]
    new_folder_path = str(base_path / 'files' / 'cars' / 'data' / 'all_car_images')
    os.makedirs(new_folder_path, exist_ok=True)
    
    # Get current working directory to make paths relative
    cwd = os.getcwd()
    
    car_df["image_path"] = ""
    # Use enumerate to generate unique sequential IDs
    for i, image_path in zip(car_df.index, car_df["image_path_orig"]):
        src_image = image_path
        filename = os.path.basename(image_path)

        # Generate unique random string (8 characters: 4 random letters + 4 random digits)
        unique_id = ''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ', k=6)) + ''.join(random.choices('0123456789', k=4))
        dst_image_abs = os.path.join(new_folder_path, f"{i}_{unique_id}_{filename}")
        
        if not os.path.exists(dst_image_abs):
            shutil.copy(src_image, dst_image_abs)
        
        # Convert to relative path from current working directory
        dst_image_rel = os.path.relpath(dst_image_abs, cwd)
        car_df.loc[i, "image_path"] = dst_image_rel
    
    car_df["damage_status"] = "no_damage"
    
    return car_df[["image_path", "damage_status"]]


def _prepare_car_audio_data(data_path: str) -> pd.DataFrame:
    """
    Prepares car diagnostic audio data with generic and detailed problem categories.
    
    Args:
        data_path: Path to the car diagnostics dataset
        
    Returns:
        DataFrame with columns: audio_path, generic_problem, detailed_problem
    """
    audio_files = []
    
    # Find the "car diagnostics dataset" folder
    dataset_folder = os.path.join(data_path, "car diagnostics dataset")
    
    # Walk through the directory structure
    # Structure: dataset_folder/generic_problem/detailed_problem/audio_files
    # Or: dataset_folder/generic_problem/combined/subfolder/audio_files
    
    for root, dirs, files in os.walk(dataset_folder):
        # Skip if no audio files in this directory
        audio_in_dir = [f for f in files if f.endswith((".wav", ".mp3", ".flac", ".m4a", ".WAV", ".MP3"))]
        if not audio_in_dir:
            continue
        
        # Get relative path from dataset folder
        rel_path = os.path.relpath(root, dataset_folder)
        path_parts = rel_path.split(os.sep)
        
        # Extract generic_problem (first level folder)
        if len(path_parts) >= 1:
            generic_problem = path_parts[0]
        else:
            generic_problem = "unknown"
        
        # Extract detailed_problem
        if len(path_parts) >= 2:
            if path_parts[1] == "combined":
                # For combined folders, use the subfolder name
                if len(path_parts) >= 3:
                    detailed_problem = path_parts[2]
                else:
                    detailed_problem = "combined"
            else:
                detailed_problem = path_parts[1]
        else:
            detailed_problem = "unknown"
        
        # Process each audio file
        for audio_file in audio_in_dir:
            audio_path = os.path.join(root, audio_file)
            audio_files.append({
                'audio_path_orig': audio_path,
                'generic_problem': generic_problem,
                'detailed_problem': detailed_problem
            })
    
    audio_df = pd.DataFrame(audio_files)

    base_path = Path(__file__).resolve().parents[4]
    new_folder_path = str(base_path / 'files' / 'cars' / 'data' / 'all_car_audio')
    os.makedirs(new_folder_path, exist_ok=True)
    
    # Get current working directory to make paths relative
    cwd = os.getcwd()

    audio_df["audio_path"] = ""
    def copy_audio(audio_path):
        src_audio = audio_path
        filename = os.path.basename(audio_path)

        # Generate unique random string (8 characters: 4 random letters + 4 random digits)
        unique_id = ''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ', k=6)) + ''.join(random.choices('0123456789', k=4))
        dst_audio_abs = os.path.join(new_folder_path, f"{i}_{unique_id}_{filename}")

        if not os.path.exists(dst_audio_abs):
            shutil.copy(src_audio, dst_audio_abs)
        
        # Convert to relative path from current working directory
        dst_audio_rel = os.path.relpath(dst_audio_abs, cwd)
        return dst_audio_rel

    for i, audio_path in zip(audio_df.index, audio_df["audio_path_orig"]):
        dst_audio = copy_audio(os.path.join(data_path, "audio", "audio", audio_path))
        audio_df.loc[i, "audio_path"] = dst_audio
    return audio_df[["audio_path", "generic_problem", "detailed_problem"]]


def _prepare_complaints_text_data(data_path: str) -> pd.DataFrame:
    """
    Prepares NHTSA complaints text data with categorized issue types.
    
    Args:
        data_path: Path to the NHTSA complaints dataset
        
    Returns:
        DataFrame with complaint text data and categorized issues
    """
    # Look for complaints.csv file
    complaints_file = f"{data_path}/nhtsa_component_classification.csv"
    complaints_df = pd.read_csv(complaints_file)

    return complaints_df[["crash", "fire", "numberOfInjuries", "summary", "component_class"]]


def _create_meaningful_modality_links(
    car_data: pd.DataFrame,
    image_data: pd.DataFrame,
    audio_data: pd.DataFrame,
    complaints_data: pd.DataFrame,
    seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Creates meaningful links between cars and their modalities (images, audio, text).
    Links are based on issue types to create realistic associations.
    Returns tables in 3NF with proper foreign key relationships.
    
    Schema:
    - cars: car_id (PK), year, mileage, fuel_type, transmission, vin, registration_date, country, number_plate, previous_owners
    - images: image_id (PK), car_id (FK), image_path, damage_status
    - audio: audio_id (PK), car_id (FK), audio_path, generic_problem, detailed_problem
    - complaints: complaint_id (PK), car_id (FK), summary, component_class, crash, fire, numberOfInjuries
    
    Args:
        car_data: DataFrame with car data (columns: year, mileage, fuel_type, etc.)
        image_data: DataFrame with images (columns: image_path, damage_status)
        audio_data: DataFrame with audio data (columns: audio_path, generic_problem, detailed_problem)
        complaints_data: DataFrame with complaint data (columns: summary, component_class, crash, fire, numberOfInjuries)
        seed: Random seed
        
    Returns:
        Tuple of (car_table, image_table, audio_table, complaints_table) in 3NF
    """
    image_damages = ['lost_parts;dented;torn;paint_scratches',
       'lost_parts;torn;paint_scratches', 'lost_parts;torn',
       'torn;paint_scratches', 'broken_glass;lost_parts;dented;torn',
       'broken_glass;lost_parts;paint_scratches;torn',
       'lost_parts;puncture;paint_scratches;torn;broken_glass',
       'lost_parts;dented', 'torn', 'broken_glass;lost_parts',
       'lost_parts', 'broken_glass', 'puncture;paint_scratches',
       'dented;puncture;paint_scratches', 'broken_lamp',
       'paint_scratches;broken_lamp', 'puncture;broken_lamp',
       'broken_glass;dented;paint_scratches', 'broken_glass;torn',
       'broken_glass;dented', 'broken_glass;paint_scratches',
       'dented;puncture;paint_scratches;torn', 'puncture;torn',
       'dented;puncture', 'torn;puncture;paint_scratches',
       'lost_parts;paint_scratches', 'dented', 'torn;broken_lamp',
       'paint_scratches', 'dented;broken_lamp', 'dented;paint_scratches',
       'dented;torn;paint_scratches', 'dented;paint_scratches;torn',
       'dented;torn', 'paint_scratches;torn', 'puncture',
       'lost_parts;puncture;paint_scratches',
       'puncture;paint_scratches;torn', 'lost_parts;puncture',
       'lost_parts;dented;puncture;paint_scratches',
       'lost_parts;dented;paint_scratches;puncture',
       'lost_parts;paint_scratches;broken_lamp',
       'dented;torn;broken_lamp', 'dented;paint_scratches;broken_lamp',
       'lost_parts;dented;torn', 'lost_parts;dented;paint_scratches',
       'broken_glass;lost_parts;torn;paint_scratches',
       'lost_parts;paint_scratches;torn',
       'broken_glass;lost_parts;dented;broken_lamp',
       'dented;puncture;paint_scratches;broken_glass;broken_lamp',
       'broken_glass;dented;broken_lamp', 'broken_glass;dented;puncture',
       'dented;puncture;paint_scratches;torn;broken_lamp',
       'paint_scratches;puncture;torn',
       'lost_parts;puncture;torn;paint_scratches', 'dented;puncture;torn',
       'puncture;torn;paint_scratches',
       'broken_glass;lost_parts;paint_scratches',
       'lost_parts;broken_lamp', 'broken_glass;dented;torn;broken_lamp',
       'puncture;paint_scratches;broken_lamp',
       'puncture;paint_scratches;torn;broken_lamp',
       'lost_parts;dented;puncture;paint_scratches;torn;broken_lamp',
       'broken_glass;torn;paint_scratches',
       'broken_glass;lost_parts;torn',
       'broken_glass;paint_scratches;torn', 'paint_scratches;puncture',
       'dented;puncture;paint_scratches;broken_lamp',
       'dented;paint_scratches;puncture;torn',
       'torn;paint_scratches;broken_lamp',
       'paint_scratches;torn;broken_lamp', 'lost_parts;dented;puncture',
       'dented;torn;paint_scratches;broken_lamp',
       'dented;paint_scratches;torn;broken_lamp',
       'lost_parts;dented;puncture;paint_scratches;torn',
       'dented;paint_scratches;puncture',
       'puncture;dented;torn;paint_scratches',
       'dented;torn;puncture;paint_scratches',
       'broken_glass;lost_parts;dented', 'broken_glass;puncture',
       'lost_parts;dented;torn;paint_scratches;broken_lamp',
       'lost_parts;dented;paint_scratches;torn;broken_lamp',
       'broken_glass;puncture;paint_scratches',
       'puncture;torn;broken_lamp',
       'dented;puncture;torn;paint_scratches;broken_lamp',
       'broken_glass;dented;torn',
       'broken_glass;dented;torn;paint_scratches',
       'lost_parts;dented;puncture;torn;paint_scratches;broken_lamp',
       'lost_parts;dented;paint_scratches;broken_glass;broken_lamp',
       'lost_parts;dented;torn;paint_scratches;broken_glass',
       'lost_parts;dented;torn;broken_glass;broken_lamp',
       'broken_glass;lost_parts;dented;paint_scratches',
       'lost_parts;torn;paint_scratches;broken_lamp',
       'lost_parts;torn;broken_lamp',
       'lost_parts;dented;paint_scratches;broken_lamp',
       'lost_parts;dented;broken_lamp',
       'lost_parts;dented;puncture;torn;paint_scratches',
       'lost_parts;dented;paint_scratches;torn',
       'lost_parts;dented;torn;broken_lamp',
       'lost_parts;puncture;torn;broken_lamp', 'torn;puncture',
       'paint_scratches;puncture;torn;broken_lamp',
       'lost_parts;dented;paint_scratches;torn;broken_glass',
       'lost_parts;paint_scratches;puncture;torn',
       'lost_parts;paint_scratches;torn;broken_lamp',
       'lost_parts;dented;torn;puncture',
       'lost_parts;torn;puncture;paint_scratches',
       'lost_parts;puncture;torn',
       'lost_parts;puncture;paint_scratches;torn',
       'dented;puncture;paint_scratches;torn;broken_glass',
       'lost_parts;puncture;broken_lamp',
       'dented;paint_scratches;puncture;broken_lamp',
       'dented;puncture;broken_lamp',
       'paint_scratches;torn;puncture;broken_lamp',
       'dented;torn;paint_scratches;broken_glass;broken_lamp',
       'dented;puncture;torn;broken_lamp',
       'dented;paint_scratches;torn;broken_glass;broken_lamp',
       'lost_parts;puncture;paint_scratches;torn;broken_lamp',
       'dented;torn;puncture;broken_lamp',
       'lost_parts;dented;puncture;torn',
       'lost_parts;paint_scratches;puncture;broken_lamp',
       'lost_parts;dented;puncture;torn;broken_lamp',
       'lost_parts;torn;puncture;broken_lamp', 'dented;torn;puncture',
       'broken_glass;dented;paint_scratches;torn',
       'torn;puncture;broken_lamp',
       'lost_parts;dented;puncture;paint_scratches;torn;broken_glass',
       'puncture;torn;paint_scratches;broken_lamp',
       'lost_parts;paint_scratches;puncture',
       'dented;puncture;torn;broken_glass;broken_lamp',
       'broken_glass;broken_lamp',
       'lost_parts;dented;puncture;paint_scratches;broken_glass',
       'lost_parts;puncture;torn;paint_scratches;broken_lamp',
       'broken_glass;paint_scratches;puncture;torn',
       'broken_glass;torn;puncture;paint_scratches',
       'broken_glass;puncture;paint_scratches;torn',
       'broken_glass;torn;puncture;broken_lamp',
       'broken_glass;puncture;paint_scratches;broken_lamp',
       'broken_glass;paint_scratches;puncture',
       'broken_glass;dented;paint_scratches;broken_lamp',
       'broken_glass;torn;paint_scratches;broken_lamp',
       'dented;puncture;paint_scratches;torn;broken_glass;broken_lamp']
    np.random.seed(seed)
    random.seed(seed)
    
    # Prepare car table with primary key
    car_table = car_data.copy()
    car_table = car_table.reset_index(drop=True)
    car_table["car_id"] = car_table.index
    
    # Prepare audio table with foreign key (3NF)
    # Expected columns: audio_path, generic_problem, detailed_problem
    audio_table = audio_data.copy()
    audio_table = audio_table.reset_index(drop=True)
    audio_table["audio_id"] = audio_table.index
    audio_table["car_id"] = None  # Foreign key to cars table
    
    # Prepare complaints table with foreign key (3NF)
    # Expected columns: summary, component_class, crash, fire, numberOfInjuries
    complaints_table = complaints_data.copy()
    complaints_table = complaints_table.reset_index(drop=True)
    complaints_table["complaint_id"] = complaints_table.index
    complaints_table["car_id"] = None  # Foreign key to cars table
    
    # Prepare images table with foreign key (3NF)
    # Expected columns: image_path, damage_status
    image_table = image_data.copy()
    image_table = image_table.reset_index(drop=True)
    image_table["image_id"] = image_table.index
    image_table["car_id"] = None  # Foreign key to cars table
    
    # Define mappings between modalities based on actual data labels
    # Map audio problems to compatible image damage and complaint components
    audio_to_image_mapping = {
        # Startup state issues
        "startup state": {
            "normal_engine_startup": ["no_damage"],
            "bad_ignition": ["no_damage"] + image_damages,  # May or may not show damage
            "dead_battery": ["no_damage"]  # Usually no visible damage
        },
        # Idle state issues
        "idle state": {
            "normal_engine_idle": ["no_damage"] + image_damages,
            "no oil_serpentine belt": ["no_damage"] + image_damages,
            "power_steering": ["no_damage"] + image_damages,
            "serpentine_belt": ["no_damage"] + image_damages,
            "power steering combined_no oil": ["no_damage"] + image_damages,
            "power steering combined_serpentine belt": ["no_damage"] + image_damages,
            "power steering combined_no oil_serpentine belt": ["no_damage"] + image_damages
        },
        # Braking state issues
        "braking state": {
            "normal_brakes": ["no_damage"],
            "worn_out_brakes":["no_damage"] + image_damages # May show wear
        }
    }
    
    # Map audio problems to compatible complaint component classes
    audio_to_complaint_mapping = {
        "startup state": {
            "normal_engine_startup": ['AIR BAGS', 'BACK OVER PREVENTION', 'ELECTRICAL SYSTEM', 'EQUIPMENT', 
                'EXTERIOR LIGHTING', 'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
                'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
                'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
                'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION', 'TIRES',
                'VEHICLE SPEED CONTROL', 'VISIBILITY', 'VISIBILITY/WIPER',
                'WHEELS'],
            "bad_ignition": ["ENGINE", "ELECTRICAL SYSTEM", "FUEL SYSTEM"],
            "dead_battery": ["ELECTRICAL SYSTEM"]
        },
        "idle state": {
            "normal_engine_idle": ['AIR BAGS', 'BACK OVER PREVENTION', 'ELECTRICAL SYSTEM', 'ENGINE',
       'ENGINE AND ENGINE COOLING', 'EQUIPMENT', 'EXTERIOR LIGHTING',
       'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
       'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
       'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
       'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION', 'TIRES',
       'VEHICLE SPEED CONTROL', 'VISIBILITY', 'VISIBILITY/WIPER',
       'WHEELS'],
            "no oil_serpentine belt": ['ELECTRICAL SYSTEM', 'ENGINE',
       'ENGINE AND ENGINE COOLING', 'FUEL SYSTEM',
       'FUEL/PROPULSION SYSTEM', 'POWER TRAIN',
       'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION', 'TIRES'],
            "power_steering": ['AIR BAGS', 'BACK OVER PREVENTION', 'ELECTRICAL SYSTEM', 'ENGINE',
                'ENGINE AND ENGINE COOLING', 'EQUIPMENT', 'EXTERIOR LIGHTING',
                'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
                'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
                'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
                'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION', 'TIRES',
                'VEHICLE SPEED CONTROL', 'VISIBILITY', 'VISIBILITY/WIPER',
                'WHEELS'],
            "serpentine_belt": ['ELECTRICAL SYSTEM', 'ENGINE',
                'ENGINE AND ENGINE COOLING', 'EXTERIOR LIGHTING',
                'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
                'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
                'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
                'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION',
                'VEHICLE SPEED CONTROL'],
            "power steering combined_no oil": ['ELECTRICAL SYSTEM', 'ENGINE',
                'ENGINE AND ENGINE COOLING', 'EQUIPMENT', 'EXTERIOR LIGHTING',
                'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
                'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
                'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
                'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION',
                'VEHICLE SPEED CONTROL'],
            "power steering combined_serpentine belt": ['ELECTRICAL SYSTEM', 'ENGINE',
                'ENGINE AND ENGINE COOLING', 'EXTERIOR LIGHTING',
                'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
                'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
                'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
                'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION',
                'VEHICLE SPEED CONTROL'],
            "power steering combined_no oil_serpentine belt": ['ELECTRICAL SYSTEM', 'ENGINE',
                'ENGINE AND ENGINE COOLING', 'EXTERIOR LIGHTING',
                'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
                'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
                'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
                'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION',
                'VEHICLE SPEED CONTROL'],
        },
        "braking state": {
            "normal_brakes": ['AIR BAGS', 'BACK OVER PREVENTION', 'ELECTRICAL SYSTEM', 'ENGINE',
       'ENGINE AND ENGINE COOLING', 'EQUIPMENT', 'EXTERIOR LIGHTING',
       'FORWARD COLLISION AVOIDANCE', 'FUEL SYSTEM',
       'FUEL/PROPULSION SYSTEM', 'LANE DEPARTURE',
       'LATCHES/LOCKS/LINKAGES', 'POWER TRAIN', 'SEAT BELTS', 'SEATS',
       'SERVICE BRAKES', 'STEERING', 'STRUCTURE', 'SUSPENSION', 'TIRES',
       'VEHICLE SPEED CONTROL', 'VISIBILITY', 'VISIBILITY/WIPER',
       'WHEELS'],
            "worn_out_brakes": ["SERVICE BRAKES", 'STEERING', 'STRUCTURE', 'SUSPENSION', 'TIRES', 'VEHICLE SPEED CONTROL', 'VISIBILITY', 'VISIBILITY/WIPER', 'WHEELS']
        }
    }
    
    # Group audio by generic_problem and detailed_problem
    audio_by_problem = {}
    if len(audio_table) > 0:
        for (generic, detailed), group in audio_table.groupby(['generic_problem', 'detailed_problem']):
            key = (generic, detailed)
            audio_by_problem[key] = group[group["car_id"].isna()].copy()
    
    # Group images by damage_status
    images_by_status = {}
    if len(image_table) > 0:
        for status in image_table["damage_status"].unique():
            images_by_status[status] = image_table[(image_table["damage_status"] == status) & (image_table["car_id"].isna())].copy()
    
    # Group complaints by component_class
    complaints_by_component = {}
    if len(complaints_table) > 0:
        for component in complaints_table["component_class"].unique():
            complaints_by_component[component] = complaints_table[(complaints_table["component_class"] == component) & (complaints_table["car_id"].isna())].copy()
    
    # Strategy: Create different types of car-modality associations
    # 1. ALL audio files must be assigned to cars with 3 modalities (audio + image + text)
    # 2. Most remaining cars get 2 modalities (image + text, or just image, or just text)
    # 3. Leftover cars get 1 modality (image or text)
    # Note: No modality is used twice for the same car (enforced by assignment logic)
    
    num_cars = len(car_table)
    car_indices = list(car_table.index)
    random.shuffle(car_indices)
    
    idx = 0
    
    # 1. Assign ALL audio files to cars with 3 modalities (audio + image + text)
    # Collect all available audio entries
    all_audio_entries = []
    for audio_key, audio_group in audio_by_problem.items():
        for audio_idx in audio_group.index:
            all_audio_entries.append((audio_idx, audio_key))
    
    # Shuffle audio entries for random assignment
    random.shuffle(all_audio_entries)
    
    # Assign each audio file to a car with matching image and complaint
    for audio_idx, audio_key in all_audio_entries:
        if idx >= len(car_indices):
            break  # No more cars available
        
        car_id = car_indices[idx]
        idx += 1
        
        generic_problem, detailed_problem = audio_key
        
        # Assign the audio
        audio_table.loc[audio_idx, "car_id"] = car_id
        # Remove from available pool
        audio_by_problem[audio_key] = audio_by_problem[audio_key].drop(audio_idx)
        
        # Assign matching image based on audio problem
        # Handle combined cases and fallback to generic mapping
        if detailed_problem.startswith("power steering") or "combined" in detailed_problem.lower():
            # Combined issues - can have various damage states
            compatible_damage = ["no_damage", "damaged"]
        else:
            compatible_damage = audio_to_image_mapping.get(generic_problem, {}).get(detailed_problem, ["no_damage", "damaged"])
        damage_status = random.choice(compatible_damage)
        
        if damage_status in images_by_status and len(images_by_status[damage_status]) > 0:
            available_images = images_by_status[damage_status]
            if len(available_images) > 0:
                img_idx = available_images.index[0]
                image_table.loc[img_idx, "car_id"] = car_id
                # Remove from available pool
                images_by_status[damage_status] = images_by_status[damage_status].drop(img_idx)
        
        # Assign matching complaint based on audio problem
        # Handle combined cases
        if detailed_problem.startswith("power steering") or "combined" in detailed_problem.lower():
            compatible_components = ["ENGINE", "POWER TRAIN", "ELECTRICAL SYSTEM", "STEERING"]
        else:
            compatible_components = audio_to_complaint_mapping.get(generic_problem, {}).get(detailed_problem, ["UNKNOWN"])
        component_class = random.choice(compatible_components)
        
        if component_class in complaints_by_component and len(complaints_by_component[component_class]) > 0:
            available_complaints = complaints_by_component[component_class]
            if len(available_complaints) > 0:
                complaint_idx = available_complaints.index[0]
                complaints_table.loc[complaint_idx, "car_id"] = car_id
                # Remove from available pool
                complaints_by_component[component_class] = complaints_by_component[component_class].drop(complaint_idx)
    
    # 2. Assign remaining cars with 2 modalities (image + text) until resources run out
    # Keep assigning until we can't assign both image and text anymore
    while idx < len(car_indices):
        car_id = car_indices[idx]
        
        # Check if we can assign both image and text
        available_statuses = [s for s in images_by_status.keys() if len(images_by_status[s]) > 0]
        available_components = [c for c in complaints_by_component.keys() if len(complaints_by_component[c]) > 0]
        
        # If we can assign both, do it
        if available_statuses and available_components:
            idx += 1
            
            # Assign image
            damage_status = random.choice(available_statuses)
            available_images = images_by_status[damage_status]
            if len(available_images) > 0:
                img_idx = available_images.index[0]
                image_table.loc[img_idx, "car_id"] = car_id
                images_by_status[damage_status] = images_by_status[damage_status].drop(img_idx)
            
            # Assign text
            component_class = random.choice(available_components)
            available_complaints = complaints_by_component[component_class]
            if len(available_complaints) > 0:
                complaint_idx = available_complaints.index[0]
                complaints_table.loc[complaint_idx, "car_id"] = car_id
                complaints_by_component[component_class] = complaints_by_component[component_class].drop(complaint_idx)
        else:
            # Can't assign both, break and move to single modality assignment
            break
    
    # 3. Assign leftover cars with 1 modality (image or text)
    while idx < len(car_indices):
        car_id = car_indices[idx]
        idx += 1
        
        # Check what's available
        available_statuses = [s for s in images_by_status.keys() if len(images_by_status[s]) > 0]
        available_components = [c for c in complaints_by_component.keys() if len(complaints_by_component[c]) > 0]
        
        # Prefer image if available, otherwise text
        if available_statuses:
            damage_status = random.choice(available_statuses)
            available_images = images_by_status[damage_status]
            if len(available_images) > 0:
                img_idx = available_images.index[0]
                image_table.loc[img_idx, "car_id"] = car_id
                images_by_status[damage_status] = images_by_status[damage_status].drop(img_idx)
        elif available_components:
            component_class = random.choice(available_components)
            available_complaints = complaints_by_component[component_class]
            if len(available_complaints) > 0:
                complaint_idx = available_complaints.index[0]
                complaints_table.loc[complaint_idx, "car_id"] = car_id
                complaints_by_component[component_class] = complaints_by_component[component_class].drop(complaint_idx)
        else:
            # No more modalities available, stop
            break
    
    # Filter tables to only assigned entries (with foreign keys)
    audio_table = audio_table[audio_table["car_id"].notna()].copy()
    image_table = image_table[image_table["car_id"].notna()].copy()
    complaints_table = complaints_table[complaints_table["car_id"].notna()].copy()
    
    # Collect all car_ids that have at least one assigned modality
    cars_with_modalities = set()
    if len(audio_table) > 0:
        cars_with_modalities.update(audio_table["car_id"].unique())
    if len(image_table) > 0:
        cars_with_modalities.update(image_table["car_id"].unique())
    if len(complaints_table) > 0:
        cars_with_modalities.update(complaints_table["car_id"].unique())
    
    # Filter car_table to only include cars with at least one assigned modality
    car_table = car_table[car_table["car_id"].isin(cars_with_modalities)].copy()
    
    # Return in 3NF format with proper column names
    # cars: car_id (PK) + all car attributes
    # images: image_id (PK), car_id (FK), image_path, damage_status
    # audio: audio_id (PK), car_id (FK), audio_path, generic_problem, detailed_problem
    # complaints: complaint_id (PK), car_id (FK), summary, component_class, crash, fire, numberOfInjuries
    
    return car_table, image_table, audio_table, complaints_table


def _denormalize_data(
    car_table: pd.DataFrame,
    image_table: pd.DataFrame,
    audio_table: pd.DataFrame,
    complaints_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Denormalizes the normalized tables into a single table with all information.
    Creates a row for each unique combination of car + image + audio + complaint.
    If a car has multiple images, audio files, or complaints, multiple rows will be created.
    
    Args:
        car_table: DataFrame with car data (car_id as PK)
        image_table: DataFrame with image data (image_id, car_id, image_path, damage_status)
        audio_table: DataFrame with audio data (audio_id, car_id, audio_path, generic_problem, detailed_problem)
        complaints_table: DataFrame with complaint data (complaint_id, car_id, summary, component_class, crash, fire, numberOfInjuries)
        
    Returns:
        Single denormalized DataFrame with all car attributes and all modality information
    """
    # Start with car table
    denormalized = car_table.copy()
    
    # Merge with images (left join to keep all cars, even without images)
    if len(image_table) > 0:
        denormalized = denormalized.merge(
            image_table,
            on="car_id",
            how="left",
            suffixes=("", "_img")
        )
    else:
        # Add empty columns if no images
        denormalized["image_id"] = None
        denormalized["image_path"] = None
        denormalized["damage_status"] = None
    
    # Merge with audio (left join)
    if len(audio_table) > 0:
        denormalized = denormalized.merge(
            audio_table,
            on="car_id",
            how="left",
            suffixes=("", "_audio")
        )
    else:
        # Add empty columns if no audio
        denormalized["audio_id"] = None
        denormalized["audio_path"] = None
        denormalized["generic_problem"] = None
        denormalized["detailed_problem"] = None
    
    # Merge with complaints (left join)
    if len(complaints_table) > 0:
        denormalized = denormalized.merge(
            complaints_table,
            on="car_id",
            how="left",
            suffixes=("", "_complaint")
        )
    else:
        # Add empty columns if no complaints
        denormalized["complaint_id"] = None
        denormalized["summary"] = None
        denormalized["component_class"] = None
        denormalized["crash"] = None
        denormalized["fire"] = None
        denormalized["numberOfInjuries"] = None
    
    # Remove duplicate car_id column if it exists (from merges)
    if "car_id_img" in denormalized.columns:
        denormalized = denormalized.drop(columns=["car_id_img"])
    if "car_id_audio" in denormalized.columns:
        denormalized = denormalized.drop(columns=["car_id_audio"])
    if "car_id_complaint" in denormalized.columns:
        denormalized = denormalized.drop(columns=["car_id_complaint"])
    
    return denormalized


def _shuffle_tables(df: pd.DataFrame) -> pd.DataFrame:
    """Shuffles a DataFrame."""
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def scale_down_data(
    car_table: pd.DataFrame,
    image_table: pd.DataFrame,
    audio_table: pd.DataFrame,
    complaints_table: pd.DataFrame,
    scaling_factor: int,
    seed: int = 42,
) -> tuple:
    """
    Scales down all tables to the necessary size while maintaining the ratios of 
    cars with 3 modalities, 2 modalities, and 1 modality.
    """
    if car_table.shape[0] <= scaling_factor:
        return car_table, image_table, audio_table, complaints_table
    
    np.random.seed(seed)
    random.seed(seed)
    
    # Identify cars by modality count
    cars_with_audio = set(audio_table["car_id"].unique()) if len(audio_table) > 0 else set()
    cars_with_image = set(image_table["car_id"].unique()) if len(image_table) > 0 else set()
    cars_with_complaint = set(complaints_table["car_id"].unique()) if len(complaints_table) > 0 else set()
    
    # Categorize cars by modality count
    cars_3_modalities = []
    cars_2_modalities = []
    cars_1_modality = []
    
    for car_id in car_table["car_id"].unique():
        has_audio = car_id in cars_with_audio
        has_image = car_id in cars_with_image
        has_complaint = car_id in cars_with_complaint
        
        modality_count = sum([has_audio, has_image, has_complaint])
        
        if modality_count == 3:
            cars_3_modalities.append(car_id)
        elif modality_count == 2:
            cars_2_modalities.append(car_id)
        elif modality_count == 1:
            cars_1_modality.append(car_id)
    
    # Calculate original ratios
    total_cars = len(car_table)
    ratio_3 = len(cars_3_modalities) / total_cars if total_cars > 0 else 0
    ratio_2 = len(cars_2_modalities) / total_cars if total_cars > 0 else 0
    ratio_1 = len(cars_1_modality) / total_cars if total_cars > 0 else 0
    
    # Calculate target counts maintaining ratios
    target_3 = max(1, int(scaling_factor * ratio_3)) if len(cars_3_modalities) > 0 else 0
    target_2 = max(1, int(scaling_factor * ratio_2)) if len(cars_2_modalities) > 0 else 0
    target_1 = scaling_factor - target_3 - target_2  # Remaining cars go to 1 modality
    
    # Ensure we don't exceed available cars
    target_3 = min(target_3, len(cars_3_modalities))
    target_2 = min(target_2, len(cars_2_modalities))
    target_1 = min(target_1, len(cars_1_modality))
    
    # Adjust if we need more cars
    remaining = scaling_factor - target_3 - target_2 - target_1
    if remaining > 0:
        # Distribute remaining cars proportionally
        if len(cars_3_modalities) > target_3:
            add_3 = min(remaining, len(cars_3_modalities) - target_3)
            target_3 += add_3
            remaining -= add_3
        if remaining > 0 and len(cars_2_modalities) > target_2:
            add_2 = min(remaining, len(cars_2_modalities) - target_2)
            target_2 += add_2
            remaining -= add_2
        if remaining > 0 and len(cars_1_modality) > target_1:
            target_1 += remaining
    
    # Sample cars from each category
    selected_cars = []
    
    if target_3 > 0 and len(cars_3_modalities) > 0:
        selected_3 = random.sample(cars_3_modalities, min(target_3, len(cars_3_modalities)))
        selected_cars.extend(selected_3)
    
    if target_2 > 0 and len(cars_2_modalities) > 0:
        selected_2 = random.sample(cars_2_modalities, min(target_2, len(cars_2_modalities)))
        selected_cars.extend(selected_2)
    
    if target_1 > 0 and len(cars_1_modality) > 0:
        selected_1 = random.sample(cars_1_modality, min(target_1, len(cars_1_modality)))
        selected_cars.extend(selected_1)
    
    # Filter car table
    car_table_sf = car_table[car_table["car_id"].isin(selected_cars)].copy()
    car_table_sf = car_table_sf.reset_index(drop=True)
    car_table_sf["car_id"] = car_table_sf.index
    
    # Create mapping from old car_id to new car_id
    old_to_new = dict(zip(selected_cars, car_table_sf["car_id"]))
    
    # Filter and update related tables
    car_ids_set = set(selected_cars)
    
    image_table_sf = image_table[image_table["car_id"].isin(car_ids_set)].copy()
    image_table_sf["car_id"] = image_table_sf["car_id"].map(old_to_new)
    
    audio_table_sf = audio_table[audio_table["car_id"].isin(car_ids_set)].copy()
    audio_table_sf["car_id"] = audio_table_sf["car_id"].map(old_to_new)
    
    complaints_table_sf = complaints_table[complaints_table["car_id"].isin(car_ids_set)].copy()
    complaints_table_sf["car_id"] = complaints_table_sf["car_id"].map(old_to_new)
    
    return car_table_sf, image_table_sf, audio_table_sf, complaints_table_sf


def _prepare_data_from_scratch(args: argparse.Namespace) -> None:
    """Prepares the cars data from scratch by downloading datasets and creating tables."""
    _download_kaggle_datasets()

    base_path = Path(__file__).resolve().parents[4]
    num_cars = args.scaling_factor

    source_data_folder = base_path / "files" / "cars" / "data" / "source_data"
    os.makedirs(source_data_folder, exist_ok=True)
    
    # Generate synthetic car data
    if not os.path.exists(f"{base_path}/files/cars/data/source_data/car_data.csv"):
        print("Generating synthetic car data...")
        car_table = _generate_synthetic_car_data(num_cars=300000, seed=args.seed)
        car_table.to_csv(f"{base_path}/files/cars/data/source_data/car_data.csv", index=False)
    else:
        car_table = pd.read_csv(f"{base_path}/files/cars/data/source_data/car_data.csv")

    if not os.path.exists(f"{base_path}/files/cars/data/source_data/all_images.csv") or not Path(f"{base_path}/files/cars/data/all_car_images").exists():
        print("Preparing image data...")
        stanford_images = _prepare_car_images_stanford(args.stanford_cars)
        damage_images = _prepare_car_images_damage(args.damage_images)

        all_images = pd.concat([stanford_images, damage_images])
        all_images.to_csv(f"{base_path}/files/cars/data/source_data/all_images.csv", index=False)
    else:
        all_images = pd.read_csv(f"{base_path}/files/cars/data/source_data/all_images.csv")

    if not os.path.exists(f"{base_path}/files/cars/data/source_data/all_audio.csv") or not Path(f"{base_path}/files/cars/data/all_car_audio").exists():
        print("Preparing audio data...")
        audio_data = _prepare_car_audio_data(args.audio_diagnostics)
        audio_data.to_csv(f"{base_path}/files/cars/data/source_data/all_audio.csv", index=False)
    else:
        audio_data = pd.read_csv(f"{base_path}/files/cars/data/source_data/all_audio.csv")
        
    if not os.path.exists(f"{base_path}/files/cars/data/source_data/all_complaints.csv"):
        print("Preparing text data...")
        complaints_data = _prepare_complaints_text_data(args.complaints)
        complaints_data.to_csv(f"{base_path}/files/cars/data/source_data/all_complaints.csv", index=False)
    else:
        complaints_data = pd.read_csv(f"{base_path}/files/cars/data/source_data/all_complaints.csv")
    
    # Create linked tables with meaningful associations
    print("Linking data with meaningful cross-modal associations...")

    files_list = [f"{base_path}/files/cars/data/full_data/car_data_full.csv", f"{base_path}/files/cars/data/full_data/image_data_full.csv", f"{base_path}/files/cars/data/full_data/audio_data_full.csv", f"{base_path}/files/cars/data/full_data/text_complaints_data_full.csv"]
    if not all(os.path.exists(file) for file in files_list):
        car_table_with_links, image_table_with_links, audio_table_with_links, complaints_table_with_links = _create_meaningful_modality_links(
            car_table, all_images, audio_data, complaints_data, args.seed
        )
    else:
        car_table_with_links = pd.read_csv(f"{base_path}/files/cars/data/full_data/car_data_full.csv")
        image_table_with_links = pd.read_csv(f"{base_path}/files/cars/data/full_data/image_data_full.csv")
        audio_table_with_links = pd.read_csv(f"{base_path}/files/cars/data/full_data/audio_data_full.csv")
        complaints_table_with_links = pd.read_csv(f"{base_path}/files/cars/data/full_data/text_complaints_data_full.csv")

    # Create output folder
    base_folder = Path(__file__).resolve().parents[4] / "files" / "cars" / "data" / "full_data"
    os.makedirs(base_folder, exist_ok=True)

    # Save full data that can be scaled down
    _denormalize_data(
        car_table_with_links, image_table_with_links, audio_table_with_links, complaints_table_with_links
    ).to_csv(f"{base_folder}/car_data_denormalized.csv", index=False)

     # Shuffle
    car_table_with_links = _shuffle_tables(car_table_with_links)
    image_table_with_links = _shuffle_tables(image_table_with_links)
    audio_table_with_links = _shuffle_tables(audio_table_with_links)
    complaints_table_with_links = _shuffle_tables(complaints_table_with_links)

    car_table_with_links.to_csv(f"{base_folder}/car_data_full.csv", index=False)
    image_table_with_links.to_csv(f"{base_folder}/image_data_full.csv", index=False)
    audio_table_with_links.to_csv(f"{base_folder}/audio_data_full.csv", index=False)
    complaints_table_with_links.to_csv(f"{base_folder}/text_complaints_data_full.csv", index=False)
    
    # Create output folder
    base_folder = Path(__file__).resolve().parents[4] / "files" / "cars" / "data"
    
    # Scale down if needed
    if num_cars < len(car_table_with_links):
        car_table_sf, image_table_sf, audio_table_sf, complaints_table_sf = scale_down_data(
            car_table_with_links, image_table_with_links, audio_table_with_links, complaints_table_with_links,
            scaling_factor=args.scaling_factor,
            seed=args.seed
        )
        
    else:
        car_table_sf = car_table_with_links
        image_table_sf = image_table_with_links
        audio_table_sf = audio_table_with_links
        complaints_table_sf = complaints_table_with_links
    
        num_cars = car_table_with_links.shape[0]
    
    # Save
    car_table_sf.to_csv(f"{base_folder}/car_data_{num_cars}.csv", index=False)
    image_table_sf.to_csv(f"{base_folder}/image_car_data_{num_cars}.csv", index=False)
    audio_table_sf.to_csv(f"{base_folder}/audio_car_data_{num_cars}.csv", index=False)
    complaints_table_sf.to_csv(f"{base_folder}/text_complaints_data_{num_cars}.csv", index=False)
    
    print(f"Data preparation complete! Files saved to {base_folder}.")


def prepare_data(scaling_factor: int = 157376) -> None:
    """Main function to prepare cars data."""
    if scaling_factor < 1:
        raise ValueError("scaling_factor should be at least 1")
    
    # Check if data already exists
    base_folder = Path(__file__).resolve().parents[4] / "files" / "cars" / "data"
    folder = base_folder / f"sf_{scaling_factor}"
    
    csv_files = [
        "car_data_full.csv",
        "image_data_full.csv",
        "audio_data_full.csv",
        "text_complaints_data_full.csv"
    ]

    base_folder_full = Path(__file__).resolve().parents[4] / "files" / "cars" / "data" / f"sf_{scaling_factor}" if scaling_factor != 157376 else Path(__file__).resolve().parents[4] / "files" / "cars" / "data" / "full_data"
    base_folder = Path(__file__).resolve().parents[4] / "files" / "cars" / "data" / f"sf_{scaling_factor}"
    
    if all(os.path.exists(base_folder_full / f) for f in csv_files):
        print("Data already exists, skipping download.")
    
    else:
        _download_from_drive(id="1mNJaYSv5W_5sWhrGCCfdo5ljmfMthifI", file_name="full_data.zip")
    
    if not Path(f"{Path(__file__).resolve().parents[4] / "files" / "cars" / "data"}/all_car_images").exists():
        _download_from_drive(id="1EjSOvDH2M-QpSdnxDTLzyrq1Z08m_0-N", file_name="all_car_images.zip")

    if not Path(f"{Path(__file__).resolve().parents[4] / "files" / "cars" / "data"}/all_car_audio").exists():
        _download_from_drive(id="11dUPwTRuCpHSTAQAo3T0GWKr73WokvZ5", file_name="all_car_audio.zip")

    car_table_with_links = pd.read_csv(f"{base_folder_full}/car_data_full.csv")
    image_table_with_links = pd.read_csv(f"{base_folder_full}/image_data_full.csv")
    audio_table_with_links = pd.read_csv(f"{base_folder_full}/audio_data_full.csv")
    complaints_table_with_links = pd.read_csv(f"{base_folder_full}/text_complaints_data_full.csv")

    # Scale down if needed
    if scaling_factor < len(car_table_with_links):
        car_table_sf, image_table_sf, audio_table_sf, complaints_table_sf = scale_down_data(
            car_table_with_links, image_table_with_links, audio_table_with_links, complaints_table_with_links,
            scaling_factor=scaling_factor,
            seed=42
        )
        
    else:
        car_table_sf = car_table_with_links
        image_table_sf = image_table_with_links
        audio_table_sf = audio_table_with_links
        complaints_table_sf = complaints_table_with_links

        scaling_factor = car_table_with_links.shape[0]
    
    # Save
    os.makedirs(base_folder, exist_ok=True)
    car_table_sf.to_csv(f"{base_folder}/car_data_{scaling_factor}.csv", index=False)
    image_table_sf.to_csv(f"{base_folder}/image_car_data_{scaling_factor}.csv", index=False, columns=["image_path","image_id", "car_id"])
    audio_table_sf.to_csv(f"{base_folder}/audio_car_data_{scaling_factor}.csv", index=False, columns=["audio_path","audio_id", "car_id"])
    complaints_table_sf.to_csv(f"{base_folder}/text_complaints_data_{scaling_factor}.csv", index=False, columns=["summary","complaint_id", "car_id"])


def main():
    parser = argparse.ArgumentParser(description="Generate cars dataset from Kaggle sources")
    
    parser.add_argument(
        "--scaling_factor",
        type=int,
        default=157376,
        help="Number of cars in the dataset (default: 20000)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)"
    )
    
    base_path = Path(__file__).resolve().parents[4]
    raw_data = base_path / "files" / "cars" / "data" / "raw_data"
    
    parser.add_argument(
        "--damage_images",
        type=str,
        default=str(raw_data / "vehicle-damage-detection"),
        help="Path to vehicle damage detection dataset"
    )
    
    parser.add_argument(
        "--stanford_cars",
        type=str,
        default=str(raw_data / "stanford-cars"),
        help="Path to Stanford car dataset"
    )
    
    parser.add_argument(
        "--audio_diagnostics",
        type=str,
        default=str(raw_data / "car-diagnostics"),
        help="Path to car diagnostics audio dataset"
    )
    
    parser.add_argument(
        "--complaints",
        type=str,
        default=str(raw_data / "nhtsa-dataset"),
        help="Path to NHTSA complaints dataset"
    )
    
    args = parser.parse_args()
    
    if args.scaling_factor < 1:
        raise ValueError("scaling_factor should be at least 1")
    
    download_data_from_drive = True
    if download_data_from_drive:
        prepare_data(scaling_factor=args.scaling_factor)
    else:
        _prepare_data_from_scratch(args)


if __name__ == "__main__":
    main()
