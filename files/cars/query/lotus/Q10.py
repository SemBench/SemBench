import os
import pandas as pd

def run(data_dir: str, scale_factor: int = 157376):
    # Load data
    cars = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"car_data_{scale_factor}.csv"))
    complaints = pd.read_csv(os.path.join(data_dir, "data", f"sf_{scale_factor}", f"text_complaints_data_{scale_factor}.csv"))

    # Join cars with complaints
    joined = cars.merge(complaints, on='car_id', how='inner')

    # Define categories
    categories = [
        "ELECTRICAL SYSTEM", "POWER TRAIN", "ENGINE", "STEERING", "SERVICE BRAKES",
        "STRUCTURE", "AIR BAGS", "ENGINE AND ENGINE COOLING", "VEHICLE SPEED CONTROL",
        "VISIBILITY/WIPER", "FUEL/PROPULSION SYSTEM", "FORWARD COLLISION AVOIDANCE",
        "EXTERIOR LIGHTING", "SUSPENSION", "FUEL SYSTEM", "VISIBILITY", "WHEELS",
        "SEAT BELTS", "BACK OVER PREVENTION", "TIRES", "SEATS", "LATCHES/LOCKS/LINKAGES",
        "LANE DEPARTURE", "EQUIPMENT"
    ]

    # Create prompt with categories
    categories_str = ", ".join(categories)
    prompt = f'Classify car complaint to one of given problem categories. Categories: {categories_str}. Answer only one of given problem categories, nothing more.'

    # Apply classification using sem_extract
    joined = joined.sem_extract(
        input_cols=["summary"],
        output_cols={"problem_category": prompt}
    )

    return joined[['car_id', 'problem_category']]
