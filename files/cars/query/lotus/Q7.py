import os
import pandas as pd
from lotus.types import ImageArray, AudioArray

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    cars = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"car_data_{scale_factor}.csv"))
    images = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"image_car_data_{scale_factor}.csv"))
    audio = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"audio_car_data_{scale_factor}.csv"))
    complaints = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"text_complaints_data_{scale_factor}.csv"))

    # Check 1: Cars with worn brakes (audio)
    audio_joined = cars.merge(audio, on='car_id', how='inner')
    audio_joined['audio_path'] = audio_joined['audio_path'].apply(lambda x: AudioArray([x]))
    audio_result = audio_joined.sem_filter('You are given an audio recording of car diagnostics. Return true if the car from the recording has worn out brakes.', default=False)

    # Check 2: Cars with electrical problems (text)
    text_joined = cars.merge(complaints, on='car_id', how='inner')
    text_result = text_joined.sem_filter('In the complaint, the car has some problems with electrical system / connected to electrical system. Complaint: {summary}.', default=False)

    # Check 3: Cars that are dented (image)
    image_joined = cars.merge(images, on='car_id', how='inner')
    image_joined['image_path'] = image_joined['image_path'].apply(lambda x: ImageArray([x]))
    image_result = image_joined.sem_filter('You are given an image of a vehicle or its parts. Return true if car is dented.', default=False)

    # UNION: Combine and remove duplicates
    all_results = pd.concat([
        audio_result[['car_id']],
        text_result[['car_id']],
        image_result[['car_id']]
    ]).drop_duplicates()

    return all_results['car_id']
