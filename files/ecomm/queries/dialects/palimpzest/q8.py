import os
import pandas as pd
import palimpzest as pz


def run(pz_config, data_dir: str):
    # Load data
    styles_details = pd.read_parquet(
        os.path.join(data_dir, "styles_details.parquet")
    ).rename(
        columns={"id": "prod_id"}
    )  # prevent naming conflict with internal Palimpzest 'id' column
    images = pz.ImageFileDataset(
        id="images", path=os.path.join(data_dir, "images")
    )

    # Pre-filter data: Filter for long descriptions.
    # Then propagate this filter to 'images' based on the product id.
    images = images.add_columns(
        udf=lambda row: {"prod_id": row["filename"].split(".", 1)[0]},
        cols=[
            {
                "name": "prod_id",
                "type": str,
                "description": "Product id generated from image name",
            }
        ],
    )
    styles_details = styles_details[
        styles_details.apply(
            lambda row: (
                row["productDescriptors"].get("description") is not None and
                row["productDescriptors"]["description"].get("value") is not None and
                len(row["productDescriptors"]["description"]["value"]) >= 3000
            ),
            axis=1,
        )
    ]
    # images = images.filter(
    #     lambda row: int(row["prod_id"]) in styles_details["prod_id"].values
    # )

    styles_details_ds = pz.MemoryDataset(
        id="styles_details", vals=styles_details
    )

    # Join data: text-to-image join
    processed = styles_details_ds.sem_join(
        images,
        """
        The image fits the description
        """,
        depends_on=[
            "contents",
            "productDisplayName",
            "productDescriptors",
        ],
    )

    # Generate joined identifiers
    processed = processed.add_columns(
        udf=lambda row: {
            "product_id": str(row["prod_id"]) + "-" + str(row["prod_id_right"])
        },
        cols=[
            {"name": "product_id", "type": str, "description": "Combined ID"}
        ],
    )
    processed = processed.project(["product_id"])

    output = processed.run(pz_config)
    return output
