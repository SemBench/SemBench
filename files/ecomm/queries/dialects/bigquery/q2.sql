SELECT
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images.uri, '/')), '.')) as id
FROM EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
WHERE true
  AND AI.IF(
    ('The image shows a (pair of) sports shoe(s) that feature the colors yellow and silver.', images.ref),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  )
;
