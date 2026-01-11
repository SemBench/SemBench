from operator import itemgetter
import os
import pandas as pd
from lotus.dtype_extensions import ImageArray


def run(data_dir: str):
    # Configure LOTUS for image-only join if approximate policy is enabled
    if '_configure_lotus' in globals() and '_policy' in globals() and globals()['_policy'] == 'approximate':
        globals()['_configure_lotus']('image')

    # Load data
    styles_details = pd.read_parquet(
        os.path.join(data_dir, "styles_details.parquet")
    )
    image_mapping = pd.read_parquet(
        os.path.join(data_dir, "image_mapping.parquet")
    )

    # Pre-filter data
    styles_details = styles_details[
        styles_details["baseColour"].isin(
            ["Black", "Blue", "Red", "White", "Orange", "Green"]
        )
        & (styles_details["colour1"] == "")
        & (styles_details["colour2"] == "")
        & (styles_details["price"] < 800)
    ]
    image_mapping = image_mapping[
        image_mapping["id"].astype("int").isin(styles_details["id"])
    ]
    image_mapping["images"] = ImageArray(
        image_mapping.filename.apply(
            lambda s: os.path.join(data_dir, "images", s)
        )
    )

    # Reset index for approximate policy
    # if '_policy' in globals() and globals()['_policy'] == 'approximate':
    #     image_mapping = image_mapping.reset_index(drop=True)

    # Self-join
    join_instruction = """
     Determine whether both images display objects of the same category
     (e.g., both are shoes, both are bags, etc.) and whether these objects
     share the same dominant surface color. Disregard any logos, text, or
     printed graphics on the objects. There might be other objects in the
     images. Only focus on the main object. Base your comparison solely on
     object type and overall surface color: {images:left} {images:right}
    """

    # if '_cascade_args' in globals() and '_policy' in globals() and globals()['_policy'] == 'approximate':
    #     processed = image_mapping.sem_join(
    #         image_mapping,
    #         join_instruction,
    #         cascade_args=globals()['_cascade_args']
    #     )
    # else:
    #     processed = image_mapping.sem_join(image_mapping, join_instruction)
        
    processed = image_mapping.sem_join(image_mapping, join_instruction)

    # Remove identical join partners
    processed = processed[processed["id:left"] != processed["id:right"]]

    processed["id"] = (
        processed["id:left"].astype("str")
        + "-"
        + processed["id:right"].astype("str")
    )
    return processed["id"]
