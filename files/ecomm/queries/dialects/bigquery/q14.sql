SELECT
  ARRAY_AGG(
    ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images.uri, '/')), '.'))
    ORDER BY AI.SCORE(('The image ', images.ref, ' fits the description: ', styles_details.productDisplayName, ' ', styles_details.productDescriptors.description.value), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>) ASC
    LIMIT 1
  )[0] AS id
FROM fashion_product_images.STYLES_DETAILS as styles_details
JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
  ON AI.IF(('The image ', images.ref, ' fits the description: ', styles_details.productDisplayName, ' ', styles_details.productDescriptors.description.value), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
WHERE styles_details.price < 130
  AND AI.IF(('The image ', images.ref, ' depicts white socks'), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
GROUP BY
  styles_details.id,
  styles_details.productDisplayName,
  styles_details.productDescriptors.description
;
