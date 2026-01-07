import os
import pandas as pd

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    complaints = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"text_complaints_data_{scale_factor}.csv"))

    # Filter data
    complaints = complaints.sem_filter('You are be given a textual complaint entailing that the car was in a crash/accident/collision. Complaint: {summary}.')
    return complaints['car_id']
