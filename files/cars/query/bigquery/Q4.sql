SELECT 2026 - AVG(c.year) AS average_age
FROM cars_dataset.cars  AS c
JOIN cars_dataset.complaints  AS s
ON c.car_id = s.car_id
WHERE AI.IF(
    FORMAT("""In the complaint, the car has some problems with engine / connected to engine. Complaint: %s.""", s.summary), 
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' 
    <<other_params>>
)
