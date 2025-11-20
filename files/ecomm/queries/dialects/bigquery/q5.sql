WITH product_selection AS (
  SELECT *
  FROM fashion_product_images.STYLES_DETAILS styles_details
  WHERE true
    AND masterCategory.typeName = 'Apparel'
    -- Exclude difficult categories:
    AND subCategory.typeName NOT IN ('Saree', 'Apparel Set', 'Loungewear and Nightwear')
)
SELECT
  id,
  -- AI.CLASSIFY is not implemented yet. Use AI.GENERATE instead.
  AI.GENERATE(
    ('''
     You are given a description of a product. Your task is to classify the product
     into one of the following categories: 
      (1) Dress: A dress is a one-piece outer garment that is worn on the torso, hangs down
                 over the legs, and often consist of a bodice attached to a skirt.
      (2) Bottomwear: Bottomwear refers to clothing worn on the lower part of the body,
                 such as trousers, jeans, skirts, shorts, and leggings.
      (3) Socks: Socks are a type of clothing worn on the feet, typically made of soft fabric,
                 designed to provide comfort and warmth.
      (4) Topwear: Topwear refers to clothing worn on the upper part of the body,
                 such as shirts, blouses, t-shirts, and jackets
      (5) Innerwear: Innerwear refers to clothing worn beneath outer garments,
                 typically close to the skin, such as underwear, bras, and undershirts.
     When classifying the product, only output the category name, nothing more.

     The product description is as follows:
     ''', styles_details.productDisplayName, ' ', styles_details.productDescriptors.description.value),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  ).result AS category
FROM product_selection styles_details
;