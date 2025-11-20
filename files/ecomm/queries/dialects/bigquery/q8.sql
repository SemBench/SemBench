WITH product_selection AS (
  SELECT *
  FROM fashion_product_images.STYLES_DETAILS styles_details
  WHERE true
    AND CHAR_LENGTH(styles_details.productDescriptors.description.value) >= 3000
)
SELECT
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images.uri, '/')), '.')) || '-' ||
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images.uri, '/')), '.')) AS id,
FROM product_selection as styles_details
JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
  ON AI.IF(
    ('The image ', images.ref, ' fits the description: ', styles_details.productDisplayName, ' ', styles_details.productDescriptors.description.value),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  )
;
