import os
import pandas as pd
from lotus.types import ImageArray, AudioArray

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    cars = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"car_data_{scale_factor}.csv"))
    images = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"image_car_data_{scale_factor}.csv"))
    audio = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"audio_car_data_{scale_factor}.csv"))
    complaints = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"text_complaints_data_{scale_factor}.csv"))

    # Join all tables
    joined = cars.merge(images, on='car_id', how='left')
    joined = joined.merge(audio, on='car_id', how='left')
    joined = joined.merge(complaints, on='car_id', how='left')

    # Filter for cars with at least 2 modalities
    joined = joined[(joined['audio_id'].notna() & joined['complaint_id'].notna()) |
                    (joined['image_id'].notna() & joined['complaint_id'].notna()) |
                    (joined['image_id'].notna() & joined['audio_id'].notna())]

    # Check each modality separately
    # Audio damage check
    audio_df = joined[joined['audio_id'].notna()].copy()
    audio_df['audio_path'] = audio_df['audio_path'].apply(lambda x: AudioArray([x]))
    audio_damaged = audio_df.sem_filter('You are given an audio recording of car diagnostics. Return true if the recording captures an audio of a damaged car.', default=False)
    audio_damaged_ids = set(audio_damaged['car_id'])

    # Image damage check
    image_df = joined[joined['image_id'].notna()].copy()
    image_df['image_path'] = image_df['image_path'].apply(lambda x: ImageArray([x]))
    image_damaged = image_df.sem_filter('You are given an image of a vehicle or its parts. Return true if car is damaged.', default=False)
    image_damaged_ids = set(image_damaged['car_id'])

    # Text damage check (fire/burned)
    text_df = joined[joined['complaint_id'].notna()].copy()
    text_damaged = text_df.sem_filter('You are be given a textual complaint entailing that the car was in on fire or burned. Complaint: {summary}.', default=False)
    text_damaged_ids = set(text_damaged['car_id'])

    # XOR logic: at least one modality shows damage AND at least one doesn't
    all_car_ids = set(joined['car_id'].unique())

    result_ids = []
    for car_id in all_car_ids:
        has_audio = car_id in set(joined[joined['audio_id'].notna()]['car_id'])
        has_image = car_id in set(joined[joined['image_id'].notna()]['car_id'])
        has_text = car_id in set(joined[joined['complaint_id'].notna()]['car_id'])

        is_audio_damaged = car_id in audio_damaged_ids if has_audio else None
        is_image_damaged = car_id in image_damaged_ids if has_image else None
        is_text_damaged = car_id in text_damaged_ids if has_text else None

        # Count positives and negatives
        statuses = [s for s in [is_audio_damaged, is_image_damaged, is_text_damaged] if s is not None]

        if len(statuses) >= 2:  # At least 2 modalities
            has_positive = any(statuses)
            has_negative = not all(statuses)

            if has_positive and has_negative:
                result_ids.append(car_id)

    return pd.DataFrame({'car_id': result_ids})
