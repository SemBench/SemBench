import os
import pandas as pd
from lotus.dtype_extensions import ImageArray

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    cars = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"car_data_{scale_factor}.csv"))
    images = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"image_car_data_{scale_factor}.csv"))

    # Join cars with images
    joined = cars.merge(images, on='car_id', how='inner')

    # Apply semantic filter on images
    joined['image_path'] = ImageArray(joined['image_path'])
    joined = joined.sem_filter('You are given an image of a vehicle or its parts. Return true if car has both, puncture and paint scratches. Image: {image_path}', default=False)

    # Limit to 100
    return joined['car_id'].head(100)
