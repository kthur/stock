"""Dynamic Strategy Registry — 신규 전략 엔진 파일 추가만으로 시스템 전체 자동 등록."""

import importlib
import logging
import pkgutil
from typing import Any, Dict, List, Optional, Tuple, Type

logger = logging.getLogger(__name__)


class StrategyMeta:
    """전략 메타데이터 (가중치, 스코어 컬럼, 레짐 기본 가중치 등)."""

    def __init__(
        self,
        strategy_id: str,
        display_name: str,
        score_column: str,
        category: str = "factor",  # 'factor' | 'ml' | 'stat' | 'event'
        default_regime_weights: Optional[Dict[str, float]] = None,
        output_file: Optional[str] = None,
        requires_fundamentals: bool = False,
        requires_indicators: bool = False,
        is_standalone: bool = False,  # True인 경우 앙상블 비중 배분에서 제외하고 독립 시그널로만 사용
    ) -> None:
        self.strategy_id = strategy_id
        self.display_name = display_name
        self.score_column = score_column
        self.category = category
        safe_regime_weights = {}
        if default_regime_weights and isinstance(default_regime_weights, dict):
            import math
            for r_k, r_v in default_regime_weights.items():
                try:
                    f_v = float(r_v)
                    safe_regime_weights[str(r_k)] = f_v if (math.isfinite(f_v) and f_v >= 0.0) else 0.0
                except (ValueError, TypeError):
                    safe_regime_weights[str(r_k)] = 0.0
        self.default_regime_weights = safe_regime_weights
        self.output_file = output_file
        self.requires_fundamentals = requires_fundamentals
        self.requires_indicators = requires_indicators
        self.is_standalone = is_standalone


class StrategyRegistry:
    """전역 전략 레지스트리 (싱글턴)."""

    _instance: Optional["StrategyRegistry"] = None
    _strategies: Dict[str, Tuple[Type[Any], StrategyMeta]]

    def __new__(cls) -> "StrategyRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._strategies = {}
        return cls._instance

    def register(self, meta: StrategyMeta, engine_cls: Type[Any]) -> None:
        self._strategies[meta.strategy_id] = (engine_cls, meta)
        logger.debug(f"[StrategyRegistry] Registered strategy '{meta.strategy_id}' ({meta.display_name})")

    def get(self, strategy_id: str) -> Optional[Tuple[Type[Any], StrategyMeta]]:
        return self._strategies.get(strategy_id)

    def get_all(self) -> Dict[str, Tuple[Type[Any], StrategyMeta]]:
        return dict(self._strategies)

    def get_all_ids(self) -> List[str]:
        return list(self._strategies.keys())

    def get_all_score_columns(self) -> Dict[str, str]:
        return {sid: meta.score_column for sid, (_, meta) in self._strategies.items()}

    def get_strategy_count(self) -> int:
        return len(self._strategies)

    def auto_discover(self, package_paths: Optional[List[str]] = None) -> None:
        """지정된 패키지 경로에서 전략 모듈을 자동 임포트하여 데코레이터를 실행시킴."""
        if package_paths is None:
            package_paths = ["src.core", "src.ai"]
        import sys
        from pathlib import Path

        # Add trading_system root to sys.path if not present
        cur_file = Path(__file__).resolve()
        ts_dir = str(cur_file.parent.parent.parent)
        if ts_dir not in sys.path:
            sys.path.insert(0, ts_dir)

        core_modules = [
            "src.ai.ml_strategy_adapters",
            "src.core.hft_engine",
            "src.core.stat_arb",
            "src.core.sector_rotation",
            "src.core.rim_valuation",
            "src.core.event_driven",
            "src.core.mq_factor",
            "src.core.iv_skew",
            "src.core.order_flow",
            "src.core.short_term_reversal",
            "src.core.multi_factor_neutralizer",
            "src.core.vol_target",
            "src.core.arm_factor",
            "src.core.card_factor",
            "src.core.latr_factor",
            "src.core.supply_chain",
            "src.core.accruals_quality",
            "src.core.trend_efficiency",
            "src.core.inst_foreign_sector",
            "src.core.llm_sentiment_engine",
            "src.core.short_interest_squeeze",
            "src.core.valueup_catalyst",
            "src.core.gamma_squeeze",
            "src.core.insider_buying",
            "src.core.earnings_tone_drift",
            "src.core.dual_correction",
            "src.core.cross_asset_spillover",
            "src.core.supply_chain_gnn",
            "src.core.range_expansion_breakout",
        ]
        for modname in core_modules:
            try:
                importlib.import_module(modname)
            except Exception as e:
                logger.warning(f"[StrategyRegistry] Module load FAILED for {modname}: {e}")

        for pkg_path in package_paths:
            try:
                pkg = importlib.import_module(pkg_path)
                if hasattr(pkg, "__path__"):
                    for _, modname, _ in pkgutil.walk_packages(
                        pkg.__path__, prefix=pkg.__name__ + "."
                    ):
                        try:
                            importlib.import_module(modname)
                        except Exception as e:
                            logger.debug(f"[StrategyRegistry] Auto-discover skip {modname}: {e}")
            except Exception as e:
                logger.warning(f"[StrategyRegistry] Failed auto-discover package {pkg_path}: {e}")


_registry = StrategyRegistry()


def register_strategy(meta: StrategyMeta):
    """클래스 데코레이터: 전략 엔진을 레지스트리에 자동 등록."""

    def decorator(cls: Type[Any]):
        _registry.register(meta, cls)
        return cls

    return decorator


def get_registry() -> StrategyRegistry:
    return _registry
