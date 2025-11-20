SELECT styles_details.id
FROM fashion_product_images.STYLES_DETAILS
JOIN fashion_product_images.IMAGE_MAPPING
  ON image_mapping.link = styles_details.styleImages.default.imageURL
JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
  ON ARRAY_LAST(SPLIT(images.uri, '/')) = image_mapping.filename
WHERE true
  AND AI.IF(('''
    You will receive a description of what a customer is looking for together with an image and a textual description of the product.
    Determine if they both match.
    
    I am looking for a running shirt for men with a round neck and short sleeves,
    preferably in blue or black, but not bright colors like white.
    Also definitely not green.
    It should be suitable for outdoor running in warm weather.
    If the t-shirt is not green, it should at least feature a striped design.

    The product has the following image''',
    images.ref, ' and textual description ',
    styles_details.productDisplayName, ' ',
    styles_details.productDescriptors.description.value
  ),
  connection_id => '<<connection>>',
  model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>)
;
