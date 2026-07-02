# -*- coding: utf-8 -*-
"""ATR 动态止损效果演示

无需外部数据源/API key，用模拟 K 线对比：
- 低波动股 / 中波动股 / 高波动股 的 ATR 差异
- ATR 动态止损（入场价 - 2×ATR）vs 固定 5% 止损

体现"波动率自适应"的核心价值：低波动股止损收紧（少亏），高波动股止损放宽
（避免被正常波动洗出），相比"LLM 拍脑袋止损"或"固定百分比止损"更科学。
"""

import os
import sys
from unittest.mock import patch

# 把项目根加入 sys.path，便于在子目录运行时 import src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src.stock_analyzer import StockTrendAnalyzer


def make_stock(start: float, drift: float, volatility: float, n: int = 60, seed: int = 42) -> pd.DataFrame:
    """生成带趋势与波动的模拟日 K 线。"""
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, volatility, n)
    closes = start * np.cumprod(1 + returns)
    intraday = np.abs(rng.normal(0, volatility, n)) * closes  # 日内振幅
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "open": closes,
        "high": closes + intraday * 0.6,
        "low": closes - intraday * 0.6,
        "close": closes,
        "volume": rng.integers(1_000_000, 5_000_000, n),
    })


def main() -> None:
    analyzer = StockTrendAnalyzer()
    # patch get_config，规避 data_provider 重加载链（演示只看 ATR 算法效果）
    with patch("src.stock_analyzer.get_config") as cfg:
        cfg.return_value.bias_threshold = 5.0

        cases = [
            ("稳健蓝筹（低波动）", 50.0, 0.001, 0.012),
            ("科技成长（中波动）", 30.0, 0.0015, 0.025),
            ("题材热门（高波动）", 10.0, 0.002, 0.045),
        ]
        for name, start, drift, vol in cases:
            df = make_stock(start, drift, vol)
            result = analyzer.analyze(df, "demo")
            entry = result.current_price
            atr_stop = entry - 2 * result.atr
            fixed_stop = entry * 0.95
            print(f"\n{'=' * 60}")
            print(f" {name}")
            print(f"{'=' * 60}")
            print(f"  现价:            {entry:.2f}")
            print(f"  ATR(14):         {result.atr:.3f}    (占价 {result.atr_ratio:.2f}%)")
            print(f"  波动信号:        {result.atr_signal}")
            print(f"  趋势/MACD/RSI:   {result.trend_status.value} | {result.macd_signal} | RSI(12)={result.rsi_12:.1f}")
            print(f"  {'- ' * 28}")
            print(f"  入场价(=现价):   {entry:.2f}")
            print(f"  ATR动态止损:     {atr_stop:.2f}    (回撤 {(entry - atr_stop) / entry * 100:.2f}%)  ← 波动率自适应")
            print(f"  固定5%止损:      {fixed_stop:.2f}    (回撤 5.00%)")

    print(f"\n{'=' * 60}")
    print(" 结论：ATR 止损 = 入场价 - 2×ATR。")
    print("  低波动股 ATR 小 → 止损收紧（少亏，不被噪音触发）；")
    print("  高波动股 ATR 大 → 止损放宽（避免被正常波动洗出）。")
    print("  这就是相对『LLM 拍脑袋止损』或『固定 5% 止损』的核心优势。")


if __name__ == "__main__":
    main()
