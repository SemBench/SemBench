"""
Created on May 28, 2025

@author: Jiale Lao

LOTUS system runner implementation based on generic_runner for movie use case.
"""

from overrides import override
import pandas as pd
import time
from typing import List
import lotus
from lotus.models import LM
import re
from PIL import ImageFile

from runner.generic_runner import GenericRunner, GenericQueryMetric

# Allow loading of truncated images (some source images may be incomplete)
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Pricing rules: (text_input, audio_input, output) per 1M tokens
PRICING = {
    "gpt-4o": {"text": 2.5, "audio": 2.5, "output": 10.0},
    "gpt-4o-mini": {"text": 0.15, "audio": 0.15, "output": 0.6},
    "gpt-4o-audio-preview": {
        "text": 2.5,
        "audio": 2.5,
        "output": 10.0,
    },
    "gpt-5": {"text": 1.25, "audio": 1.25, "output": 10.0},
    "gpt-5-mini": {"text": 0.25, "audio": 0.25, "output": 2.0},
    "gemini-2.0-flash": {
        "text": 0.15,
        "audio": 1.0,
        "output": 0.6,
    },
    "gemini-2.5-flash": {
        "text": 0.3,
        "audio": 1.0,
        "output": 2.5,
    },
    "gemini-2.5-flash-lite": {
        "text": 0.1,
        "audio": 0.3,
        "output": 0.4,
    },
    "gemini-2.5-pro": {
        "text": 1.25,
        "audio": 1.25,
        "output": 10.0,
    },
}


class GenericLotusRunner(GenericRunner):
    """GenericRunner for LOTUS system."""

    # thinking for gemini-2.5-pro can not be disabled, but always has issues
    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str = "gemini-2.5-flash",
        concurrent_llm_worker=20,
        skip_setup: bool = False,
        policy="approximate",
        ranking="map",
    ):
        """
        Initialize LOTUS runner.

        Args:
            use_case: The use case to run
            model_name: LLM model to use
        """
        super().__init__(
            use_case,
            scale_factor,
            model_name,
            concurrent_llm_worker,
            skip_setup,
        )
        self.policy = policy  # the policy can be "exact" or "approximate"
        self.ranking = ranking  # the ranking method could be "topk" or "map", for sem_topk and sem_map respectively

        # Initialize LOTUS

        # to avoid exceeding the reasoning_token of gemini models, default in LOTUS is 512
        self.max_tokens = 8192

        # Configure LM based on model_name
        self.lm = self._configure_lm()

        lotus.settings.configure(lm=self.lm)

        self._initialize_lotus_with_warmup()

    def _configure_lm(self) -> LM:
        """
        Configure Language Model based on self.model_name.

        Returns:
            Configured LM instance
        """
        base_config = {
            "max_batch_size": self.concurrent_llm_worker,
            "max_tokens": self.max_tokens,
        }

        model_lower = self.model_name.lower()

        if "gemini-2.5-pro" in model_lower or "gemini_2_5_pro" in model_lower:
            # gemini-2.5-pro: reasoning_effort="low", solve the "no content due to length" issue
            # but does not work when concurrent_llm_worker is 20, try using rate_limit to control
            return LM(
                self.model_name,
                rate_limit=2000,
                max_tokens=self.max_tokens,
                reasoning_effort="low",
            )
        elif (
            "gemini-2.5-flash" in model_lower
            or "gemini_2_5_flash" in model_lower
        ):
            # gemini-2.5-flash: reasoning_effort="disable", works well
            return LM(
                self.model_name, **base_config, reasoning_effort="disable"
            )
        elif (
            "gemini-2.0-flash" in model_lower
            or "gemini_2_0_flash" in model_lower
        ):
            # gemini-2.0-flash: no reasoning_effort parameter needed
            return LM(self.model_name, **base_config)
        elif "gpt-5-mini" in model_lower or "gpt_5_mini" in model_lower:
            # gpt-5-mini: reasoning_effort="minimal"
            return LM(
                self.model_name, **base_config, reasoning_effort="minimal"
            )
        else:
            # Default configuration for unknown models (no reasoning_effort)
            print(
                f"Warning: Unknown model '{self.model_name}', using default configuration"
            )
            return LM(self.model_name, **base_config)

    def _initialize_lotus_with_warmup(self):
        """Initialize LOTUS and perform connection warmup to avoid first-query errors."""

        # Configure LOTUS
        lotus.settings.configure(lm=self.lm)

        # Strategy 1: Perform a simple warmup query
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Make a simple test call to establish connection
                self.lm.__call__(["hi"], show_progress_bar=False)
                print(
                    f"LOTUS connection warmed up successfully on attempt {attempt + 1}"
                )
                break

            except Exception as e:
                print(f"Warmup attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Don't fail initialization, just log the warning
                    print(
                        "Warning: Connection warmup failed, but continuing..."
                    )

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost based on prompt and completion tokens.
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            
        Returns:
            Total cost in USD
        """
        model_name = self.model_name.lower()
        
        # Find matching pricing configuration
        pricing_config = None
        for model_key in PRICING:
            if model_key.lower() in model_name:
                pricing_config = PRICING[model_key]
                break
        
        if pricing_config is None:
            print(f"Warning: No pricing found for model '{self.model_name}', cost calculation skipped")
            return 0.0
        
        # Calculate cost: prices are per 1M tokens
        input_cost = (prompt_tokens / 1_000_000) * pricing_config["text"]
        output_cost = (completion_tokens / 1_000_000) * pricing_config["output"]
        total_cost = input_cost + output_cost
        
        return total_cost

    @override
    def get_system_name(self) -> str:
        return "lotus"

    def execute_query(self, query_id: int) -> GenericQueryMetric:
        """
        Execute a specific query using LOTUS and return metric with results.

        Args:
            query_id: ID of the query (e.g., 1 for Q1, 5 for Q5)

        Returns:
            QueryMetric object containing results DataFrame and metrics
        """
        # Create appropriate metric object
        metric = GenericQueryMetric(query_id=query_id, status="pending")

        # Reset token stats before each query
        try:
            lotus.settings.lm.reset_stats()
        except Exception as e:
            print(f"  Warning: Could not reset stats: {e}")

        try:
            query_fn = self._discover_query_impl(query_id)
            start_time = time.time()
            results = query_fn()
            execution_time = time.time() - start_time

            # Store results in metric
            metric.execution_time = execution_time
            metric.results = results
            metric.status = "success"

            # Get token usage and cost
            self._update_token_usage(metric)

        except Exception as e:
            # Handle failure
            metric.status = "failed"
            metric.error = str(e)
            metric.results = self._get_empty_results_dataframe(query_id)
            print(f"  Error in Q{query_id} execution: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Reset stats after storing
            try:
                lotus.settings.lm.reset_stats()
            except:
                pass

        return metric

    def _get_empty_results_dataframe(self, query_id: int) -> pd.DataFrame:
        """
        Get empty DataFrame with correct columns for a query.

        Args:
            query_id: ID of the query

        Returns:
            Empty DataFrame with correct columns
        """
        if query_id == 1:
            return pd.DataFrame(columns=["reviewId", "movieId", "reviewText"])
        elif query_id == 5:
            return pd.DataFrame(
                columns=[
                    "id",
                    "reviewId_left",
                    "reviewText_left",
                    "reviewId_right",
                    "reviewText_right",
                ]
            )
        else:
            return pd.DataFrame()

    def _update_token_usage(self, metric: GenericQueryMetric):
        """Update metric with token usage and cost information."""
        try:
            # Get usage stats from LOTUS using the correct API
            prompt_tokens = lotus.settings.lm.stats.physical_usage.prompt_tokens
            completion_tokens = lotus.settings.lm.stats.physical_usage.completion_tokens
            total_tokens = lotus.settings.lm.stats.physical_usage.total_tokens
            total_cost = lotus.settings.lm.stats.physical_usage.total_cost
            
            # Calculate cost using our token consumption
            calculated_cost = self._calculate_cost(prompt_tokens, completion_tokens)

            # Print both tokens for comparison
            print(f"prompt token: {prompt_tokens}, completion token: {completion_tokens}")
            print(f"total tokens: {total_tokens}")
            
            # Print both costs for comparison
            print(f"  LOTUS cost: ${total_cost:.6f}")
            print(f"  Calculated cost based on token consumption: ${calculated_cost:.6f}")

            metric.token_usage = total_tokens
            metric.money_cost = calculated_cost

        except Exception as e:
            print(f"  Warning: Could not get token usage: {e}")
            metric.token_usage = 0
            metric.money_cost = 0.0

    def _discover_queries(self) -> List[int]:
        """
        Discover available queries for LOTUS.

        Any method named ``_execute_q<i>`` (where <i> is an integer ≥1) is treated
        as an implemented query.  The function returns the list of those integer
        IDs in ascending order.

        Returns:
            List of available query IDs
        """
        # Return only implemented queries

        pattern = re.compile(r"_execute_q(\d+)$")
        query_ids: List[int] = []

        # `dir(self)` lists all attribute names visible on the instance;
        # we then pick out callables whose names match our pattern.
        for attr_name in dir(self):
            match = pattern.match(attr_name)
            if match:
                attr = getattr(self, attr_name, None)
                if callable(attr):
                    query_ids.append(int(match.group(1)))

        return sorted(query_ids)
