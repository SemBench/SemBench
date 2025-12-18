SELECT p.car_id
FROM cars_dataset.car_mm as x
JOIN cars_dataset.cars  AS p
ON p.car_id = x.car_id 
WHERE AI.IF(
    prompt => (
    "You are given an image of a vehicle or its parts. Return true if car has both, puncture and paint scratches.", 
    x.image
    ), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>)
LIMIT 100
