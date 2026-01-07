import os
import numpy as np
import pandas as pd
import palimpzest as pz

from palimpzest.core.lib.schemas import ImageFilepath, AudioFilepath
import copy
from palimpzest.constants import Model

data_audio_cols = [
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "audio_path", "type": AudioFilepath, "desc": "The filepath containing audios."},
]

data_image_cols = [
    {"name": "image_id", "type": int, "desc": "The integer id for the car image"},
    {"name": "car_id", "type": int, "desc": "The integer id for the car"},
    {"name": "image_path", "type": ImageFilepath, "desc": "The filepath containing the car image."},
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

    # Join with outer joins to get all combinations
    tmp_join = cars.join(car_images.set_index('car_id'), on='car_id', how='outer')[['image_path', 'car_id', 'image_id', 'year']]
    tmp_join = tmp_join.join(audio.set_index('car_id'), on='car_id', how='outer')[['car_id', 'year', 'image_id', 'image_path', 'audio_path', 'audio_id']]
    tmp_join = tmp_join.join(complaints.set_index('car_id'), on='car_id', how='outer')[['car_id', 'year', 'image_id', 'image_path', 'audio_path', 'audio_id', 'complaint_id', 'summary']]

    tmp_join["non_missing_count"] = tmp_join[["image_id", "complaint_id", "audio_id"]].notna().sum(axis=1)

    # Filter: keep rows with at least 2 present
    tmp_join = tmp_join[tmp_join["non_missing_count"] >= 2]
    tmp_join = tmp_join.drop(columns=["non_missing_count"])

    # Filter each modality separately
    audio_filtered = audio.loc[audio["car_id"].isin(tmp_join["car_id"].tolist()), ["car_id", "audio_path"]]
    car_images_filtered = car_images[car_images["car_id"].isin(tmp_join["car_id"].tolist())]
    complaints_filtered = complaints[complaints["car_id"].isin(tmp_join["car_id"].tolist())]

    audio_pz = MyDataset(id="audio", car_df=audio_filtered, schema=data_audio_cols)
    audio_pz = audio_pz.sem_filter("You are given an audio recording of car diagnostics. Return true if the recording captures an audio of a damaged car.", depends_on=["audio_path"])
    output_audio = audio_pz.run(copy.deepcopy(pz_config))
    audio_cost = output_audio.execution_stats.total_execution_cost
    output_audio = output_audio.to_df()
    output_audio["sick_audio"] = 1
    
    car_images_pz = MyDataset(id="car_images", car_df=car_images_filtered, schema=data_image_cols)
    car_images_pz = car_images_pz.sem_filter("You are given an image of a vehicle or its parts. Return true if car is damaged.", depends_on=["image_path"])
    output_images = car_images_pz.run(copy.deepcopy(pz_config))
    image_cost = output_images.execution_stats.total_execution_cost
    output_images = output_images.to_df()
    output_images["sick_image"] = 1

    complaints_pz = pz.MemoryDataset(id="complaints", vals=complaints_filtered)
    complaints_pz = complaints_pz.sem_filter("You are be given a textual complaint entailing that the car was on fire or burned. Complaint:", depends_on=["summary"])
    output_text = complaints_pz.run(copy.deepcopy(pz_config))
    text_cost = output_text.execution_stats.total_execution_cost
    output_text = output_text.to_df()
    output_text["sick_text"] = 1

    tmp_join.reset_index(inplace=True)

    res = tmp_join.join(output_audio.set_index('car_id'), on='car_id', how='outer', rsuffix="_au")
    res = res.join(output_images.set_index('car_id'), on='car_id', how='outer', rsuffix="_im")
    res = res.join(output_text.set_index('car_id'), on='car_id', how='outer', rsuffix="_txt")

    res["sick_text"] = np.where(res["summary_txt"].isna() & res["sick_text"].isna(), 0, res["sick_text"])
    res["sick_image"] = np.where(res["image_path_im"].isna() & res["sick_image"].isna(), 0, res["sick_image"])
    res["sick_audio"] = np.where(res["audio_path_au"].isna() & res["sick_audio"].isna(), 0, res["sick_audio"])

    # Find sick and healthy according to two different modalities
    res = res[((
       (res["sick_audio"] == 1) | (res["sick_text"] == 1) | (res["sick_image"] == 1)) & 
       ((res["sick_audio"] == 0) | (res["sick_text"] == 0) | (res["sick_image"] == 0)
    ))]

    cost = audio_cost + text_cost + image_cost

    return (res[["car_id", "year", "complaint_id", "image_id", "audio_id"]], cost)

