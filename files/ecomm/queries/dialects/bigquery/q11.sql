WITH images AS (
  SELECT
    images.*,
    productDisplayName AS title,
    productDescriptors.description.value AS descr,
    price
  FROM fashion_product_images.STYLES_DETAILS styles_details
  JOIN fashion_product_images.IMAGE_MAPPING mapping
    ON styles_details.styleImages.default.imageURL = mapping.link
  JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
    ON ARRAY_LAST(SPLIT(images.uri, '/')) = mapping.filename
)
SELECT
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images1.uri, '/')), '.')) || '-' ||
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images2.uri, '/')), '.')) || '-' ||
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images3.uri, '/')), '.')) || '-' ||
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images4.uri, '/')), '.')) AS id
FROM
  images as images1,
  images as images2,
  images as images3,
  images as images4
WHERE true
  -- Filters
  AND images4.price <= 500
  AND AI.IF(('''
    You will receive an image and a description of a product.
    Determine whether the product can be worn on the feet, like shoes, sandals, flip-flops, ...
    The predominant color of the depicted product should be black.
    If there are multiple products in the picture, always refer to the most promiment one.
    The description of the product is as follows: ''',
    images1.title, ' ', images1.descr, ' ', images1.ref),
    connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('''
    You will receive an image and a description of a product.
    Determine whether the product can be worn on the lower part of the body, like pants, shorts, skirts, ...
    The predominant color of the depicted product should be black.
    Do not consider swimwear.
    If there are multiple products in the picture, always refer to the most promiment one.
    The description of the product is as follows: ''',
    images2.title, ' ', images2.descr, ' ', images2.ref),
    connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('''
    You will receive an image and a description of a product.
    Determine whether the product can be worn on the upper part of the body, like t-shirts, shirts, pullovers, hoodies, but still require some sort of clothing on the lower body, which means, e.g., not a dress.
    The predominant color of the depicted product should be black.
    Do not consider swimwear.
    If there are multiple products in the picture, always refer to the most promiment one.
    The description of the product is as follows: ''',
    images3.title, ' ', images3.descr, ' ', images3.ref),
    connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('''
    You will receive an image and a description of a product.
    Determine whether the product a watch or some jewellery or a bag.
    A bag might be a handbag or a (gym) backpack or some other type of bag.
    If there are multiple products in the picture, always refer to the most promiment one.
    The description of the product is as follows: ''',
    images4.title, ' ', images4.descr, ' ', images4.ref),
    connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  -- Join conditions
  AND AI.IF(('You will receive and image and the description of two products. Determine whether they are from the same brand. The description of the first product is as follows: ', images1.title, ' ', images1.descr, ' And the image of the first product is ', images1.ref, 'The description of the second product is as follows: ', images2.title, ' ', images2.descr, ' And the image of the second product is ', images2.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('You will receive and image and the description of two products. Determine whether they are from the same brand. The description of the first product is as follows: ', images2.title, ' ', images2.descr, ' And the image of the first product is ', images2.ref, 'The description of the second product is as follows: ', images3.title, ' ', images3.descr, ' And the image of the second product is ', images3.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
  AND AI.IF(('You will receive and image and the description of two products. Determine whether they are from the same brand. The description of the first product is as follows: ', images3.title, ' ', images3.descr, ' And the image of the first product is ', images3.ref, 'The description of the second product is as follows: ', images4.title, ' ', images4.descr, ' And the image of the second product is ', images4.ref), connection_id => '<<connection>>', model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
;
