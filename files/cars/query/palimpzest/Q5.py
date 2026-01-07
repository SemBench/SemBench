import os
import pandas as pd
import palimpzest as pz

from palimpzest.core.lib.schemas import ImageFilepath, AudioFilepath
from palimpzest.core.elements.groupbysig import GroupBySig


data_cols = [
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "transmission", "type": str, "desc": "The string transmission."},
    {"name": "image_id", "type": int, "desc": "The integer id for the car image"},
    {"name": "image_path", "type": ImageFilepath, "desc": "The filepath containing the car image"},
    {"name": "audio_id", "type": int, "desc": "The integer id for the audio"},
    {"name": "audio_path", "type": AudioFilepath, "desc": "The filepath containing audios."},
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
    cars = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/car_data_{scale_factor}.csv")) 
    car_images = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/image_car_data_{scale_factor}.csv"))
    audio = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/audio_car_data_{scale_factor}.csv"))
    
    # Join 
    tmp_join = cars.join(car_images.set_index('car_id'), on='car_id', how='inner')[['image_path', 'car_id', 'image_id', 'transmission']]
    tmp_join = tmp_join.join(audio.set_index('car_id'), on='car_id', how='inner')[['car_id', 'transmission', 'image_id', 'image_path', 'audio_path', 'audio_id']]
    
    tmp_join = MyDataset(id="my-data", car_df=tmp_join)

    # Filter transmission
    tmp_join = tmp_join.filter(lambda row: row['transmission'] == 'Automatic')

    # Filter audio
    tmp_join = tmp_join.sem_filter('You are given an audio recording of car diagnostics. Return true if the recording captures an audio of a damaged car.', depends_on=['audio_path'])
    # Filter image
    tmp_join = tmp_join.sem_filter("You are given an image of a vehicle or its parts. Return true if car is damaged.", depends_on=['image_path'])
    tmp_join = tmp_join.project(['car_id', 'transmission'])
    tmp_join = tmp_join.distinct(distinct_cols=['car_id', 'transmission'])

    # Group by
    gby_desc = GroupBySig(group_by_fields=["transmission"], agg_funcs=["count"], agg_fields=["transmission"])
    res = tmp_join.groupby(gby_desc)

    output = res.run(pz_config)
    return output

