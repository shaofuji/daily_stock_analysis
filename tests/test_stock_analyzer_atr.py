# -*- coding: utf-8 -*-
"""ATR (Average True Range, Wilder 平滑) 指标测试。

验证点：
1. _calculate_atr 产出 ATR_{period} 列，Wilder 平滑口径
2. 当 True Range 恒定时，ATR 精确收敛到该 TR 值（独立验证算法正确性）
3. analyze() 正确填充 atr / atr_ratio / atr_signal 并进 to_dict
4. 数据不足时优雅降级

注：完整 analyze() 会触发 get_config()，进而拉起 data_provider 重加载链
（含 akshare/tushare/longbridge 等重数据源库）。为保持单元测试轻量、聚焦
ATR 逻辑本身，集成用例用 patch 规避 get_config 的真实加载。
"""

import unittest
from unittest.mock import patch

import pandas as pd

from src.stock_analyzer import StockTrendAnalyzer, TrendAnalysisResult


def _make_constant_range_df(n: int, daily_range: float = 1.0, base: float = 10.0) -> pd.DataFrame:
    """构造 True Range 恒定的 K 线序列。

    每日 close 恒为 base，high = base + r/2，low = base - r/2：
    - H - L = r
    - |H - prev_close| = r/2（prev_close = base）
    - |L - prev_close| = r/2
    故 TR = max(r, r/2, r/2) = r（恒定），Wilder ATR 应精确收敛到 r。
    """
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "open": [base] * n,
        "high": [base + daily_range / 2] * n,
        "low": [base - daily_range / 2] * n,
        "close": [base] * n,
        "volume": [1_000_000] * n,
    })


class StockAnalyzerAtrTestCase(unittest.TestCase):
    @staticmethod
    def _run_analyze(df: pd.DataFrame, code: str = "000001") -> TrendAnalysisResult:
        """跑完整 analyze，patch get_config 规避 data_provider 重加载链。"""
        with patch("src.stock_analyzer.get_config") as mock_cfg:
            mock_cfg.return_value.bias_threshold = 5.0
            return StockTrendAnalyzer().analyze(df, code)

    def test_calculate_atr_produces_column(self) -> None:
        """_calculate_atr 产出 ATR_{period} 列。"""
        analyzer = StockTrendAnalyzer()
        df = _make_constant_range_df(30)
        result = analyzer._calculate_atr(df)
        self.assertIn(f"ATR_{analyzer.ATR_PERIOD}", result.columns)

    def test_atr_converges_to_constant_true_range(self) -> None:
        """True Range 恒定时，Wilder ATR 精确收敛到该 TR 值（独立验证算法）。"""
        analyzer = StockTrendAnalyzer()
        for daily_range in (1.0, 2.5, 0.3):
            with self.subTest(daily_range=daily_range):
                df = _make_constant_range_df(30, daily_range=daily_range)
                result = analyzer._calculate_atr(df)
                latest_atr = float(result[f"ATR_{analyzer.ATR_PERIOD}"].iloc[-1])
                self.assertAlmostEqual(latest_atr, daily_range, places=6)

    def test_analyze_populates_atr_fields(self) -> None:
        """analyze() 正确填充 atr / atr_ratio / atr_signal。"""
        # daily_range=1.0, base=10.0 → ATR=1.0, atr_ratio=1.0/10.0×100=10.0
        df = _make_constant_range_df(30, daily_range=1.0, base=10.0)
        result = self._run_analyze(df)
        self.assertAlmostEqual(result.atr, 1.0, places=6)
        self.assertAlmostEqual(result.atr_ratio, 10.0, places=4)
        self.assertTrue(result.atr_signal)

    def test_atr_signal_reflects_volatility_level(self) -> None:
        """atr_signal 按波动率百分比给出合理等级描述。"""
        # 高波动：daily_range=2.0, base=10.0 → atr_ratio=20% → "波动剧烈"
        df = _make_constant_range_df(30, daily_range=2.0, base=10.0)
        result = self._run_analyze(df)
        self.assertIn("剧烈", result.atr_signal)

    def test_analyze_atr_insufficient_data(self) -> None:
        """_analyze_atr 在数据不足时设置提示且不填充 atr。"""
        analyzer = StockTrendAnalyzer()
        df = _make_constant_range_df(5)  # < ATR_PERIOD + 1
        result = TrendAnalysisResult(code="000001")
        analyzer._analyze_atr(df, result)
        self.assertEqual(result.atr, 0.0)
        self.assertEqual(result.atr_signal, "数据不足")

    def test_to_dict_contains_atr_fields(self) -> None:
        """to_dict 包含 atr 相关字段。"""
        df = _make_constant_range_df(30)
        result = self._run_analyze(df)
        payload = result.to_dict()
        for key in ("atr", "atr_ratio", "atr_signal"):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
