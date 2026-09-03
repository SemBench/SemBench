"""
Lotus system runner implementation.
Placeholder required by the current structure of the benchmarking framework.
"""

from pathlib import Path
import sys
import time
import types
import lotus
import traceback

from runner.generic_runner import GenericQueryMetric, GenericRunner

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from runner.generic_lotus_runner.generic_lotus_runner import GenericLotusRunner

# Import additional modules for approximate policy
from lotus.models import SentenceTransformersRM
from lotus.types import CascadeArgs
from lotus.vector_store import FaissVS


class LotusRunner(GenericLotusRunner):
    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str = "vertex_ai/gemini-2.5-flash",
        concurrent_llm_worker=20,
        skip_setup: bool = False,
    ):
        super().__init__(
            use_case,
            scale_factor,
            model_name,
            concurrent_llm_worker,
            skip_setup=skip_setup,
        )

        # Initialize components for approximate policy
        if hasattr(self, "policy") and self.policy == "approximate":
            # Initialize both embedding models for mixed modality support
            self.rm_text = SentenceTransformersRM(model="intfloat/e5-base-v2")
            self.rm_image = SentenceTransformersRM("clip-ViT-B-32")
            self.vs = FaissVS()
            self.cascade_args = CascadeArgs(
                recall_target=0.8, precision_target=0.8
            )

    def _configure_lotus_for_join_type(self, join_type: str):
        """Configure LOTUS settings based on join type (text-only, image-only, or mixed)."""
        if hasattr(self, "policy") and self.policy == "approximate":
            if join_type == "text":
                lotus.settings.configure(
                    lm=self.lm, rm=self.rm_text, vs=self.vs
                )
            elif join_type == "image":
                lotus.settings.configure(
                    lm=self.lm, rm=self.rm_image, vs=self.vs
                )
            else:  # mixed or default
                # For mixed modality, use image embeddings as they handle both
                lotus.settings.configure(
                    lm=self.lm, rm=self.rm_image, vs=self.vs
                )

    def _discover_queries(self):
        # Match default implementation from GenericRunner
        return GenericRunner._discover_queries(self)

    def execute_query(self, query_id: int) -> GenericQueryMetric:
        metric = GenericQueryMetric(query_id=query_id, status="pending")

        # Reset token stats before each query
        try:
            lotus.settings.lm.reset_stats()
        except Exception as e:
            print(f"  Warning: Could not reset stats: {e}")

        try:
            # The queries in LOTUS are Python files with a run() function.
            # Load its contents, create a module, invoke the run() function.
            query_text = self.scenario_handler.get_query_text(
                query_id, self.get_system_name()
            )
            query_module = types.ModuleType(f"q{query_id}_module")

            # Inject helper functions and objects for approximate policy
            if hasattr(self, "policy") and self.policy == "approximate":
                query_module.__dict__["_configure_lotus"] = self._configure_lotus_for_join_type
                query_module.__dict__["_cascade_args"] = self.cascade_args
                query_module.__dict__["_policy"] = self.policy

            exec(query_text, query_module.__dict__)

            start_time = time.time()
            results = query_module.run(self.scenario_handler.get_data_dir())
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
            print(f"  Error in Q{query_id} execution: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise

        finally:
            # Reset stats after storing
            try:
                lotus.settings.lm.reset_stats()
            except:
                pass

        return metric
