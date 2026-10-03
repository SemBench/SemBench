"""
Created on Aug 8, 2025

@author: Jiale Lao

ThalamusDB runner implementation for animals use case.
"""

import os
from typing import Dict, Any
from pathlib import Path
import duckdb
import pandas as pd

# if you use local thalamusdb codes, please uncomment the following codes
# import sys

# sys.path.append(str(Path(__file__).parent.parent.parent.parent))
# tdb_path = str(
#     Path(__file__).parent.parent.parent.parent.parent
#     / "runner"
#     / "generic_thalamusdb_runner"
# )
# sys.path.insert(0, tdb_path)
# end of local codes version

from runner.generic_thalamusdb_runner.generic_thalamusdb_runner import (
    GenericThalamusDBRunner,
)


class ThalamusDBRunner(GenericThalamusDBRunner):
    """ThalamusDB runner for animals use case."""

    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str = "gemini-2.5-flash",
        concurrent_llm_worker: int = 1,
        skip_setup: bool = False,
    ):
        """
        Initialize ThalamusDB runner for animals case.

        Args:
            use_case: The use case to run
            model_name: LLM model to use
            concurrent_llm_worker: Number of concurrent workers
        """
        # Set database path to animals database
        db_name = "animals_database.duckdb"
        db_folder = (
            Path(__file__).resolve().parents[5] / "files" / use_case / "data" / f"sf_{scale_factor}"
        )
        db_path = db_folder / db_name

        if not os.path.exists(db_path):
            # Step 1: Read CSVs
            image_data_df = pd.read_csv(f"{db_folder}/image_data.csv")
            audio_data_df = pd.read_csv(f"{db_folder}/audio_data.csv")

            # Step 2: Connect to a persistent DuckDB file
            conn = duckdb.connect(
                db_path
            )  # Creates the file if it doesn't exist

            # Step 3: Save DataFrames as persistent tables
            # Create ImageData table with columns: image, city, stationID
            # Note: Species column is not visible to ThalamusDB
            image_df_visible = image_data_df[
                ["ImagePath", "City", "StationID"]
            ].rename(
                columns={
                    "ImagePath": "image",
                    "City": "city",
                    "StationID": "stationID",
                }
            )

            # Create AudioData table with columns: audio, city, stationID
            # Note: Animal column is not visible to ThalamusDB
            audio_df_visible = audio_data_df[
                ["AudioPath", "City", "StationID"]
            ].rename(
                columns={
                    "AudioPath": "audio",
                    "City": "city",
                    "StationID": "stationID",
                }
            )

            conn.register("image_df_visible", image_df_visible)
            conn.register("audio_df_visible", audio_df_visible)

            conn.execute(
                "CREATE TABLE ImageData AS SELECT * FROM image_df_visible"
            )
            conn.execute(
                "CREATE TABLE AudioData AS SELECT * FROM audio_df_visible"
            )

        super().__init__(
            use_case,
            scale_factor,
            model_name,
            concurrent_llm_worker,
            db_path,
            skip_setup=skip_setup,
        )

    def _execute_q1(self) -> Dict[str, Any]:
        """
        Q1: How many pictures of zebras do we have in our database?
        Ground truth: select count(*) from ImageData where Species LIKE '%ZEBRA%';
        """
        sql_query = """
        select count(*) as count
        from ImageData 
        where NLfilter(image, 'the image contains a zebra')
        """

        return self.execute_thalamusdb_query(sql_query)

    def _execute_q2(self) -> Dict[str, Any]:
        """
        Q2: How many sound recordings of elephants do we have in our database?
        Ground truth: select count(*) from AudioData where Animal = 'Elephant';
        """
        sql_query = """
        select count(*) as count
        from AudioData 
        where NLfilter(audio, 'the audio contains elephant sounds')
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q3(self) -> Dict[str, Any]:
        """
        Q3: What is the city where we captured most pictures of zebras?
        Ground truth: select city from ImageData where Species LIKE '%ZEBRA%' group by city order by count(*) desc limit 1;
        """
        sql_query = """
        select city
        from ImageData 
        where NLfilter(image, 'the image contains a zebra')
        group by city 
        order by count(*) desc 
        limit 1
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q4(self) -> Dict[str, Any]:
        """
        Q4: What is the city for which we have most recordings of elephants?
        Ground truth: select city from AudioData where Animal = 'Elephant' group by city order by count(*) desc limit 1;
        """
        sql_query = """
        select city
        from AudioData 
        where NLfilter(audio, 'the audio contains elephant sounds')
        group by city 
        order by count(*) desc 
        limit 1
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q5(self) -> Dict[str, Any]:
        """
        Q5: What is the list of cities for which we have either images or audio recordings of elephants?
        Ground truth: select distinct city from (select city from ImageData where Species LIKE '%ELEPHANT%') UNION (select city from AudioData where Animal = 'Elephant');
        """
        sql_query = """
        select distinct city from (
            select city from ImageData where NLfilter(image, 'the image contains an elephant')
            UNION 
            select city from AudioData where NLfilter(audio, 'the audio contains elephant sounds')
        )
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q6(self) -> Dict[str, Any]:
        """
        Q6: For which cities do we have images of monkeys but no audio recordings of monkeys?
        Ground truth: select distinct city from ImageData I where Species LIKE '%MONKEY%' and not exists (select * from AudioData A where A.city = I.city and A.animal = 'Monkey');
        """
        sql_query = """
        select distinct city 
        from ImageData I 
        where NLfilter(I.image, 'the image contains a monkey')
        and not exists (
            select * from AudioData A 
            where A.city = I.city 
            and NLfilter(A.audio, 'the audio contains monkey sounds')
        )
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q7(self) -> Dict[str, Any]:
        """
        Q7: What are the cities for which zebras and impala co-occur?
        Ground truth: select city from (select city from ImageData where Species LIKE '%ZEBRA%') INTERSECT (select city from ImageData where Species LIKE '%IMPALA%');
        """
        sql_query = """
        select city from (
            select city from ImageData where NLfilter(image, 'the image contains a zebra')
        ) INTERSECT (
            select city from ImageData where NLfilter(image, 'the image contains an impala')
        )
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q8(self) -> Dict[str, Any]:
        """
        Q8: What is the list of cities for which we found at least one image or audio recording of elephants and at least one image or audio recording of monkeys?
        Ground truth: select city from ((select city from ImageData where Species LIKE '%ELEPHANT%') UNION (select city from AudioData where Animal = 'Elephant'))  INTERSECT ((select city from ImageData where Species LIKE '%MONKEY%') UNION (select city from AudioData where Animal = 'Monkey'));
        """
        sql_query = """
        select city from (
            (select city from ImageData where NLfilter(image, 'the image contains an elephant'))
            UNION 
            (select city from AudioData where NLfilter(audio, 'the audio contains elephant sounds'))
        ) INTERSECT (
            (select city from ImageData where NLfilter(image, 'the image contains a monkey'))
            UNION 
            (select city from AudioData where NLfilter(audio, 'the audio contains monkey sounds'))
        )
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q9(self) -> Dict[str, Any]:
        """
        Q9: What is the list of cities for which we have both images and audio recordings of monkeys?
        Ground truth: select distinct city from (select city from ImageData where Species LIKE '%MONKEY%') INTERSECT (select city from AudioData where Animal = 'Monkey');
        """
        sql_query = """
        select distinct city from (
            select city from ImageData where NLfilter(image, 'the image contains a monkey')
        ) intersect (
            select city from AudioData where NLfilter(audio, 'the audio contains monkey sounds')
        )
        """
        return self.execute_thalamusdb_query(sql_query)

    def _execute_q10(self) -> Dict[str, Any]:
        """
        Q10: What is the city and station with most associated pictures showing zebras?
        Ground truth: select city, stationID from ImageData where Species LIKE '%ZEBRA%'  group by city, stationID order by count(*) DESC limit 1;
        """
        sql_query = """
        select city, stationID 
        from ImageData 
        where NLfilter(image, 'the image contains a zebra')
        group by city, stationID 
        order by count(*) desc 
        limit 1
        """
        return self.execute_thalamusdb_query(sql_query)
