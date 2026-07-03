# -*- coding: utf-8 -*-
"""趋势三件套演示：方向(trend_status) + 强度(ADX) + 波动(ATR)

用模拟数据对比「趋势股」与「震荡股」，体现三件套如何配合：
- 方向（trend_status / MA 排列）：多头还是空头
- 强度（ADX）：是趋势行情还是震荡行情 ← 本次新增的核心维度
- 波动（ATR）：价格波动幅度，定止损

核心洞察：ADX 低（<20，震荡）时，即使 MA 排列偶尔多头，趋势策略也易反复亏——
这正是「只看 MA 排列」会踩的坑，ADX 补上了『强度』维度。
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src.stock_analyzer import StockTrendAnalyzer


def make_trending(n: int = 60, base: float = 10.0, drift: float = 0.003, vol: float = 0.015, seed: int = 42) -> pd.DataFrame:
    """趋势股：持续上行（带正常波动）。"""
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    closes = base * np.cumprod(1 + rets)
    intra = np.abs(rng.normal(0, vol, n)) * closes
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "open": closes, "high": closes + intra * 0.6, "low": closes - intra * 0.6,
        "close": closes, "volume": rng.integers(1_000_000, 5_000_000, n),
    })


def make_swinging(n: int = 60, base: float = 10.0, amp: float = 0.04, seed: int = 7) -> pd.DataFrame:
    """震荡股：在区间内来回波动，无明显趋势。"""
    rng = np.random.default_rng(seed)
    phase = np.sin(np.linspace(0, 6 * np.pi, n)) * amp  # 多周期振荡，制造来回
    noise = rng.normal(0, 0.005, n)
    closes = base * (1 + phase + noise)
    intra = np.abs(rng.normal(0, amp / 3, n)) * closes
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "open": closes, "high": closes + intra * 0.6, "low": closes - intra * 0.6,
        "close": closes, "volume": rng.integers(1_000_000, 5_000_000, n),
    })


def main() -> None:
    analyzer = StockTrendAnalyzer()
    with patch("src.stock_analyzer.get_config") as cfg:
        cfg.return_value.bias_threshold = 5.0
        cases = [
            ("趋势股（持续上行）", make_trending()),
            ("震荡股（来回波动）", make_swinging()),
        ]
        for name, df in cases:
            r = analyzer.analyze(df, "demo")
            print(f"\n{'=' * 60}")
            print(f" {name}")
            print(f"{'=' * 60}")
            print(f"  📈 方向  trend_status: {r.trend_status.value}  |  {r.ma_alignment}")
            print(f"  💪 强度  ADX(14): {r.adx:.1f}   (+DI {r.plus_di:.1f} / -DI {r.minus_di:.1f})")
            print(f"           → {r.adx_signal}")
            print(f"  🌊 波动  ATR(14): {r.atr:.3f}  (占价 {r.atr_ratio:.2f}%)")
            print(f"           → {r.atr_signal}")
            print(f"  {'- ' * 28}")
            if r.adx < 20:
                print(f"  🎯 综合：震荡行情 → 即使 MA 偶尔多头，趋势策略也易反复亏，宜区间操作或观望")
            elif r.adx >= 25:
                stop = r.current_price - 2 * r.atr
                print(f"  🎯 综合：趋势行情 → 方向明确，适合顺势；ATR 止损 = {r.current_price:.2f} - 2×{r.atr:.2f} = {stop:.2f}")
            else:
                print(f"  🎯 综合：趋势形成中 → 观望方向选择")

    print(f"\n{'=' * 60}")
    print(" 趋势三件套：方向(MA排列) + 强度(ADX) + 波动(ATR)")
    print("  只看 MA 排列会在震荡市踩坑（金叉买在顶、死叉卖在底）；")
    print("  ADX 补上『强度』——ADX<20 时无论 MA 多好看都该收手。")


if __name__ == "__main__":
    main()
