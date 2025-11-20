SELECT 
  AI.GENERATE(
    ('''
    You are given a product description and an image of the product as well as the product id.
    The product contains a fashion item (clothing, shoes, accessories, etc).
    There might be multiple fashion items in the image, especially when a model is presenting them.
    If this is the case, focus only on the primary fashion item and use the description to determine which item in the image is of interest.

    For each product, generate the following JSON:
    ```
    {
        "id": <product id> (integer),
        "brand": <extract the brand name from the description and/or image. use lower-case letters for the brand name>",
        "category": <classify the images into ''accessories'', ''apparel'', ''footwear''>
    }
    ```

    Output the json in a single line.
    Keep the order of the keys in the JSON as given in the description.
    Do not use spaces between { or keys and values in the JSON, i.e., do no use spaces anywhere in the JSON structure.
    Use normal quotes in the JSON; do not use single quotes.

    The id, description and the image are as follows:
    ''',
    CAST(styles_details.id AS STRING), ' ',
    styles_details.productDisplayName, ' ',
    styles_details.productDescriptors.description.value, ' ',
    images.ref),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  ).result AS id
FROM fashion_product_images.STYLES_DETAILS
JOIN fashion_product_images.IMAGE_MAPPING
  ON image_mapping.link = styles_details.styleImages.default.imageURL
JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
  ON ARRAY_LAST(SPLIT(images.uri, '/')) = image_mapping.filename
WHERE true
  AND styles_details.masterCategory.typeName in ('Accessories', 'Apparel', 'Footwear')
  AND AI.IF(('Does the following description describe a product from either Adidas or Puma?',
    styles_details.productDisplayName, ' ',
    styles_details.productDescriptors.description.value
  ),
  connection_id => '<<connection>>',
  model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
;
