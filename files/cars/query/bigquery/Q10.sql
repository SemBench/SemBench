SELECT p.car_id, AI.GENERATE(
    FORMAT("""
    Classify car complaint to one of given problem categories. Answer only one of given problem categories, nothing more. 
    Problem categories: ELECTRICAL SYSTEM, POWER TRAIN, ENGINE, STEERING, SERVICE BRAKES, STRUCTURE, AIR BAGS, ENGINE AND ENGINE COOLING, VEHICLE SPEED CONTROL, VISIBILITY/WIPER, FUEL/PROPULSION SYSTEM, FORWARD COLLISION AVOIDANCE, EXTERIOR LIGHTING, SUSPENSION, FUEL SYSTEM, VISIBILITY, WHEELS, SEAT BELTS, BACK OVER PREVENTION, TIRES, SEATS, LATCHES/LOCKS/LINKAGES, LANE DEPARTURE, EQUIPMENT.
    Complaint: %s
    """, c.summary), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>).result as problem_category
FROM cars_dataset.cars AS p
JOIN cars_dataset.complaints AS c
ON p.car_id = c.car_id



