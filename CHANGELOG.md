# 更新日志 (Changelog)

本文件记录 `feature/quant-enhancements` 分支相对上游 `v3.24.1` 的增量改动。

## [Unreleased] - 2026-07-03

### 🎯 主题
为个股分析补齐「趋势三件套」——方向 + 强度 + 波动：
1. **ATR（真实波动幅度）动态止损**：把 LLM 自由生成、不可复现的止损价，替换为基于波动率的算法止损（`止损 = 入场价 - 2×ATR`）。
2. **ADX（平均趋向指标）趋势强度**：新增"强度"维度，区分趋势行情与震荡行情，避免在震荡市用趋势策略反复亏。

### ✨ 新增

#### ATR 动态止损
- **ATR 指标（Wilder 平滑口径）** —— `src/stock_analyzer.py`
  - `StockTrendAnalyzer` 新增 `_calculate_atr` / `_analyze_atr`，挂载到 `analyze()` 主流程
  - `TrendAnalysisResult` 新增 `atr` / `atr_ratio`(占价比) / `atr_signal`(波动等级) 字段
  - 与现有 RSI 采用相同的 Wilder 平滑（`ewm(alpha=1/period, adjust=False)`），口径一致
  - 类常量：`ATR_PERIOD=14`、`ATR_STOP_MULTIPLIER=2.0`
- **ATR 止损覆盖** —— `src/agent/orchestrator.py`
  - 新增 `_apply_atr_stop_loss`，在 `_normalize_dashboard_payload` 的 sniper 段注入
  - 用 `入场价 - 2×ATR` 覆盖 LLM 止损价，标注 `stop_loss_method="ATR×2"`
  - **回测引擎零改动**：下游透明消费算法止损

#### ADX 趋势强度
- **ADX 指标（Wilder DMI 三步法）** —— `src/stock_analyzer.py`
  - `StockTrendAnalyzer` 新增 `_calculate_adx` / `_analyze_adx`，挂载到 `analyze()` 主流程
  - `TrendAnalysisResult` 新增 `adx` / `plus_di` / `minus_di` / `adx_status` / `adx_signal` 字段
  - 复用 ATR 的 True Range 口径，Wilder 平滑一致；DMI 三步：±DM → ±DI → DX → ADX
  - 趋势分级：ADX≥25 强趋势 / 20–25 趋势形成中 / <20 无趋势（震荡）
  - 类常量：`ADX_PERIOD=14`、`ADX_STRONG_TREND=25.0`、`ADX_WEAK_TREND=20.0`

#### 共用
- **Agent 工具暴露 ATR/ADX** —— `src/agent/tools/analysis_tools.py`
  - `analyze_trend` 返回值新增 ATR 与 ADX 全部字段，供 Agent 决策参考
- **单元测试**
  - `tests/test_stock_analyzer_atr.py`：6 用例 + 3 subtest（含 Wilder 稳态收敛验证）
  - `tests/test_stock_analyzer_adx.py`：6 用例（核心：强趋势 ADX≥25、震荡 ADX<20 的区分能力）
- **演示脚本**
  - `scripts/demo_atr.py`：ATR 止损的波动率自适应对比
  - `scripts/demo_indicators.py`：趋势三件套（趋势股 vs 震荡股）

### 🛡️ 兼容性
- 无破坏性变更：所有新增 dataclass 字段均有默认值，`to_dict()` 仅增键不删键。
- 现有 MA/MACD/RSI/乖离率/量能指标的计算逻辑完全未动。

### 🧪 测试
- `tests/test_stock_analyzer_atr.py`：6 passed + 3 subtest
- `tests/test_stock_analyzer_adx.py`：6 passed
- 回归：`tests/test_stock_analyzer_rsi.py`(2+3)、`tests/test_stock_analyzer_bias.py`(7) 全过
- 合计 **22 用例 + 6 subtest 全过**
