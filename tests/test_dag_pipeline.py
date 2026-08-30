"""
tests/test_dag_pipeline.py
Unit tests for DAG Modular Pipeline Orchestrator & Task Checkpointing Engine.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
create dummy/facade implementations, or circumvent the intended task. A Forensic
Auditor will independently verify your work. Integrity violations WILL be detected
and your work WILL be rejected.
"""

import os
import sys
import shutil
import tempfile
import unittest
from typing import Any, List

# Ensure project root and trading_system are in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd

try:
    from dag_pipeline import (
        CheckpointManager,
        CyclicDependencyError,
        DAGContext,
        DAGRunner,
        Task,
    )
except ImportError:
    from trading_system.dag_pipeline import (
        CyclicDependencyError,
        DAGContext,
        DAGRunner,
        Task,
    )

from src.config import TradingConfig


class DummyTask(Task):
    """Concrete test implementation of Task interface."""

    def __init__(self, name: str, dependencies: List[str] = None, fail: bool = False):
        super().__init__(name=name, dependencies=dependencies)
        self.executed = False
        self.restored = False
        self.fail = fail

    def execute(self, context: DAGContext) -> Any:
        self.executed = True
        if self.fail:
            raise RuntimeError(f"Task {self.name} deliberate failure")
        return {"task_name": self.name, "df": pd.DataFrame({"a": [1, 2, 3]})}

    def checkpoint(self, context: DAGContext, result: Any) -> None:
        cm = context.checkpoint_manager
        artifacts = []
        if isinstance(result, dict) and "df" in result:
            art = cm.save_parquet(f"{self.name}_output.parquet", result["df"])
            artifacts.append(art)
        cm.mark_completed(self.name, duration=0.01, artifacts=artifacts, context=context)

    def restore(self, context: DAGContext) -> Any:
        self.restored = True
        cm = context.checkpoint_manager
        df = cm.load_parquet(f"{self.name}_output.parquet")
        return {"task_name": self.name, "df": df}


class TestDAGPipeline(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = TradingConfig()
        self.context = DAGContext(config=self.config, checkpoint_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_task_interface_compliance(self):
        task = DummyTask(name="T1")
        self.assertEqual(task.name, "T1")
        self.assertEqual(task.dependencies, [])
        res = task.execute(self.context)
        self.assertIn("task_name", res)
        task.checkpoint(self.context, res)
        self.assertTrue(task.is_checkpoint_valid(self.context))
        restored = task.restore(self.context)
        self.assertTrue(task.restored)
        self.assertEqual(len(restored["df"]), 3)

    def test_dag_topological_sort_diamond(self):
        # A -> B, A -> C, B -> D, C -> D
        task_a = DummyTask("A")
        task_b = DummyTask("B", dependencies=["A"])
        task_c = DummyTask("C", dependencies=["A"])
        task_d = DummyTask("D", dependencies=["B", "C"])

        runner = DAGRunner([task_a, task_b, task_c, task_d], self.context)
        names = [t.name for t in runner.execution_order]
        self.assertEqual(names[0], "A")
        self.assertEqual(names[-1], "D")
        self.assertIn("B", names[1:3])
        self.assertIn("C", names[1:3])

    def test_dag_cycle_detection_raises_error(self):
        # A -> B -> C -> A
        task_a = DummyTask("A", dependencies=["C"])
        task_b = DummyTask("B", dependencies=["A"])
        task_c = DummyTask("C", dependencies=["B"])

        with self.assertRaises(CyclicDependencyError):
            DAGRunner([task_a, task_b, task_c], self.context)

    def test_pipeline_resumption_skips_executed_nodes(self):
        task_a = DummyTask("A")
        task_b = DummyTask("B", dependencies=["A"])

        runner1 = DAGRunner([task_a, task_b], self.context)
        runner1.run()
        self.assertTrue(task_a.executed)
        self.assertTrue(task_b.executed)

        # Second run with new task instances but same checkpoint dir
        task_a2 = DummyTask("A")
        task_b2 = DummyTask("B", dependencies=["A"])
        context2 = DAGContext(config=self.config, checkpoint_dir=self.test_dir)
        runner2 = DAGRunner([task_a2, task_b2], context2)
        runner2.run()

        # Task A and B should be restored from checkpoints, NOT re-executed
        self.assertFalse(task_a2.executed)
        self.assertTrue(task_a2.restored)
        self.assertFalse(task_b2.executed)
        self.assertTrue(task_b2.restored)

    def test_force_rerun_invalidates_checkpoints(self):
        task_a = DummyTask("A")
        runner1 = DAGRunner([task_a], self.context)
        runner1.run()

        # Re-run with force_rerun=True
        config_force = TradingConfig()
        setattr(config_force, "force_rerun", True)
        context_force = DAGContext(config=config_force, checkpoint_dir=self.test_dir)
        task_a2 = DummyTask("A")
        runner2 = DAGRunner([task_a2], context_force)
        runner2.run()

        self.assertTrue(task_a2.executed)
        self.assertFalse(task_a2.restored)


if __name__ == "__main__":
    unittest.main()
