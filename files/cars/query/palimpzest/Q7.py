import os
import pandas as pd
import palimpzest as pz

from palimpzest.core.lib.schemas import ImageFilepath, AudioFilepath
import copy


data_audio_cols = [
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "audio_path", "type": AudioFilepath, "desc": "The filepath containing audios."}
]

data_image_cols = [
    {"name": "image_id", "type": int, "desc": "The integer id for the car image"},
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "image_path", "type": ImageFilepath, "desc": "The filepath containing the car image"},
]


class MyDataset(pz.IterDataset):
  def __init__(self, id: str, car_df: pd.DataFrame, schema: list):
    super().__init__(id=id, schema=schema)
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
    complaints = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/text_complaints_data_{scale_factor}.csv"))

    # Join for audio
    audio_join = cars.join(audio.set_index('car_id'), on='car_id', how='inner')[['car_id', 'year', 'audio_path']]
    audio_pz = MyDataset(id="audio", car_df=audio_join, schema=data_audio_cols)
    audio_pz = audio_pz.sem_filter("You are given an audio recording of car diagnostics. Return true if the car from the recording has worn out brakes.", depends_on=["audio_path"])
    output_audio = audio_pz.run(copy.deepcopy(pz_config))
    audio_cost = output_audio.execution_stats.total_execution_cost
    output_audio = output_audio.to_df()
    
    # Join for text
    text_join = cars.join(complaints.set_index('car_id'), on='car_id', how='inner')
    complaints_pz = pz.MemoryDataset(id="complaints", vals=text_join)
    complaints_pz = complaints_pz.sem_filter("In the complaint, the car has some problems with electrical system / connected to electrical system. Complaint:", depends_on=["summary"])
    output_text = complaints_pz.run(copy.deepcopy(pz_config))
    text_cost = output_text.execution_stats.total_execution_cost
    output_text = output_text.to_df()

    # Join for image
    image_join = cars.join(car_images.set_index('car_id'), on='car_id', how='inner')[['car_id', 'year', 'image_path', 'image_id']]
    car_images_pz = MyDataset(id="car_images", car_df=image_join, schema=data_image_cols)
    car_images_pz = car_images_pz.sem_filter("You are given an image of a vehicle or its parts. Return true if car is dented.", depends_on=["image_path"])
    output_images = car_images_pz.run(copy.deepcopy(pz_config))
    image_cost = output_images.execution_stats.total_execution_cost
    output_images = output_images.to_df()

    res = pd.concat([output_audio[['car_id']], output_text[['car_id']], output_images[['car_id']]], ignore_index=True).drop_duplicates()
    # Ensure column names are strings
    res.columns = [str(col) for col in res.columns]

    cost = audio_cost + text_cost + image_cost
    return (res, cost)

