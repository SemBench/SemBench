import os
import pandas as pd
import palimpzest as pz


def run(pz_config, data_dir: str, scale_factor: int = 157376):
    # Load data
    complaints_text = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/text_complaints_data_{scale_factor}.csv"))
    complaints_text = pz.MemoryDataset(id="complaints", vals=complaints_text)

    # Filter data
    complaints_text = complaints_text.sem_filter('You are be given a textual complaint entailing that the car was in a crash/accident/collision. Complaint:', depends_on=['summary'])
    complaints_text = complaints_text.project(['car_id'])
    complaints_text = complaints_text.distinct(distinct_cols=['car_id'])
    
    output = complaints_text.run(pz_config)
    
    return output

