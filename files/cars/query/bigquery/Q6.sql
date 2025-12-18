WITH two_more_modalities AS (
  SELECT p.car_id, p.year, s.complaint_id, s.summary, x.image_id, x.image as image, a.audio_id, a.image as audio
  FROM cars_dataset.cars as p 
  LEFT JOIN cars_dataset.car_mm as x ON p.car_id = x.car_id
  LEFT JOIN cars_dataset.audio_mm as a ON p.car_id = a.car_id
  LEFT JOIN cars_dataset.complaints as s ON p.car_id = s.car_id
  WHERE (a.image IS NOT NULL AND s.complaint_id IS NOT NULL) OR
    (x.image_id IS NOT NULL AND s.complaint_id IS NOT NULL) OR
    (x.image_id IS NOT NULL AND a.image IS NOT NULL) 
),
sick_audio AS (
  SELECT a.car_id
  FROM two_more_modalities as a
  WHERE a.audio_id IS NOT NULL AND AI.IF(
        prompt => (
          "You are given an audio recording of car diagnostics. Return true if the recording captures an audio of a damaged car.", 
          a.audio
        ), 
        connection_id => '<<connection>>',
        model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>)),
sick_image AS(
  SELECT x.car_id
  FROM two_more_modalities as x
  WHERE x.image_id IS NOT NULL AND AI.IF(
      prompt => (
        "You are given an image of a vehicle or its parts. Return true if car is damaged.", 
        x.image
      ), 
      connection_id => '<<connection>>',
      model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>
)
),
sick_text AS (
  SELECT s.car_id
  FROM two_more_modalities as s
  WHERE s.complaint_id IS NOT NULL AND AI.IF(
      FORMAT("""
      You are be given a textual complaint entailing that the car was in on fire or burned. Complaint: %s.
      """, s.summary), 
      connection_id => '<<connection>>',
      model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>)
)
SELECT * FROM (
  SELECT t.car_id, t.year, t.complaint_id, t.image_id, t.audio_id, 
  IF(a.car_id IS NOT NULL, 1, IF(t.audio_id IS NOT NULL, 0, NULL)) AS is_sick_audio, 
  IF(s.car_id IS NOT NULL, 1, IF(t.complaint_id IS NOT NULL, 0, NULL)) AS is_sick_text, 
  IF(x.car_id IS NOT NULL, 1, IF(t.image_id IS NOT NULL, 0, NULL))  AS is_sick_image
  FROM two_more_modalities t
  LEFT JOIN sick_audio a ON t.car_id = a.car_id
  LEFT JOIN sick_text s ON t.car_id = s.car_id
  LEFT JOIN sick_image x ON t.car_id = x.car_id)
WHERE (is_sick_audio = 1 OR is_sick_text = 1 OR is_sick_image = 1)
AND
(is_sick_audio = 0 OR is_sick_text = 0 OR is_sick_image = 0);

