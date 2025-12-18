"""
Created on Jun 28, 2025

@author: OlgaOvcharenko
"""

from pathlib import Path
from typing import Any, Dict
import sys
import pandas as pd
import numpy as np

from sklearn.metrics import precision_recall_fscore_support

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from evaluator.generic_evaluator import (
    GenericEvaluator,
    QueryMetricRetrieval,
    QueryMetricAggregation,
)


class CarsEvaluator(GenericEvaluator):
    """Evaluator for the cars benchmark using the reusable framework."""

    def __init__(self, use_case: str, scale_factor: int = None) -> None:
        super().__init__(use_case, scale_factor)

    def _load_domain_data(self) -> None:
        #  Read full data w/ labels
        full_data_path = self._root / "data" / "full_data"
        cars_df = pd.read_csv(full_data_path / f"car_data_full.csv")
        audio_df = pd.read_csv(full_data_path / f"audio_data_full.csv")
        image_df = pd.read_csv(full_data_path / f"image_data_full.csv")
        text_df = pd.read_csv(full_data_path / f"text_complaints_data_full.csv")

        if self.scale_factor != 157376:
            #  Read sample data w/o labels
            data_path = self._root / "data" / f"sf_{int(self.scale_factor)}"
            cars_sample_df = pd.read_csv(data_path / f"car_data_{int(self.scale_factor)}.csv")
            audio_sample_df = pd.read_csv(data_path / f"audio_data_{int(self.scale_factor)}.csv")
            image_sample_df = pd.read_csv(data_path / f"image_data_{int(self.scale_factor)}.csv")
            text_sample_df = pd.read_csv(data_path / f"text_complaints_data_{int(self.scale_factor)}.csv")

            cars_df = cars_df[ cars_df["car_id"].isin(cars_sample_df["car_id"])]
            audio_df = audio_df[audio_df["audio_id"].isin(audio_sample_df["audio_id"])]
            image_df = image_df[image_df["image_id"].isin(image_sample_df["image_id"])]
            text_df = text_df[text_df["complaint_id"].isin(text_sample_df["complaint_id"])]
        
        self.cars_df = cars_df
        self.audio_df = audio_df
        self.image_df = image_df
        self.text_df = text_df


    def _get_ground_truth(self, query_id: int) -> pd.DataFrame:
        query_name = f"Q{query_id}"
        gt_path = self._results_path / "ground_truth" / f"{query_name}_{f"{int(self.scale_factor)}"}.csv"
        if gt_path.exists():
            return pd.read_csv(gt_path)

        ground_truth_fn = self._discover_ground_truth_impl(query_id)
        return ground_truth_fn()

    def _generate_q1_ground_truth(self) -> pd.DataFrame:
        # crash,fire,numberOfInjuries,summary,component_class,complaint_id,car_id
        crash = self.text_df[self.text_df["crash"] == True]
        gt = crash["car_id"].drop_duplicates().copy()

        path = self._results_path / "ground_truth" / f"Q1_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        return gt

    def _generate_q2_ground_truth(self) -> pd.DataFrame:
        electric_cars = self.cars_df[self.cars_df["fuel_type"] == "Electric"]
        car_audio_df = self.audio_df[self.audio_df["car_id"].isin(electric_cars["car_id"])]
        dead_battery_audio = car_audio_df[(car_audio_df["generic_problem"] == "startup state") & (car_audio_df["detailed_problem"] == "dead_battery")]

        gt = dead_battery_audio["car_id"].drop_duplicates().copy()
        path = self._results_path / "ground_truth" / f"Q2_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        return gt

    def _generate_q3_ground_truth(self) -> pd.DataFrame:
        # 5 manual cars with no visual damages
        manual_cars = self.cars_df[self.cars_df["transmission"] == "Manual"]
        car_image_df = self.image_df[self.image_df["car_id"].isin(manual_cars["car_id"])]
        no_damaged_cars = car_image_df[car_image_df["damage_status"] == "no_damage"]
        manual_cars_with_no_damage = manual_cars[manual_cars["car_id"].isin(no_damaged_cars["car_id"])]
        gt = manual_cars_with_no_damage[["vin"]].reset_index(drop=True).copy()   

        path = self._results_path / "ground_truth" / f"Q3_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        return gt

    def _generate_q4_ground_truth(self) -> pd.DataFrame:
        # Average age of cars with engine problems

        all_engine_problems = self.text_df.loc[
            self.text_df["component_class"] == "ENGINE", "car_id"
        ]
        avg_age = 2026 - self.cars_df.loc[self.cars_df["car_id"].isin(all_engine_problems), "year"].mean()

        gt = pd.DataFrame({"average_age": [avg_age]})

        path = self._results_path / "ground_truth" / f"Q4_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        return gt

    def _generate_q5_ground_truth(self) -> pd.DataFrame:
        damaged_cars_image = self.image_df.loc[self.image_df["damage_status"] != "no_damage", "car_id"]
        damaged_cars_audio = self.audio_df.loc[~self.audio_df["detailed_problem"].str.startswith("normal_"), "car_id"]
        damaged_cars = self.cars_df.loc[self.cars_df["car_id"].isin(damaged_cars_image) & self.cars_df["car_id"].isin(damaged_cars_audio)]
        gt = damaged_cars.loc[damaged_cars["transmission"] == "Automatic", "transmission"].value_counts().to_frame()
        gt = gt.reset_index()

        path = self._results_path / "ground_truth" / f"Q5_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)

        return gt

    def _denormalize_data(self,
        car_table: pd.DataFrame,
        image_table: pd.DataFrame,
        audio_table: pd.DataFrame,
        complaints_table: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Denormalizes the normalized tables into a single table with all information.
        Creates a row for each unique combination of car + image + audio + complaint.
        If a car has multiple images, audio files, or complaints, multiple rows will be created.
        
        Args:
            car_table: DataFrame with car data (car_id as PK)
            image_table: DataFrame with image data (image_id, car_id, image_path, damage_status)
            audio_table: DataFrame with audio data (audio_id, car_id, audio_path, generic_problem, detailed_problem)
            complaints_table: DataFrame with complaint data (complaint_id, car_id, summary, component_class, crash, fire, numberOfInjuries)
            
        Returns:
            Single denormalized DataFrame with all car attributes and all modality information
        """
        # Start with car table
        denormalized = car_table.copy()
        
        # Merge with images (left join to keep all cars, even without images)
        if len(image_table) > 0:
            denormalized = denormalized.merge(
                image_table,
                on="car_id",
                how="left",
                suffixes=("", "_img")
            )
        else:
            # Add empty columns if no images
            denormalized["image_id"] = None
            denormalized["image_path"] = None
            denormalized["damage_status"] = None
        
        # Merge with audio (left join)
        if len(audio_table) > 0:
            denormalized = denormalized.merge(
                audio_table,
                on="car_id",
                how="left",
                suffixes=("", "_audio")
            )
        else:
            # Add empty columns if no audio
            denormalized["audio_id"] = None
            denormalized["audio_path"] = None
            denormalized["generic_problem"] = None
            denormalized["detailed_problem"] = None
        
        # Merge with complaints (left join)
        if len(complaints_table) > 0:
            denormalized = denormalized.merge(
                complaints_table,
                on="car_id",
                how="left",
                suffixes=("", "_complaint")
            )
        else:
            # Add empty columns if no complaints
            denormalized["complaint_id"] = None
            denormalized["summary"] = None
            denormalized["component_class"] = None
            denormalized["crash"] = None
            denormalized["fire"] = None
            denormalized["numberOfInjuries"] = None
        
        # Remove duplicate car_id column if it exists (from merges)
        if "car_id_img" in denormalized.columns:
            denormalized = denormalized.drop(columns=["car_id_img"])
        if "car_id_audio" in denormalized.columns:
            denormalized = denormalized.drop(columns=["car_id_audio"])
        if "car_id_complaint" in denormalized.columns:
            denormalized = denormalized.drop(columns=["car_id_complaint"])
        
        return denormalized

    def _generate_q6_ground_truth(self) -> pd.DataFrame:
        # Find cars that are damaged according one modality but not the other. For this query, for complaints, check if car was on fire.
        damaged_cars = self._denormalize_data(self.cars_df, self.image_df, self.audio_df, self.text_df)

        damaged_cars.to_csv("damaged_cars.csv", index=False)

        damaged_cars["detailed_problem"] = damaged_cars["detailed_problem"].apply(lambda x: "no_damage" if isinstance(x, str) and x.startswith("normal_") else ("None" if pd.isna(x) else "damaged"))

        damaged_cars["fire"] = damaged_cars["fire"].apply(lambda x: "no_damage" if x == False else ("None" if pd.isna(x) else "damaged"))

        damaged_cars["damage_status"] = damaged_cars["damage_status"].apply(lambda x: "no_damage" if x == "no_damage" else ("None" if pd.isna(x) else "damaged"))

        gt = damaged_cars[
            (
                damaged_cars["damage_status"]
                + ", "
                + damaged_cars["detailed_problem"]
                + ", "
                + damaged_cars["fire"]
            ).apply(
                lambda x: (x.split(", ").count("no_damage") > 0) & (x.split(", ").count("damaged") > 0)
            )
        ]

        path = self._results_path / "ground_truth" / f"Q6_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)

        return gt

    def _generate_q7_ground_truth(self) -> pd.DataFrame:
        # Find cars that are at least either dented (image), have worn out brakes (audio), or electrical system problems (text). They should be damaged at least according to a single modality.
        worn_out_brakes_cars = self.audio_df[self.audio_df["detailed_problem"] == "worn_out_brakes"]["car_id"]
        electrical_system_cars = self.text_df[self.text_df["component_class"] == "ELECTRICAL SYSTEM"]["car_id"]
        damaged_cars = self.image_df[self.image_df["damage_status"].str.contains("dented")]["car_id"]

        # Combine all Series and get unique car_ids
        all_car_ids = pd.concat([worn_out_brakes_cars, electrical_system_cars, damaged_cars]).drop_duplicates()
        gt = pd.DataFrame({"car_id": all_car_ids}).copy()

        path = self._results_path / "ground_truth" / f"Q7_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        
        return gt
    
    def _generate_q8_ground_truth(self) -> pd.DataFrame:
        gt = self.image_df.loc[self.image_df["damage_status"].apply(
                lambda x: ("paint_scratches" in x.split(";")) & ("puncture" in x.split(";"))
            ), ["car_id"]]
            

        path = self._results_path / "ground_truth" / f"Q8_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        return gt
    
    def _generate_q9_ground_truth(self) -> pd.DataFrame:
        # Torn car (image) and bad ignition (audio)
        torn = self.image_df.loc[self.image_df["damage_status"].apply(lambda x: ("torn" in x.split(";"))), ["car_id"]]
        bad_ignition = self.audio_df.loc[self.audio_df["detailed_problem"].str.contains("bad_ignition"), ["car_id"]]

        gt = torn[torn["car_id"].isin(bad_ignition["car_id"])].drop_duplicates()

        path = self._results_path / "ground_truth" / f"Q9_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        return gt
    
    def _generate_q10_ground_truth(self) -> pd.DataFrame:
        gt = self.cars_df.join(self.text_df.set_index('car_id'), on='car_id', how='inner')[['car_id', 'component_class']]
        gt["component_class"] = gt["component_class"].apply(lambda x: x.lower())
        gt.reset_index(inplace=True)
        gt.rename(columns={"component_class": "problem_category"}, inplace=True)

        path = self._results_path / "ground_truth" / f"Q10_{int(self.scale_factor)}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        gt.to_csv(path, index=False)
        
        return gt

    def _evaluate_single_query(
        self,
        query_id: int,
        system_results: pd.DataFrame,
        ground_truth: pd.DataFrame,
    ) -> "QueryMetricRetrieval | QueryMetricAggregation":
        evaluate_fn = self._discover_evaluate_impl(query_id)
        return evaluate_fn(system_results, ground_truth)

    def _evaluate_q1(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricRetrieval:
        system_results.columns = system_results.columns.str.lower()
        id_column = "car_id"

        precision = GenericEvaluator.compute_accuracy_score("precision", ground_truth, system_results, id_column=id_column).accuracy
        recall = GenericEvaluator.compute_accuracy_score("recall", ground_truth, system_results, id_column=id_column).accuracy
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)

    def _evaluate_q2(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricRetrieval:
        system_results.columns = system_results.columns.str.lower()
        id_column = "car_id"

        print(ground_truth)
        print(system_results)
        
        system_results.drop_duplicates(inplace=True)
        
        precision = GenericEvaluator.compute_accuracy_score("precision", ground_truth, system_results, id_column=id_column).accuracy
        recall = GenericEvaluator.compute_accuracy_score("recall", ground_truth, system_results, id_column=id_column).accuracy
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)
    
    def _evaluate_q3(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        id_column="vin"

        system_results.columns = system_results.columns.str.lower()

        print(f"Systems results sample for Q3: {system_results}")
        print(f"Ground truth sample for Q3: {ground_truth}")

        correct_ids_ix = ground_truth[id_column].isin(system_results[id_column].to_list())
        correct_ids = ground_truth.loc[correct_ids_ix,:]
        ground_truth_sample = None
        if correct_ids.empty:
            ground_truth_sample = ground_truth.sample(n=10, random_state=42)

        elif correct_ids.shape[0] > 10:
            raise "Ground truth for Q3 should not contain more than 10 rows. Query contains LIMIT 10."
        
        elif correct_ids.shape[0] < 10:
            ground_truth_sample = pd.concat([correct_ids, ground_truth[correct_ids_ix==False].sample(n=10-correct_ids.shape[0], random_state=42)])
            print(f"Smaller: {ground_truth_sample}")

        elif correct_ids.shape[0] == 10:
            ground_truth_sample = correct_ids
        print(f"Systems results sample for Q3: {system_results}")
        print(f"Ground truth sample for Q3: {ground_truth_sample}")
        
        precision = GenericEvaluator.compute_accuracy_score("precision", ground_truth_sample, system_results, id_column=id_column).accuracy
        recall = GenericEvaluator.compute_accuracy_score("recall", ground_truth_sample, system_results, id_column=id_column).accuracy
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)

    def _evaluate_q4(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        system_results.columns = system_results.columns.str.lower()
        return self._generic_aggregation_evaluation(system_results, ground_truth)

    def _evaluate_q5(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        system_results.columns = system_results.columns.str.lower()
        print(ground_truth)
        return self._generic_aggregation_evaluation(system_results, ground_truth)

    def _evaluate_q6(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        system_results.columns = system_results.columns.str.lower()
        id_column = "car_id"

        print(system_results)
        print(ground_truth)
        
        precision = GenericEvaluator.compute_accuracy_score("precision", ground_truth, system_results, id_column=id_column).accuracy
        recall = GenericEvaluator.compute_accuracy_score("recall", ground_truth, system_results, id_column=id_column).accuracy
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)
    
    def _evaluate_q7(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        system_results.columns = system_results.columns.str.lower()
        id_column = "car_id"

        print(system_results)
        print(ground_truth)
        
        precision = GenericEvaluator.compute_accuracy_score("precision", ground_truth, system_results, id_column=id_column).accuracy
        recall = GenericEvaluator.compute_accuracy_score("recall", ground_truth, system_results, id_column=id_column).accuracy
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)
    
    def _evaluate_q8(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        id_column="car_id"

        system_results.columns = system_results.columns.str.lower()

        print(f"Systems results sample for Q8: {system_results}")
        print(f"Ground truth sample for Q8: {ground_truth}")

        correct_ids_ix = ground_truth[id_column].isin(system_results[id_column].to_list())
        correct_ids = ground_truth.loc[correct_ids_ix,:]
        ground_truth_sample = None
        if correct_ids.empty:
            ground_truth_sample = ground_truth.sample(n=100, random_state=42)

        elif correct_ids.shape[0] > 100:
            raise "Ground truth for Q8 should not contain more than 100 rows. Query contains LIMIT 100."
        
        elif correct_ids.shape[0] < 100:
            ground_truth_sample = pd.concat([correct_ids, ground_truth[correct_ids_ix==False].sample(n=100-correct_ids.shape[0], random_state=42)])
            print(f"Smaller: {ground_truth_sample}")

        elif correct_ids.shape[0] == 100:
            ground_truth_sample = correct_ids
        print(f"Systems results sample for Q8: {system_results}")
        print(f"Ground truth sample for Q8: {ground_truth_sample}")

        precision = GenericEvaluator.compute_accuracy_score("precision", ground_truth_sample, system_results, id_column=id_column).accuracy
        recall = GenericEvaluator.compute_accuracy_score("recall", ground_truth_sample, system_results, id_column=id_column).accuracy
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)
    
    def _evaluate_q9(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        id_column="car_id"
        system_results.columns = system_results.columns.str.lower()
        print(system_results)
        print(ground_truth)

        precision = GenericEvaluator.compute_accuracy_score("precision", ground_truth, system_results, id_column=id_column).accuracy
        recall = GenericEvaluator.compute_accuracy_score("recall", ground_truth, system_results, id_column=id_column).accuracy
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)
    
    def _evaluate_q10(
        self, system_results: pd.DataFrame, ground_truth: pd.DataFrame
    ) -> QueryMetricAggregation:
        id_column = "car_id"
        result_column = "problem_category"

        system_results.columns = system_results.columns.str.lower()
        system_results["problem_category"] = system_results["problem_category"].apply(lambda x: str(x).lower().replace("\n", ""))

        gt = ground_truth.sort_values(id_column)[result_column]
        query = system_results.sort_values(id_column)[result_column]
        
        (precision, recall, f1, _) = precision_recall_fscore_support(gt, query, average="macro")
        return QueryMetricRetrieval(precision=precision, recall=recall, f1_score=f1)
