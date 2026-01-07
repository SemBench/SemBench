import os
import pandas as pd

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    cars = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"car_data_{scale_factor}.csv"))
    complaints = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"text_complaints_data_{scale_factor}.csv"))

    # Join cars with complaints
    joined = cars.merge(complaints, on='car_id', how='inner')

    # Filter for engine problems
    joined = joined.sem_filter('In the complaint, the car has some problems with engine / connected to engine. Complaint: {summary}.')

    # Calculate average age
    average_age = 2026 - joined['year'].mean()

    return pd.DataFrame({'average_age': [average_age]})
