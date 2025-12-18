SELECT p.vin as vin
FROM cars_dataset.cars as p 
JOIN cars_dataset.car_mm  AS x 
ON p.car_id = x.car_id
WHERE p.transmission = "Manual" AND AI.IF(
    prompt => (
      "You are given an image of a vehicle or its parts. Return true if car is not damaged.", 
      x.image
    ), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>
)
LIMIT 10;
