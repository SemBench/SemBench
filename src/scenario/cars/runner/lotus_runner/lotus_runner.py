"""
Lotus system runner implementation for Cars scenario.
"""

from pathlib import Path
import sys
import importlib.util

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from runner.generic_lotus_runner.generic_lotus_runner import GenericLotusRunner


class LotusRunner(GenericLotusRunner):
    def __init__(
        self,
        use_case: str,
        scale_factor: int,
        model_name: str = "gemini-2.5-flash",
        concurrent_llm_worker=20,
        skip_setup: bool = False,
    ):
        super().__init__(
            use_case, scale_factor, model_name, concurrent_llm_worker, skip_setup
        )

    def _load_and_execute_query(self, query_id: int):
        """Dynamically load and execute a query from the query files."""
        query_file = Path(__file__).resolve().parents[5] / "files" / self.use_case / "query" / "lotus" / f"Q{query_id}.py"

        # Load the query module
        spec = importlib.util.spec_from_file_location(f"query_{query_id}", query_file)
        query_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(query_module)

        # Execute the query - pass files_path as data_dir
        return query_module.run(str(self.files_path), self.scale_factor)

    def _execute_q1(self):
        return self._load_and_execute_query(1)

    def _execute_q2(self):
        return self._load_and_execute_query(2)

    def _execute_q3(self):
        return self._load_and_execute_query(3)

    def _execute_q4(self):
        return self._load_and_execute_query(4)

    def _execute_q5(self):
        return self._load_and_execute_query(5)

    def _execute_q6(self):
        return self._load_and_execute_query(6)

    def _execute_q7(self):
        return self._load_and_execute_query(7)

    def _execute_q8(self):
        return self._load_and_execute_query(8)

    def _execute_q9(self):
        return self._load_and_execute_query(9)

    def _execute_q10(self):
        return self._load_and_execute_query(10)
