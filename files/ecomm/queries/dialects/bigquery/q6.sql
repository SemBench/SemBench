WITH product_selection AS (
  SELECT images.*
  FROM fashion_product_images.STYLES_DETAILS styles_details
  JOIN fashion_product_images.IMAGE_MAPPING mapping
    ON styles_details.styleImages.default.imageURL = mapping.link
  JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
    ON ARRAY_LAST(SPLIT(images.uri, '/')) = mapping.filename
  WHERE true
    AND masterCategory.typeName = 'Apparel'
    -- Exclude difficult categories:
    AND subCategory.typeName NOT IN ('Saree', 'Apparel Set', 'Loungewear and Nightwear')
)
SELECT
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(images.uri, '/')), '.')) AS id,
  -- AI.CLASSIFY is not implemented yet. Use AI.GENERATE instead.
  AI.GENERATE(
    ('''
     You are given an image of a product. Your task is to classify the product
     into one of the following categories: 
      (1) Dress: A dress is a one-piece outer garment that is worn on the torso, hangs down
                 over the legs, and often consist of a bodice attached to a skirt.
      (2) Bottomwear: Bottomwear refers to clothing worn on the lower part of the body,
                 such as trousers, jeans, skirts, shorts, and leggings.
      (3) Socks: Socks are a type of clothing worn on the feet, typically made of soft fabric,
                 designed to provide comfort and warmth.
      (4) Topwear: Topwear refers to clothing worn on the upper part of the body,
                 such as shirts, blouses, t-shirts, and jackets.
      (5) Innerwear: Innerwear refers to clothing worn beneath outer garments,
                 typically close to the skin, such as underwear, bras, and undershirts.
     When classifying the product, only output the category name, nothing more.
     ''', images.ref),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  ).result AS category
FROM product_selection images
;