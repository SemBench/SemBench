SELECT DISTINCT p.car_id
FROM cars_dataset.car_mm as x, cars_dataset.cars AS p, cars_dataset.audio_mm as a
WHERE p.car_id = x.car_id AND p.car_id = a.car_id AND AI.IF(
    prompt => (
    "You are given an image of a vehicle and an audio recording of car diagnostics. Return true if car is torn according to image and has bad ignition according to audio.", 
    x.image, a.image
    ), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>)
    