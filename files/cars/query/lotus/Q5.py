import os
import pandas as pd
from lotus.types import ImageArray, AudioArray

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    cars = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"car_data_{scale_factor}.csv"))
    images = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"image_car_data_{scale_factor}.csv"))
    audio = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"audio_car_data_{scale_factor}.csv"))

    # Join cars with images and audio
    joined = cars.merge(images, on='car_id', how='inner')
    joined = joined.merge(audio, on='car_id', how='inner')

    # Filter for Automatic transmission
    joined = joined[joined['transmission'] == 'Automatic']

    # Apply semantic filters
    joined['audio_path'] = joined['audio_path'].apply(lambda x: AudioArray([x]))
    joined = joined.sem_filter('You are given an audio recording of car diagnostics. Return true if the recording captures an audio of a damaged car.', default=False)

    joined['image_path'] = joined['image_path'].apply(lambda x: ImageArray([x]))
    joined = joined.sem_filter('You are given an image of a vehicle or its parts. Return true if car is damaged.', default=False)

    # Count distinct cars
    count = joined['car_id'].nunique()

    return pd.DataFrame({'count': [count]})
