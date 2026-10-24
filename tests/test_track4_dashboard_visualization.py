# -*- coding: utf-8 -*-

import inspect
import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

_LEGACY_LITERALS = (
    "8.19",
    "1,149.55",
    "1149.55",
    "35.43",
    "8,089",
    "SP500 10.05%",
    "KOSPI 10.18%",
    "KOSPI -71.6%",
    "KOSDAQ -90.8%",
    "13.05%",
    "~40%",
    "1.86회",
    "Pass Rate: 100%",
    "방어 성공",
    "Lookahead 0%",
)


def _valid_artifact() -> dict:
    return {
        "metadata": {
            "official_benchmark": "stock_universe",
            "verification_status": "PASSED",
            "synthetic_rows": 0,
            "universe_symbols": 106,
            "registry_symbols": 106,
            "universe_coverage_pct": 100.0,
            "total_trading_days": 7412,
            "simulation_period": "1996-01-01 ~ 2026-08-31",
            "benchmark_name": "KOSPI",
            "benchmark_cagr_pct": 6.1,
            "benchmark_mdd_pct": -55.2,
        },
        "portfolio_overall": {
            "initial_capital": 100000000.0,
            "final_equity": 156780000.0,
            "cagr_pct": 12.34,
            "total_net_return_pct": 56.78,
            "total_gross_return_pct": 78.9,
            "max_drawdown_pct": -9.87,
            "sharpe_ratio": 1.23,
            "sortino_ratio": 1.78,
            "win_rate_pct": 58.2,
            "profit_factor": 1.45,
            "annualized_volatility_pct": 11.4,
        },
        "historical_crises": [
            {
                "crisis_name": "Test Crisis A",
                "start_date": "2000-01-01",
                "end_date": "2000-12-31",
                "net_return_pct": 5.5,
                "benchmark_return_pct": -10.0,
                "max_drawdown_pct": -3.2,
                "recovery_days": 45,
                "defense_pass": True,
            },
            {
                "crisis_name": "Test Crisis B",
                "start_date": "2008-01-01",
                "end_date": "2008-12-31",
                "net_return_pct": -4.5,
                "benchmark_return_pct": -20.0,
                "max_drawdown_pct": -11.0,
                "recovery_days": 120,
                "defense_pass": False,
            },
        ],
        "annual_distribution": [
            {
                "year": 2024,
                "net_return_pct": 8.5,
                "max_drawdown_pct": -2.1,
                "sharpe_ratio": 1.1,
            },
            {
                "year": 2025,
                "net_return_pct": -3.2,
                "max_drawdown_pct": -4.4,
                "sharpe_ratio": -0.4,
                "is_partial": True,
            },
        ],
    }


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    import trading_system.generate_report as gr

    monkeypatch.setattr(gr, "OFFICIAL_30YEAR_BENCHMARK_PATH", tmp_path / "official.json")
    monkeypatch.setattr(gr, "PAPER_TRADING_REPORT_PATH", tmp_path / "paper.json")
    return tmp_path


class TestTrack4DashboardVisualization:
    def test_missing_artifact_renders_unverified_state(self, isolated_paths):
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        html = build_30year_benchmark_dashboard_html(isolated_paths)

        assert "공식 30년 벤치마크 재구축 중 (Unverified)" in html
        assert "UNVERIFIED" in html
        assert "benchmarks/30year/stock_universe_summary.json" in html
        for literal in _LEGACY_LITERALS:
            assert literal not in html

    def test_legacy_artifact_cannot_render_performance(self, isolated_paths):
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        legacy = {
            "portfolio_overall": {
                "cagr_pct": 8.19,
                "total_net_return_pct": 1149.55,
                "max_drawdown_pct": -35.43,
            }
        }
        (isolated_paths / "stock_universe_summary.json").write_text(
            json.dumps(legacy), encoding="utf-8"
        )

        html = build_30year_benchmark_dashboard_html(isolated_paths)

        assert "공식 30년 벤치마크 재구축 중 (Unverified)" in html
        assert "8.19" not in html
        assert "1,149.55" not in html
        assert "35.43" not in html

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda data: data["metadata"].update(official_benchmark="other"),
            lambda data: data["metadata"].update(verification_status="FAILED"),
            lambda data: data["metadata"].update(synthetic_rows=1),
            lambda data: data["metadata"].update(synthetic_rows=False),
            lambda data: data["metadata"].pop("synthetic_rows"),
            lambda data: data["metadata"].pop("universe_symbols"),
            lambda data: data["metadata"].update(universe_symbols=96, registry_symbols=106),
            lambda data: data["metadata"].update(universe_symbols=True),
            lambda data: data["portfolio_overall"].update(cagr_pct="nan"),
        ],
    )
    def test_verification_gate_rejects_untrusted_artifacts(self, isolated_paths, mutate):
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        data = _valid_artifact()
        mutate(data)
        (isolated_paths / "stock_universe_summary.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        html = build_30year_benchmark_dashboard_html(isolated_paths)

        assert "공식 30년 벤치마크 재구축 중 (Unverified)" in html
        assert "12.34%" not in html

    def test_verified_artifact_renders_data_driven_metrics(self, isolated_paths):
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        (isolated_paths / "stock_universe_summary.json").write_text(
            json.dumps(_valid_artifact()), encoding="utf-8"
        )

        html = build_30year_benchmark_dashboard_html(isolated_paths)

        assert "VERIFIED" in html
        assert "12.34%" in html
        assert "+56.78%" in html
        assert "-9.87%" in html
        assert "KOSPI CAGR 6.10% · MDD -55.20%" in html
        assert "Test Crisis A" in html
        assert "Test Crisis B" in html
        assert "Pass Rate: 50%" in html
        assert "2025년 · 부분" in html
        assert "synthetic rows 0" in html
        assert "stock_universe_summary.json" in html
        for literal in _LEGACY_LITERALS:
            assert literal not in html

    def test_missing_fields_render_na_without_fabricated_values(self, isolated_paths):
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        data = _valid_artifact()
        data["portfolio_overall"].pop("sharpe_ratio")
        data["portfolio_overall"].pop("win_rate_pct")
        data["annual_distribution"] = []
        data["historical_crises"] = []
        (isolated_paths / "stock_universe_summary.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        html = build_30year_benchmark_dashboard_html(isolated_paths)

        assert "N/A" in html
        assert "검증된 위기 데이터 없음" in html
        assert "검증된 연도별 데이터 없음" in html
        assert "방어 판정 데이터 없음" in html
        assert "Pass Rate: 100%" not in html

    def test_paper_monitor_uses_report_values_only(self, isolated_paths):
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        (isolated_paths / "stock_universe_summary.json").write_text(
            json.dumps(_valid_artifact()), encoding="utf-8"
        )
        paper = {
            "status": "COMPLETED",
            "total_executions": 3,
            "total_fees_paid_krw": 12.5,
            "total_slippage_cost_krw": 2.5,
            "invariant_net_le_gross": True,
            "final_snapshot": {
                "gross_equity": 100000000.0,
                "net_equity": 99999985.0,
                "timestamp": "2026-10-21T12:00:00",
            },
        }
        (isolated_paths / "paper.json").write_text(json.dumps(paper), encoding="utf-8")

        html = build_30year_benchmark_dashboard_html(isolated_paths)

        assert "3건" in html
        assert "15.00 KRW" in html
        assert "Invariant: PASSED" in html
        assert "17건" not in html

    def test_paper_monitor_absent_shows_no_data(self, isolated_paths):
        from trading_system.generate_report import build_30year_benchmark_dashboard_html

        (isolated_paths / "stock_universe_summary.json").write_text(
            json.dumps(_valid_artifact()), encoding="utf-8"
        )

        html = build_30year_benchmark_dashboard_html(isolated_paths)

        assert "페이퍼 트레이딩 리포트 없음" in html
        assert "301.13" not in html
        assert "99,999,687" not in html

    def test_renderer_source_has_no_legacy_performance_literals(self):
        import trading_system.generate_report as gr

        source = inspect.getsource(gr.build_30year_benchmark_dashboard_html)
        for literal in _LEGACY_LITERALS:
            assert literal not in source

    def test_gh_pages_index_html_integration(self):
        gh_pages_path = _PROJECT_ROOT / "gh-pages" / "index.html"
        target_file = gh_pages_path
        assert target_file.exists()

        content = target_file.read_text(encoding="utf-8", errors="replace")

        assert "30-Year Quantitative Benchmark" in content
        assert "공식 30년 벤치마크 재구축 중 (Unverified)" in content
        assert "+1,149.55%" not in content
        assert "-35.43%" not in content
        assert "Pass Rate: 100%" not in content
