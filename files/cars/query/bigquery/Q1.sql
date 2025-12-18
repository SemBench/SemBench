SELECT DISTINCT c.car_id
FROM cars_dataset.complaints  AS c
WHERE AI.IF(
    FORMAT("""You are be given a textual complaint entailing that the car was in a crash/accident/collision. Complaint: %s.""", c.summary), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>
)
