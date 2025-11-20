SELECT
  id
FROM fashion_product_images.STYLES_DETAILS
WHERE true
  AND AI.IF(
    ('The product is a backpack from Reebok: ',
     styles_details.productDisplayName, ' ',
     styles_details.productDescriptors.description.value),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  )
;
