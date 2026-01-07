import os
import pandas as pd
import palimpzest as pz

def run(pz_config, data_dir: str, scale_factor: int = 157376):
    # Load data
    complaints_text = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/text_complaints_data_{scale_factor}.csv"))
    cars = pd.read_csv(os.path.join(data_dir, f"data/sf_{scale_factor}/car_data_{scale_factor}.csv"))
    
    # Join before since PZ does not support joins
    tmp_join = cars.join(complaints_text.set_index('car_id'), on='car_id', how='inner')
    complaints_text = pz.MemoryDataset(id="complaints", vals=tmp_join)

    # Classify
    complaints_text = complaints_text.sem_map(
        cols=[{'name': 'problem_category', 'type': str, 'desc': 'Classify car complaint to one of given problem categories. Answer only one of given problem categories, nothing more. Complaint: Categories: ELECTRICAL SYSTEM, POWER TRAIN, ENGINE, STEERING, SERVICE BRAKES, STRUCTURE, AIR BAGS, ENGINE AND ENGINE COOLING, VEHICLE SPEED CONTROL, VISIBILITY/WIPER, FUEL/PROPULSION SYSTEM, FORWARD COLLISION AVOIDANCE, EXTERIOR LIGHTING, SUSPENSION, FUEL SYSTEM, VISIBILITY, WHEELS, SEAT BELTS, BACK OVER PREVENTION, TIRES, SEATS, LATCHES/LOCKS/LINKAGES, LANE DEPARTURE, EQUIPMENT.'}], 
        depends_on=['summary'])
    complaints_text = complaints_text.project(['car_id', 'problem_category'])
    
    output = complaints_text.run(pz_config)
    return output

