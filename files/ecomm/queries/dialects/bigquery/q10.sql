WITH images AS (
  SELECT
    images.*,
    productDisplayName AS title,
    productDescriptors.description.value AS descr
  FROM fashion_product_images.STYLES_DETAILS styles_details
  JOIN fashion_product_images.IMAGE_MAPPING mapping
    ON styles_details.styleImages.default.imageURL = mapping.link
  JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
    ON ARRAY_LAST(SPLIT(images.uri, '/')) = mapping.filename
  WHERE true
    -- Pre-filtering for simple colors
    AND styles_details.baseColour IN ('Black', 'Blue', 'Red', 'White')
    AND price <= 1000
)
SELECT
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images1.uri, '/')), '.')) || '-' ||
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images2.uri, '/')), '.')) || '-' ||
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images3.uri, '/')), '.')) AS id
FROM
  images as images1,
  images as images2,
  images as images3
WHERE true
  -- Filters
  AND AI.IF(('The image depicts a (pair of) shoe(s), sandal(s), flip-flop(s). If there are multiple products in the picture, always refer to the most promiment one.', images1.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('The image depicts a piece of apparel that can be worn on the lower part of the body, like pants, shorts, skirts, ... If there are multiple products in the picture, always refer to the most promiment one.', images2.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('The image depicts a piece of apparel that can be worn on the upper part of the body, like t-shirts, shirts, pullovers, hoodies, but still require some sort of clothing on the lower body, which means, e.g., not a dress. If there are multiple products in the picture, always refer to the most promiment one.', images3.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  -- Join conditions
  AND AI.IF(('The images depict products with the same primary base color, e.g., both are black, both are white, and both products are from the same brand. The description of the first product is ', images1.title, ' ', images1.descr, ' and the image of the first product is ', images1.ref, ' The description of the second product is ', images2.title, ' ', images2.descr, ' and the image of the second product is ', images2.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('The images depict products with the same primary base color, e.g., both are black, both are white, and both products are from the same brand. The description of the first product is ', images2.title, ' ', images2.descr, ' and the image of the first product is ', images2.ref, ' The description of the second product is ', images3.title, ' ', images3.descr, ' and the image of the second product is ', images3.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
;
