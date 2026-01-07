import os
import pandas as pd
import palimpzest as pz

from palimpzest.core.lib.schemas import ImageFilepath, AudioFilepath
import copy

# define the schema for the data you read from the file
data_image_cols = [
    {"name": "image_id", "type": int, "desc": "The integer id for the car image"},
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "image_path", "type": ImageFilepath, "desc": "The filepath containing the car image"},
]

data_audio_cols = [
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "audio_path", "type": AudioFilepath, "desc": "The filepath containing audios."},
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
    car_images = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/image_car_data_{scale_factor}.csv")) 
    cars = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/car_data_{scale_factor}.csv")) 
    audio = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/audio_car_data_{scale_factor}.csv")) 
    
    # Join cars with images
    image_join = cars.join(car_images.set_index('car_id'), on='car_id', how='inner')[['car_id', 'image_path', 'image_id']]
    image_pz = MyDataset(id="car_images", car_df=image_join, schema=data_image_cols)
    # Filter for torn cars
    image_pz = image_pz.sem_filter("You are given an image of a vehicle or its parts. Return true if car is torn according to the image.", depends_on=['image_path'])
    output_images = image_pz.run(copy.deepcopy(pz_config))
    image_cost = output_images.execution_stats.total_execution_cost
    output_images = output_images.to_df()
    
    # Join cars with audio
    audio_join = cars.join(audio.set_index('car_id'), on='car_id', how='inner')[['car_id', 'audio_path']]
    audio_pz = MyDataset(id="audio", car_df=audio_join, schema=data_audio_cols)
    # Filter for bad ignition
    audio_pz = audio_pz.sem_filter("You are given an audio recording of car diagnostics. Return true if the car from the recording has bad ignition.", depends_on=['audio_path'])
    output_audio = audio_pz.run(copy.deepcopy(pz_config))
    audio_cost = output_audio.execution_stats.total_execution_cost
    output_audio = output_audio.to_df()
    
    # Find cars that satisfy both conditions (torn AND bad ignition)
    torn_cars = set(output_images['car_id'].unique())
    bad_ignition_cars = set(output_audio['car_id'].unique())
    result_cars = torn_cars & bad_ignition_cars
    
    # Create result DataFrame
    result_df = pd.DataFrame({'car_id': list(result_cars)})
    result_df = result_df.drop_duplicates()
    # Ensure column names are strings
    result_df.columns = [str(col) for col in result_df.columns]
    
    # Return as tuple (DataFrame, cost) like Q7
    total_cost = image_cost + audio_cost
    return (result_df, total_cost)

