SELECT DISTINCT c.car_id as car_id
FROM cars_dataset.cars  AS c
JOIN cars_dataset.audio_mm  AS a 
ON c.car_id = a.car_id
WHERE c.fuel_type = 'Electric' AND AI.IF(
    prompt => (
      "You are given an audio recording of car diagnostics. Return true if the car from the recording has a dead battery, false otherwise.", 
      a.image
    ), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>
)
