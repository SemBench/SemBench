WITH product_selection AS (
  SELECT *
  FROM fashion_product_images.STYLES_DETAILS styles_details
  WHERE true
    AND price <= 500
)
SELECT
  p1.id || '-' || p2.id AS id
FROM product_selection p1
JOIN product_selection p2
  ON AI.IF(('''
     You will be given two product descriptions. Do both product descriptions describe products of the same category from the same brand, e.g., both are t-shirts from Adidas?
     
     The first product description is:
     ''', p1.productDisplayName, ' - ', p1.productDescriptors.description.value,
     '''
     The second product description is:
     ''', p2.productDisplayName, ' - ', p2.productDescriptors.description.value
     ),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  )
;
