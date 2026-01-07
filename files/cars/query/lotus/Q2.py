import os
import pandas as pd
from lotus.types import AudioArray

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    cars = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"car_data_{scale_factor}.csv"))
    audio = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"audio_car_data_{scale_factor}.csv"))

    # Join cars with audio
    joined = cars.merge(audio, on='car_id', how='inner')

    # Filter for Electric cars
    joined = joined[joined['fuel_type'] == 'Electric']

    # Apply semantic filter on audio
    joined['audio_path'] = joined['audio_path'].apply(lambda x: AudioArray([x]))
    joined = joined.sem_filter('You are given an audio recording of car diagnostics. Return true if the car from the recording has a dead battery, false otherwise.', default=False)

    return joined['car_id']
