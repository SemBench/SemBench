"""
Created on July 22, 2025

@author: Jiale Lao

LOTUS system runner implementation for animals use case.
Implements Q1, Q3, Q7, Q10 (image-only queries since LOTUS cannot process audio).
"""

import pandas as pd
from lotus.dtype_extensions import ImageArray
from pathlib import Path

# Add parent directory to path for imports
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from runner.generic_lotus_runner.generic_lotus_runner import GenericLotusRunner


class LotusRunner(GenericLotusRunner):
    """Runner for LOTUS system for animals use case."""

    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str = "gemini-2.5-flash",
        concurrent_llm_worker=20,
        skip_setup: bool = False,
    ):
        """
        Initialize LOTUS runner for animals.

        Args:
            use_case: The use case to run (should be 'animals')
            model_name: LLM model to use
        """
        super().__init__(
            use_case,
            scale_factor,
            model_name,
            concurrent_llm_worker,
            skip_setup=skip_setup,
        )

    def _execute_q1(self) -> pd.DataFrame:
        """
        Execute Q1: Count the number of pictures of zebras.

        This uses semantic filtering to identify zebra images and counts them.

        Returns:
            DataFrame with columns: count(*)
        """
        # 1. Load the image data
        image_data_df = self.load_data("image_data.csv")

        # 2. Wrap the image path column in ImageArray
        image_data_df.loc[:, "Image"] = ImageArray(image_data_df["ImagePath"])

        # 3. Perform semantic filtering to identify zebra images
        filter_instruction = "The image {Image} contains a zebra."
        zebra_images = image_data_df.sem_filter(filter_instruction)

        # 4. Count the number of zebra images
        count = len(zebra_images)

        # 5. Return result in standardized format
        result = pd.DataFrame([{"count(*)": count}])

        return result

    def _execute_q3(self) -> pd.DataFrame:
        """
        Execute Q3: Find the city where we captured most pictures of zebras.

        Returns:
            DataFrame with columns: city
        """
        # 1. Load the image data
        image_data_df = self.load_data("image_data.csv")

        # 2. Wrap the image path column in ImageArray
        image_data_df.loc[:, "Image"] = ImageArray(image_data_df["ImagePath"])

        # 3. Perform semantic filtering to identify zebra images
        filter_instruction = "The image {Image} contains a zebra."
        zebra_images = image_data_df.sem_filter(filter_instruction)

        # 4. Group by city and count, then get the city with most zebras
        if len(zebra_images) == 0:
            # If no zebras found, return empty result
            result = pd.DataFrame(columns=["city"])
        else:
            city_counts = (
                zebra_images.groupby("City").size().reset_index(name="count")
            )
            city_counts = city_counts.sort_values("count", ascending=False)

            # Get the city with most zebra pictures (ties broken arbitrarily by taking first)
            top_city = city_counts.iloc[0]["City"]
            result = pd.DataFrame([{"city": top_city}])

        return result

    def _execute_q7(self) -> pd.DataFrame:
        """
        Execute Q7: Find cities where zebras and impalas co-occur in images.

        Returns:
            DataFrame with columns: city
        """
        # 1. Load the image data
        image_data_df = self.load_data("image_data.csv")

        # 2. Wrap the image path column in ImageArray
        image_data_df.loc[:, "Image"] = ImageArray(image_data_df["ImagePath"])

        # 3. Perform semantic filtering to identify zebra images
        zebra_filter = "The image {Image} contains a zebra."
        zebra_images = image_data_df.sem_filter(zebra_filter)

        # 4. Perform semantic filtering to identify impala images
        # Reset image data for second filter
        image_data_df.loc[:, "Image"] = ImageArray(image_data_df["ImagePath"])

        impala_filter = "The image {Image} contains an impala."
        impala_images = image_data_df.sem_filter(impala_filter)

        # 5. Find intersection of cities with zebras and cities with impalas
        zebra_cities = (
            set(zebra_images["City"]) if len(zebra_images) > 0 else set()
        )
        impala_cities = (
            set(impala_images["City"]) if len(impala_images) > 0 else set()
        )

        cooccur_cities = zebra_cities.intersection(impala_cities)

        # 6. Return result
        if cooccur_cities:
            result = pd.DataFrame(
                [{"city": city} for city in sorted(cooccur_cities)]
            )
        else:
            result = pd.DataFrame(columns=["city"])

        return result

    def _execute_q10(self) -> pd.DataFrame:
        """
        Execute Q10: Find the city and station with most associated pictures showing zebras.

        Returns:
            DataFrame with columns: city, stationID
        """
        # 1. Load the image data
        image_data_df = self.load_data("image_data.csv")

        # 2. Wrap the image path column in ImageArray
        image_data_df.loc[:, "Image"] = ImageArray(image_data_df["ImagePath"])

        # 3. Perform semantic filtering to identify zebra images
        filter_instruction = "The image {Image} contains a zebra."
        zebra_images = image_data_df.sem_filter(filter_instruction)

        # 4. Group by city and station, count, then get the pair with most zebras
        if len(zebra_images) == 0:
            # If no zebras found, return empty result
            result = pd.DataFrame(columns=["city", "stationID"])
        else:
            station_counts = (
                zebra_images.groupby(["City", "StationID"])
                .size()
                .reset_index(name="count")
            )
            station_counts = station_counts.sort_values(
                "count", ascending=False
            )

            # Get the city/station pair with most zebra pictures (ties broken arbitrarily)
            top_row = station_counts.iloc[0]
            result = pd.DataFrame(
                [{"city": top_row["City"], "stationID": top_row["StationID"]}]
            )

        return result

    def _get_empty_results_dataframe(self, query_id: int) -> pd.DataFrame:
        """
        Get empty DataFrame with correct columns for a query.

        Args:
            query_id: ID of the query

        Returns:
            Empty DataFrame with correct columns
        """
        if query_id == 1:
            return pd.DataFrame(columns=["count(*)"])
        elif query_id == 3:
            return pd.DataFrame(columns=["city"])
        elif query_id == 7:
            return pd.DataFrame(columns=["city"])
        elif query_id == 10:
            return pd.DataFrame(columns=["city", "stationID"])
        else:
            return pd.DataFrame()
