WITH sick_audio AS (
  SELECT DISTINCT p.car_id, year
  FROM cars_dataset.cars  AS p
  JOIN cars_dataset.audio_mm  AS a 
  ON p.car_id = a.car_id
  WHERE AI.IF(
    prompt => ("You are given an audio recording of car diagnostics. Return true if the car from the recording has worn out brakes.", 
    a.image), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>)
),
sick_text AS (
  SELECT p.car_id, year
  FROM cars_dataset.cars  AS p
  JOIN cars_dataset.complaints  AS s
  ON p.car_id = s.car_id
  WHERE AI.IF(
    FORMAT("""
    In the complaint, the car has some problems with electrical system / connected to electrical system. Complaint: %s.
    """, s.summary), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>)
),
sick_image AS(
  SELECT p.car_id, year
  FROM cars_dataset.car_mm as x
  JOIN cars_dataset.cars  AS p
  ON p.car_id = x.car_id 
  WHERE AI.IF(
    prompt => ("You are given an image of a vehicle or its parts. Return true if car is dented.", 
    x.image), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>)
)

SELECT sick_audio.car_id FROM sick_audio
UNION DISTINCT
SELECT sick_text.car_id FROM sick_text
UNION DISTINCT
SELECT sick_image.car_id FROM sick_image
