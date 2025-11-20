SELECT
  id, AI.GENERATE(
    ('Extract the brand name from the following product description. Only return the brand name, nothing else: ',
    styles_details.productDisplayName, ' ',
    styles_details.productDescriptors.description.value),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  ).result AS category
FROM fashion_product_images.STYLES_DETAILS;
