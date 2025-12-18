# Car Scenario

*Data Modalities: text, images, audio, and tables.*

## Overview

This scenario simulates a comprehensive car diagnostics dataset that contains information about vehicles, including their specifications, reported issues, and diagnostic data. The diagnostic component includes three possible modalities per car: audio recordings of engine/brake sounds (audio), images showing vehicle damage or condition (images), and text complaints describing issues (text). Each car may have data in up to three of these modalities.

In some cases, multiple modalities reflect the same underlying problem (e.g., brake issues detected in both audio recordings and complaint text), whereas in others, they may indicate distinct issues or co-occurring conditions. This scenario explores questions concerning the presence and co-occurrence of vehicle problems that are identifiable through multimodal data—specifically images, audio, and text—using language models for analysis and inference.

## Schema

The schema has four tables:
```
Car(car_id, year, mileage, fuel_type, transmission, vin, registration_date, country, number_plate, previous_owners)
CarImage(car_id, image_id, image_path, damage_status)
CarAudio(car_id, audio_id, audio_path, generic_problem, detailed_problem)
CarComplaint(car_id, complaint_id, summary, component_class, crash, fire, numberOfInjuries)
```

The ground truth and corresponding labels are provided in the denormalized file `files/cars/data/full_data/car_data_denormalized.csv`.
This file is not designed for multimodal data processing; instead, it serves to simplify ground truth generation through conventional SQL queries.

The `Car` table stores vehicle specifications and background information, including `year` (manufacturing year), `mileage` (odometer reading), `fuel_type` (Gasoline/Diesel/Hybrid/Electric/Plug-in Hybrid), `transmission` (Automatic/Manual/CVT), `vin` (Vehicle Identification Number), `registration_date`, `country` (country of registration), `number_plate` (license plate), and `previous_owners` (number of previous owners). Cars have 0, 1, 2, or 3 modalities assigned, with each modality potentially indicating different issues or a healthy state.

The `CarImage` table contains paths to vehicle images (`image_path`), each image has an `image_id` and is assigned to a car with `car_id`. The `damage_status` field indicates the type of damage visible (e.g., "no_damage", "dented", "paint_scratches", "broken_glass", or combinations separated by semicolons). Each image is assigned to only one car.

The `CarAudio` table contains paths to audio files (`audio_path`) that record engine sounds, brake sounds, or other vehicle diagnostics. Each audio has an `audio_id` and belongs to a car (`car_id`). The `generic_problem` field indicates the problem category (e.g., "startup state", "idle state", "braking state"), and `detailed_problem` provides more specific information (e.g., "normal_engine_startup", "bad_ignition", "worn_out_brakes"). Each audio file is assigned to only one car.

The `CarComplaint` table contains text complaints (`summary`) describing vehicle issues reported by owners. Each complaint has a `complaint_id` and belongs to a car (`car_id`). The `component_class` field categorizes the issue (e.g., "ENGINE", "SERVICE BRAKES", "STEERING", "ELECTRICAL SYSTEM"). Additional fields include `crash` (boolean indicating if a crash was involved), `fire` (boolean indicating if fire was involved), and `numberOfInjuries` (count of injuries). Each complaint is assigned to only one car.

## Queries

- Find cars that were in a crash/accident/collision.

- Find cars with available audio recordings that show a dead battery.

- Find ten cars that are damaged according to images.

- How many 'Automatic' transmission cars are damaged according to audio and images?

- Find cars that are damaged according to one modality but not the other. For this query, for complaints, check if the car was on fire.

- Find cars that are either dented (image), have worn out brakes (audio), or have electrical system problems (text). They should be damaged at least according to a single modality.

- Find a hundred cars with punctures and paint scratches on images.

- Find cars that are torn according to images and have bad ignition according to audio.

- For all complaints, generate a component category from a given list of component classes.
