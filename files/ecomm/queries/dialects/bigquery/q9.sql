WITH product_selection AS (
  SELECT images.*
  FROM fashion_product_images.STYLES_DETAILS styles_details
  JOIN fashion_product_images.IMAGE_MAPPING mapping
    ON styles_details.styleImages.default.imageURL = mapping.link
  JOIN EXTERNAL_OBJECT_TRANSFORM(TABLE `fashion_product_images.IMAGES`, ['SIGNED_URL']) as images
    ON ARRAY_LAST(SPLIT(images.uri, '/')) = mapping.filename
  WHERE true
    AND styles_details.baseColour IN ('Black', 'Blue', 'Red', 'White', 'Orange', 'Green')
    AND styles_details.colour1 = ''
    AND styles_details.colour2 = ''
    AND price < 800
)
SELECT
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(p1.uri, '/')), '.')) || '-' ||
  ARRAY_FIRST(SPLIT(ARRAY_LAST(SPLIT(p2.uri, '/')), '.')) AS id
FROM product_selection p1
LEFT OUTER JOIN product_selection p2
  ON p1.uri != p2.uri
  AND AI.IF(
    ('''
     Determine whether both images display objects of the same category
     (e.g., both are shoes, both are bags, etc.) and whether these objects
     share the same dominant surface color. Disregard any logos, text, or
     printed graphics on the objects. There might be other objects in the
     images. Only focus on the main object. Base your comparison solely on
     object type and overall surface color.''', p1.ref, p2.ref),
    connection_id => '<<connection>>',
    model_params => JSON '{"labels":{"query_uuid": "<<query_id>>"}, "generation_config": {"thinking_config": {"thinking_budget": <<thinking_budget>>}}}' <<other_params>>
  )
;
