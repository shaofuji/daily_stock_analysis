# -*- coding: utf-8 -*-
"""ADX (平均趋向指标，Wilder DMI) 测试。

验证点：
1. _calculate_adx 产出 ADX / +DI / -DI 列
2. 核心区分能力：强趋势数据 ADX 高（≥25），震荡数据 ADX 低（<20）
3. analyze() 正确填充 adx 相关字段并进 to_dict
4. 数据不足时优雅降级

注：与 ATR 测试一致，集成用例 patch get_config 规避 data_provider 重加载链。
"""

import unittest
from unittest.mock import patch

import pandas as pd

from src.stock_analyzer import StockTrendAnalyzer, TrendAnalysisResult


def _make_trending_df(n: int = 50, step: float = 1.0, base: float = 10.0) -> pd.DataFrame:
    """构造强趋势数据（close 每日持续上涨 step，方向一致）。"""
    closes = [base + i * step for i in range(n)]
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "open": closes,
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
        "volume": [1_000_000] * n,
    })


def _make_swinging_df(n: int = 50, base: float = 10.0) -> pd.DataFrame:
    """构造震荡数据（close 交替涨跌，无持续方向）。"""
    closes = [base + (1.0 if i % 2 == 0 else -1.0) for i in range(n)]
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "open": closes,
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
        "volume": [1_000_000] * n,
    })


class StockAnalyzerAdxTestCase(unittest.TestCase):
    @staticmethod
    def _run_analyze(df: pd.DataFrame, code: str = "000001") -> TrendAnalysisResult:
        """跑完整 analyze，patch get_config 规避 data_provider 重加载链。"""
        with patch("src.stock_analyzer.get_config") as cfg:
            cfg.return_value.bias_threshold = 5.0
            return StockTrendAnalyzer().analyze(df, code)

    def test_calculate_adx_produces_columns(self) -> None:
        """_calculate_adx 产出 ADX / +DI / -DI 列。"""
        analyzer = StockTrendAnalyzer()
        df = _make_trending_df(40)
        result = analyzer._calculate_adx(df)
        period = analyzer.ADX_PERIOD
        self.assertIn(f"ADX_{period}", result.columns)
        self.assertIn(f"+DI_{period}", result.columns)
        self.assertIn(f"-DI_{period}", result.columns)

    def test_adx_strong_trend_higher_than_swinging(self) -> None:
        """核心：强趋势数据 ADX 显著高于震荡数据（ADX 能区分趋势/震荡）。"""
        analyzer = StockTrendAnalyzer()
        period = analyzer.ADX_PERIOD
        trending = analyzer._calculate_adx(_make_trending_df(50))
        swinging = analyzer._calculate_adx(_make_swinging_df(50))
        adx_trend = float(trending[f"ADX_{period}"].iloc[-1])
        adx_swing = float(swinging[f"ADX_{period}"].iloc[-1])
        # 相对：趋势 ADX 必须高于震荡 ADX
        self.assertGreater(adx_trend, adx_swing)
        # 绝对：强趋势 ≥ ADX_STRONG_TREND(25)，震荡 < ADX_WEAK_TREND(20)
        self.assertGreaterEqual(adx_trend, analyzer.ADX_STRONG_TREND)
        self.assertLess(adx_swing, analyzer.ADX_WEAK_TREND)

    def test_analyze_populates_adx_fields(self) -> None:
        """analyze() 正确填充 adx / plus_di / minus_di / adx_status / adx_signal。"""
        result = self._run_analyze(_make_trending_df(50))
        self.assertGreater(result.adx, 0)
        self.assertGreaterEqual(result.plus_di, 0)
        self.assertGreaterEqual(result.minus_di, 0)
        self.assertTrue(result.adx_status)
        self.assertTrue(result.adx_signal)

    def test_adx_status_reflects_trend_strength(self) -> None:
        """强趋势数据 adx_status='强趋势'；震荡数据 adx_status='无趋势'。"""
        result_trend = self._run_analyze(_make_trending_df(50))
        self.assertEqual(result_trend.adx_status, "强趋势")
        result_swing = self._run_analyze(_make_swinging_df(50))
        self.assertEqual(result_swing.adx_status, "无趋势")

    def test_analyze_adx_insufficient_data(self) -> None:
        """_analyze_adx 在数据不足时设置提示且不填充 adx。"""
        analyzer = StockTrendAnalyzer()
        df = _make_trending_df(10)  # < ADX_PERIOD * 2 = 28
        result = TrendAnalysisResult(code="000001")
        analyzer._analyze_adx(df, result)
        self.assertEqual(result.adx, 0.0)
        self.assertEqual(result.adx_signal, "数据不足")

    def test_to_dict_contains_adx_fields(self) -> None:
        """to_dict 包含 adx 相关字段。"""
        result = self._run_analyze(_make_trending_df(50))
        payload = result.to_dict()
        for key in ("adx", "plus_di", "minus_di", "adx_status", "adx_signal"):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
