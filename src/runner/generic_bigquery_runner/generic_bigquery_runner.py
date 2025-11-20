"""
Generic BigQuery system runner implementation.

@Jiale update:
(1) cost calculation, including audio token, reasoning token.
(2) parameters for BigQuery SQL, including model specification and
thinking_budgets
"""

import os
import time
import uuid
from overrides import override
from typing import Dict, List

from google.cloud import bigquery
from jinja2 import Environment

from runner.generic_runner import GenericRunner, GenericQueryMetric

jinja_env = Environment(variable_start_string="<<", variable_end_string=">>")


class GenericBigQueryRunner(GenericRunner):
    """Runner for BigQuery."""

    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str = "gemini-2.5-flash",
        concurrent_llm_worker=20,
        skip_setup: bool = False,
        thinking_budget: int = 0,
    ):
        """
        Initialize BigQuery runner.

        Args:
            use_case: The use case to run
            model_name: LLM model to use
            thinking_budget: Budget for thinking tokens (default: 0)
        """
        super().__init__(
            use_case,
            scale_factor,
            model_name,
            concurrent_llm_worker,
            skip_setup,
        )
        self.thinking_budget = thinking_budget

        # Set up BigQuery client (assumes GOOGLE_APPLICATION_CREDENTIALS is set)
        self.bq_client = bigquery.Client(
            project=os.environ.get("GCLOUD_PROJECT")
        )

    @override
    def get_system_name(self) -> str:
        return "bigquery"

    @override
    def execute_queries(
        self, query_ids: List[int]
    ) -> Dict[int, GenericQueryMetric]:
        run_uuid = uuid.uuid4()
        # resolve this inconsistency later
        query_texts = {
            query_id: (
                self._discover_query_text(query_id)
                if self.scenario_handler is None
                else self.scenario_handler.get_query_text(
                    query_id, self.get_system_name()
                )
            )
            for query_id in query_ids
        }
        query_metrics = {
            query_id: GenericQueryMetric(query_id=query_id, status="pending")
            for query_id in query_ids
        }

        for query_id, query_text in query_texts.items():
            try:
                # Replace variable names in the query text
                templated_query = jinja_env.from_string(query_text).render(
                    connection="us.connection",
                    query_id=f"{run_uuid}-q{query_id}",
                    other_params=f", endpoint => '{self.model_name}'",
                    thinking_budget=self.thinking_budget,
                )

                start_time = time.time()
                query_job = self.bq_client.query(templated_query)
                df = query_job.result().to_dataframe()
                execution_time = time.time() - start_time

                query_metrics[query_id].results = df
                query_metrics[query_id].execution_time = execution_time
                query_metrics[query_id].status = "success"
            except Exception as e:
                print(
                    f"  Error executing query {query_id}: {type(e).__name__}: {e}"  # noqa: E501
                )
                query_metrics[query_id].status = "failed"
                query_metrics[query_id].error = str(e)

        # Prices per 1M tokens (USD). Input is split into audio vs "other"
        # (text/image/video).
        MODEL_PRICES = {
            "gemini_2_5_pro": {
                "input_other": 1.25 / 1e6,
                "input_audio": 1.25 / 1e6,
                "output": 10.0 / 1e6,
            },
            "gemini_2_5_flash": {
                "input_other": 0.30 / 1e6,
                "input_audio": 1.00 / 1e6,
                "output": 2.50 / 1e6,
            },
            "gemini_2_5_flash_lite": {
                "input_other": 0.10 / 1e6,
                "input_audio": 0.30 / 1e6,
                "output": 0.40 / 1e6,
            },
            "gemini_2_0_flash": {
                "input_other": 0.15 / 1e6,
                "input_audio": 1.00 / 1e6,
                "output": 0.60 / 1e6,
            },
        }

        AGG_SQL = """
        -- see SQL above; identical text
        WITH all_inference_logs AS (
        SELECT *, 'gemini_2_0_flash'        AS model_key FROM inference_logs.gemini_2_0_flash_001
        UNION ALL
        SELECT *, 'gemini_2_0_flash_lite'   AS model_key FROM inference_logs.gemini_2_0_flash_lite_001
        UNION ALL
        SELECT *, 'gemini_2_5_flash'        AS model_key FROM inference_logs.gemini_2_5_flash
        UNION ALL
        SELECT *, 'gemini_2_5_flash_lite'   AS model_key FROM inference_logs.gemini_2_5_flash_lite_preview_06_17
        UNION ALL
        SELECT *, 'gemini_2_5_pro'          AS model_key FROM inference_logs.gemini_2_5_pro
        ),
        enriched AS (
        SELECT
            model_key,
            full_response,
            SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.promptTokenCount') AS INT64) AS prompt_total,
            COALESCE(ARRAY_LENGTH(JSON_QUERY_ARRAY(full_response, '$.usageMetadata.promptTokensDetails')), 0) AS prompt_details_len,
            SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64) AS output_tokens,
            SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.thoughtsTokenCount')  AS INT64) AS reasoning_tokens,
            SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.billablePromptUsage.textCount') AS INT64)  AS billable_text_count,
            SAFE_CAST(JSON_VALUE(full_response, '$.usageMetadata.billablePromptUsage.audioDurationSeconds') AS FLOAT64) AS billable_audio_seconds,
            (
            SELECT SUM(SAFE_CAST(JSON_VALUE(d, '$.tokenCount') AS INT64))
            FROM UNNEST(JSON_QUERY_ARRAY(full_response, '$.usageMetadata.promptTokensDetails')) AS d
            WHERE JSON_VALUE(d, '$.modality') = 'AUDIO'
            ) AS prompt_audio_detail_sum,
            (
            SELECT SUM(SAFE_CAST(JSON_VALUE(d, '$.tokenCount') AS INT64))
            FROM UNNEST(JSON_QUERY_ARRAY(full_response, '$.usageMetadata.promptTokensDetails')) AS d
            WHERE JSON_VALUE(d, '$.modality') != 'AUDIO'
            ) AS prompt_other_detail_sum
        FROM all_inference_logs
        WHERE JSON_VALUE(full_request, '$.labels.query_uuid') = @query_uuid
        )
        SELECT
        model_key,
        SUM( IFNULL( IF(prompt_details_len > 0, prompt_audio_detail_sum, 0), 0) ) AS prompt_audio_tokens,
        SUM( IFNULL( IF(prompt_details_len > 0, prompt_other_detail_sum, prompt_total), 0) ) AS prompt_other_tokens,
        SUM( IFNULL(output_tokens,   0) ) AS output_tokens,
        SUM( IFNULL(reasoning_tokens,0) ) AS reasoning_tokens,
        SUM( IFNULL(billable_text_count,  0) ) AS billable_text_count,
        SUM( IFNULL(billable_audio_seconds,0.0) ) AS billable_audio_seconds
        FROM enriched
        GROUP BY model_key
        """  # noqa: E501

        for query_id, metrics in query_metrics.items():
            if metrics.status == "failed":
                continue

            # Wait a moment for inference logs to materialize in BigQuery
            print(f"  Waiting 5 seconds for inference logs to materialize for query {query_id}...")
            time.sleep(5)

            max_retries = 3  # 3 * 5s = 15s additional wait if needed
            retry_count = 0
            cost_retrieved = False

            while retry_count < max_retries and not cost_retrieved:
                try:
                    job = self.bq_client.query(
                        AGG_SQL,
                        job_config=bigquery.QueryJobConfig(
                            query_parameters=[
                                bigquery.ScalarQueryParameter(
                                    "query_uuid",
                                    "STRING",
                                    f"{run_uuid}-q{query_id}",
                                )
                            ]
                        ),
                    )
                    df = job.result().to_dataframe()

                    if df.empty:
                        raise ValueError("usage not materialized yet (no rows)")

                    # Totals across all models for this query
                    total_prompt_other = int(
                        df["prompt_other_tokens"].fillna(0).sum()
                    )
                    total_prompt_audio = int(
                        df["prompt_audio_tokens"].fillna(0).sum()
                    )
                    total_output = int(df["output_tokens"].fillna(0).sum())
                    total_reasoning = int(
                        df["reasoning_tokens"].fillna(0).sum()
                    )

                    print(
                        f"{total_prompt_other}, {total_prompt_audio}, {total_output}, {total_reasoning}"  # noqa: E501
                    )

                    # Token usage should match usageMetadata.totalTokenCount
                    # when present:
                    total_token_usage = (
                        total_prompt_other
                        + total_prompt_audio
                        + total_output
                        + total_reasoning
                    )

                    # Money: per-model pricing
                    total_cost = 0.0
                    for row in df.itertuples(index=False):
                        model = row.model_key
                        prices = MODEL_PRICES.get(model)
                        if not prices:
                            # Unknown model: count tokens but skip billing (or
                            # set a fallback if you prefer)
                            print(
                                f"  Warning: No pricing configured for model '{model}'. Cost will exclude this model."  # noqa: E501
                            )
                            continue

                        in_cost = (
                            int(row.prompt_other_tokens) * prices["input_other"]
                        ) + (
                            int(row.prompt_audio_tokens) * prices["input_audio"]
                        )
                        # Reasoning tokens billed at output rate
                        out_cost = (
                            int(row.output_tokens) + int(row.reasoning_tokens)
                        ) * prices["output"]

                        total_cost += in_cost + out_cost

                    metrics.token_usage = int(total_token_usage)
                    metrics.money_cost = float(total_cost)
                    cost_retrieved = True

                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(
                            f"  Error getting cost for query {query_id} (attempt {retry_count}/{max_retries}): {type(e).__name__}: {e}, retrying in 5 seconds..."  # noqa: E501
                        )
                        time.sleep(5)
                    else:
                        print(
                            f"  Final error getting cost for query {query_id}: {type(e).__name__}: {e}"  # noqa: E501
                        )

            if not cost_retrieved:
                print(
                    f"  Could not retrieve cost data for query {query_id} after {max_retries} attempts, setting to 0"  # noqa: E501
                )
                metrics.token_usage = 0
                metrics.money_cost = 0.0

        return query_metrics
