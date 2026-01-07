import os
import pandas as pd
import palimpzest as pz
from palimpzest.core.lib.schemas import AudioFilepath

# define the schema for the data you read from the file
data_cols = [
    {"name": "audio_path", "type": AudioFilepath, "desc": "The filepath containing audios."},
    {"name": "car_id", "type": int, "desc": "The integer id for the car."},
    {"name": "audio_id", "type": int, "desc": "The integer id for the audio."},
    {"name": "fuel_type", "type": str, "desc": "The string fuel_type."},
]

class MyDataset(pz.IterDataset):
  def __init__(self, id: str, car_df: pd.DataFrame):
    super().__init__(id=id, schema=data_cols)
    self.car_df = car_df

  def __len__(self):
    return len(self.car_df)

  def __getitem__(self, idx: int):
    # get row from dataframe
    return self.car_df.iloc[idx].to_dict()


def run(pz_config, data_dir: str, scale_factor: int = 157376):
    # Load data
    audio = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/audio_car_data_{scale_factor}.csv"))
    cars = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/car_data_{scale_factor}.csv")) 
    
    # Join
    tmp_join = cars.join(audio.set_index('car_id'), on='car_id', how='inner')[['audio_path', 'car_id', 'audio_id', 'fuel_type']]

    tmp_join = MyDataset(id="my-data", car_df=tmp_join)

    # Filter fuel_type
    tmp_join = tmp_join.filter(lambda row: row['fuel_type'] == 'Electric')

    # Filter audio
    tmp_join = tmp_join.sem_filter('You are given an audio recording of car diagnostics. Return true if the car from the recording has a dead battery, false otherwise.', depends_on=['audio_path'])
    tmp_join = tmp_join.project(['car_id'])
    tmp_join = tmp_join.distinct(distinct_cols=['car_id'])
    
    output = tmp_join.run(pz_config)
    return output

