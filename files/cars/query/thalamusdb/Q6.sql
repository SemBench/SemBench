WITH sick_audio AS (
    SELECT car_id
    FROM two_more_modalities
    WHERE audio_id IS NOT NULL
    AND NLfilter(audio_path, 'You are given an audio recording of car diagnostics. Return true if the recording captures an audio of a damaged car.')
),
sick_image AS (
    SELECT car_id
    FROM two_more_modalities
    WHERE image_id IS NOT NULL
    AND NLfilter(image_path, 'You are given an image of a vehicle or its parts. Return true if car is damaged.')
),
sick_text AS (
    SELECT car_id
    FROM two_more_modalities
    WHERE complaint_id IS NOT NULL
    AND NLfilter(summary, 'You are be given a textual complaint entailing that the car was in on fire or burned. Complaint: {summary}.')
)
SELECT * FROM (
    SELECT
        t.car_id,
        t.year,
        t.complaint_id,
        t.image_id,
        t.audio_id,
        CASE WHEN a.car_id IS NOT NULL THEN 1 WHEN t.audio_id IS NOT NULL THEN 0 ELSE NULL END AS is_sick_audio,
        CASE WHEN s.car_id IS NOT NULL THEN 1 WHEN t.complaint_id IS NOT NULL THEN 0 ELSE NULL END AS is_sick_text,
        CASE WHEN x.car_id IS NOT NULL THEN 1 WHEN t.image_id IS NOT NULL THEN 0 ELSE NULL END AS is_sick_image
    FROM two_more_modalities t
    LEFT JOIN sick_audio a ON t.car_id = a.car_id
    LEFT JOIN sick_text s ON t.car_id = s.car_id
    LEFT JOIN sick_image x ON t.car_id = x.car_id
)
WHERE (is_sick_audio = 1 OR is_sick_text = 1 OR is_sick_image = 1)
AND (is_sick_audio = 0 OR is_sick_text = 0 OR is_sick_image = 0)
