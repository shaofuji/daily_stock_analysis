# 更新日志 (Changelog)

本文件记录 `feature/quant-enhancements` 分支相对上游 `v3.24.1` 的增量改动。

## [Unreleased] - 2026-07-02

### 🎯 主题
引入 **ATR（真实波动幅度）动态止损**：把原本由 LLM 自由生成、不可复现的止损价，
替换为基于个股自身波动率的算法止损（`止损 = 入场价 - 2×ATR`），实现"波动率自适应"。

### ✨ 新增
- **ATR 指标（Wilder 平滑口径）** —— `src/stock_analyzer.py`
  - `StockTrendAnalyzer` 新增 `_calculate_atr` / `_analyze_atr`，挂载到 `analyze()` 主流程
  - `TrendAnalysisResult` 新增 `atr` / `atr_ratio`(占价比) / `atr_signal`(波动等级) 字段
  - 与现有 RSI 采用相同的 Wilder 平滑（`ewm(alpha=1/period, adjust=False)`），口径一致
  - `format_analysis` 新增 ATR 波动率展示区块
  - 类常量：`ATR_PERIOD=14`、`ATR_STOP_MULTIPLIER=2.0`

- **ATR 动态止损覆盖** —— `src/agent/orchestrator.py`
  - 新增 `_apply_atr_stop_loss`，在 `_normalize_dashboard_payload` 的 sniper 段注入
  - 存在 ATR 数据与入场价时，用 `入场价 - 2×ATR` 覆盖 LLM 的止损价
  - 标注 `stop_loss_method="ATR×2"`，便于回测与展示识别来源
  - **回测引擎零改动**：下游 `decision_signal_extractor` → `backtest_service` → `backtest_engine` 透明消费算法止损

- **Agent 工具暴露 ATR** —— `src/agent/tools/analysis_tools.py`
  - `analyze_trend` 工具返回值新增 `atr` / `atr_ratio` / `atr_signal`

- **单元测试** —— `tests/test_stock_analyzer_atr.py`
  - 含 Wilder 稳态收敛验证（True Range 恒定时 ATR 精确收敛）、字段填充、波动等级、数据不足降级、to_dict 完整性
  - 6 用例 + 3 subtest，全部通过

- **效果演示脚本** —— `scripts/demo_atr.py`
  - 无需外部依赖/API key，用模拟 K 线直观对比 ATR 动态止损 vs 固定 5% 止损

### 🛡️ 兼容性
- 无破坏性变更：所有新增 dataclass 字段均有默认值，`to_dict()` 仅增键不删键。
- 现有 MA/MACD/RSI/乖离率/量能指标的计算逻辑完全未动。

### 🧪 测试
- `tests/test_stock_analyzer_atr.py`：6 passed + 3 subtest
- 回归：`tests/test_stock_analyzer_rsi.py`(2+3)、`tests/test_stock_analyzer_bias.py`(7) 全过
