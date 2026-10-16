"""
test_gha_workflow_resilience.py — Comprehensive Adversarial Verification for GHA CI & Daily Pipeline Resilience

Validates:
1. Strict timeouts and hang prevention in CI workflows (ci.yml, pytest.yml).
2. High-availability deployment and concurrency isolation in Daily Pipeline (daily_pipeline.yml, pipeline.yml).
3. Phase 16 & 17 benchmark synchronization integrity.
"""

from pathlib import Path
import pytest
import yaml

from trading_system.scripts.benchmark_phase16_quant_performance import Phase16QuantBenchmarkEngine
from trading_system.scripts.benchmark_phase17_quant_performance import Phase17QuantBenchmarkEngine


class TestWorkflowTimeoutAndHangPrevention:
    """Verifies that CI / Testing & Security Audit workflows enforce bounded execution."""

    @pytest.mark.parametrize("filename", ["ci.yml", "pytest.yml"])
    def test_ci_workflow_timeouts(self, filename: str):
        wf_path = Path(".github/workflows") / filename
        assert wf_path.exists(), f"Workflow file {filename} missing"
        data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))

        jobs = data.get("jobs", {})
        assert "test" in jobs, f"Job 'test' missing from {filename}"
        test_job = jobs["test"]

        # Job-level timeout must be <= 30 minutes to eliminate 6-hour hangs
        assert "timeout-minutes" in test_job, f"Job 'test' in {filename} lacks timeout-minutes"
        assert test_job["timeout-minutes"] <= 30, f"Job timeout exceeds 30m in {filename}"

        # Steps must have individual timeouts
        steps = test_job.get("steps", [])
        step_timeouts = {s.get("name"): s.get("timeout-minutes") for s in steps if "name" in s}

        for critical_step in ["Install dependencies", "Run type checking", "Lint (ruff)", "Security audit (bandit)", "Run unit tests"]:
            assert critical_step in step_timeouts, f"Critical step '{critical_step}' not found in {filename}"
            assert step_timeouts[critical_step] is not None, f"Step '{critical_step}' missing timeout-minutes in {filename}"
            assert step_timeouts[critical_step] <= 25, f"Step '{critical_step}' timeout exceeds 25m in {filename}"

        # Unit test step must enforce pytest-timeout and offline isolation
        test_step = next(s for s in steps if s.get("name") == "Run unit tests")
        assert "--timeout=" in test_step.get("run", ""), f"Unit test step lacks --timeout= in {filename}"
        env = test_step.get("env", {})
        assert env.get("HISTORICAL_OFFLINE") == "1", f"Unit test step lacks HISTORICAL_OFFLINE=1 in {filename}"


class TestDailyPipelineDeployPagesStability:
    """Verifies that Daily Pipeline deploy-pages step is immune to queue stalls and concurrency locks."""

    @pytest.mark.parametrize("filename", ["daily_pipeline.yml", "pipeline.yml"])
    def test_deploy_pages_resilience(self, filename: str):
        wf_path = Path(".github/workflows") / filename
        assert wf_path.exists(), f"Workflow file {filename} missing"
        data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))

        jobs = data.get("jobs", {})
        assert "deploy-pages" in jobs, f"Job 'deploy-pages' missing from {filename}"
        deploy_job = jobs["deploy-pages"]

        # Job-level timeout <= 20 minutes
        assert "timeout-minutes" in deploy_job, f"deploy-pages in {filename} lacks timeout-minutes"
        assert deploy_job["timeout-minutes"] <= 20, f"deploy-pages timeout exceeds 20m in {filename}"

        # Pages concurrency group to serialize deployments and avoid updating_pages locks
        assert "concurrency" in deploy_job, f"deploy-pages in {filename} lacks concurrency configuration"
        assert deploy_job["concurrency"].get("group") == "pages", f"deploy-pages concurrency group must be 'pages' in {filename}"
        assert deploy_job["concurrency"].get("cancel-in-progress") is False, f"cancel-in-progress must be false for Pages in {filename}"

        # Step-level resiliency
        steps = deploy_job.get("steps", [])
        deploy_step = next((s for s in steps if "actions/deploy-pages" in s.get("uses", "")), None)
        assert deploy_step is not None, f"actions/deploy-pages step missing in {filename}"

        assert deploy_step.get("continue-on-error") is True, f"deploy-pages step must have continue-on-error: true in {filename}"
        step_with = deploy_step.get("with", {})
        assert step_with.get("timeout") >= 600000, f"deploy-pages timeout must be >= 10m (600000ms) in {filename}"

        # Verification step must exist
        verify_step = next((s for s in steps if s.get("name") == "Verify Pages deployment outcome"), None)
        assert verify_step is not None, f"Verify Pages deployment outcome step missing in {filename}"
        assert verify_step.get("if") == "always()", f"Verification step must run on always() in {filename}"


class TestBenchmarkPhase16And17SyncReports:
    """Verifies that Phase 16 and 17 benchmark engines produce valid reports without errors."""

    def test_phase16_report_synchronization(self):
        engine = Phase16QuantBenchmarkEngine()
        res = engine.run_all(sync_reports=False)
        assert "markdown_report" in res
        assert "Phase 16 Quantitative Enhancement" in res["markdown_report"]
        assert len(res["markets_evaluated"]) == 5

    def test_phase17_report_synchronization(self):
        engine = Phase17QuantBenchmarkEngine()
        res = engine.run_all(sync_reports=False)
        assert "markdown_report" in res
        assert "Phase 17 Quantitative Enhancement" in res["markdown_report"]
        assert len(res["markets_evaluated"]) == 5
