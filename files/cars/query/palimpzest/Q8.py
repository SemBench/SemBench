import os
import pandas as pd
import palimpzest as pz

from palimpzest.core.lib.schemas import ImageFilepath

# define the schema for the data you read from the file
car_image_data_cols = [
    {"name": "image_path", "type": ImageFilepath, "desc": "The filepath containing the car image"},
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "image_id", "type": int, "desc": "The integer id for the car image"},
]


class MyDataset(pz.IterDataset):
  def __init__(self, id: str, car_df: pd.DataFrame):
    super().__init__(id=id, schema=car_image_data_cols)
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
    
    # Join before since PZ does not support joins
    tmp_join = cars.join(car_images.set_index('car_id'), on='car_id', how='inner')[['image_path', 'car_id', 'image_id']]

    tmp_join = MyDataset(id="my-car-data", car_df=tmp_join)

    # Filter image
    tmp_join = tmp_join.sem_filter('You are given an image of a vehicle or its parts. Return true if car has both, puncture and paint scratches.', depends_on=['image_path'])
    tmp_join = tmp_join.project(['car_id'])
    candidates = tmp_join.limit(100)

    output = candidates.run(pz_config)
    return output

