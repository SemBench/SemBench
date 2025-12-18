SELECT transmission, COUNT(*) AS count 
FROM
(
  SELECT DISTINCT p.car_id, p.transmission
  FROM cars_dataset.cars AS p, cars_dataset.audio_mm AS a, cars_dataset.car_mm AS x
  WHERE p.transmission = "Automatic" AND p.car_id = x.car_id AND p.car_id = a.car_id AND
      AI.IF(
      prompt => (
        "You are given an audio recording of car diagnostics. Return true if the recording captures an audio of a damaged car.", 
        a.image
      ), 
      connection_id => '<<connection>>',
      model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
      <<other_params>>
      ) AND
      AI.IF(
      prompt => (
        "You are given an image of a vehicle or its parts. Return true if car is damaged.", 
        x.image
      ), 
      connection_id => '<<connection>>',
      model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
      <<other_params>>
  )
)
GROUP BY transmission;
