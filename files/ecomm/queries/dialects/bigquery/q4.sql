WITH product_selection AS (
  SELECT images.*
  FROM fashion_product_images.STYLES_DETAILS styles_details
  JOIN fashion_product_images.IMAGE_MAPPING mapping
    ON styles_details.styleImages.default.imageURL = mapping.link
  JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
    ON ARRAY_LAST(SPLIT(images.uri, '/')) = mapping.filename
  WHERE true
    -- Limit to simple colors:
    AND baseColour IN ('Black', 'Blue', 'Red', 'White', 'Orange', 'Green')
)
SELECT
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images.uri, '/')), '.')) as id,
  AI.GENERATE(
    ('Extract the primary color of the product in the image. Only return the base color, nothing else: ', images.ref),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  ).result AS category
FROM product_selection as images
;
