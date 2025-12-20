# 🤖 LLM-TradeBot

![Adversarial Intelligence Framework](./docs/adversarial_header.png)

基于 **对抗式决策框架 (Adversarial Decision Framework)** 的智能多 Agent 量化交易机器人。通过市场状态检测、价格位置感知、动态评分校准及多层物理审计，实现高胜率、低回撤的自动化合约交易。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Strategy-Adversarial%20Intelligence-gold.svg)](https://github.com/EthanAlgoX/LLM-TradeBot)

---

## 🛡️ 对抗式决策框架 (Adversarial Decision Framework)

LLM-TradeBot 不再仅仅依赖传统的指标投票，而是采用了“全链路对抗”逻辑。在信号生成后，系统设置了四道严苛的防线：

```mermaid
graph TD
    A[量化信号生成] --> B{第一道防线: 市场状态检测}
    B -- 震荡市/高波动 --> C[降低信心得分 / 强制观望]
    B -- 趋势市 --> D{第二道防线: 价格位置感知}
    D -- 区间中部 --> C
    D -- 支撑/阻力位 --> E{第三道防线: 动态评分校准}
    E -- 信心不足 70% --> C
    E -- 强对齐 --> F{第四道防线: 物理风险审计}
    F -- 盈亏比 < 1.5 --> C
    F -- 审计通过 --> G[🚀 执行买卖订单]
```

### 核心对抗逻辑

1. **市场状态感知 (Regime Detection)**: 自动识别 `Trending`、`Choppy` 或 `Volatile`。在震荡市中自动开启“对抗过滤器”，减少追涨杀跌。
2. **价格位置感知 (Position Awareness)**: 实时计算当前价格在区间的位置。**禁止在区间中部开仓**，只在极致的 R/R（风险回报比）位置出手。
3. **信心度重塑 (Confidence Reshaping)**: 信号强度不再单纯映射为信心。系统会根据市场环境进行惩罚（如：震荡市高位多头信号，信心度将从 80% 降至 5%）。
4. **硬核风控审计 (Risk Audit Agent)**: 拥有最终一票否决权。任何不符合对抗预期的决策（如 R/R < 1.5）都将被物理拦截。

---

## ✨ 核心特性

- 🕵️ **感知优先**: 不同于常规指标派，系统优先判断“当前能不能打”，再判断“怎么打”。
- 🤖 **Multi-Agent 协作**: 4 个高度专业化的 Agent 独立运行，形成对抗验证链条。
- ⚡ **异步并发**: 并发获取多周期数据，确保 5m/15m/1h 的数据在同一快照瞬间对齐。
- 🛡️ **安全至上**: 止损方向修正、资金预演、一票否决机制，为实盘交易保驾护航。
- 📊 **全链路审计**: 每一个决策背后的对抗过程、信心惩罚细节均完整记录，实现真正的“白盒化”决策。

---

## 🚀 快速开始

### 启动流程

![快速开始流程](./docs/quick_start_flow_1766232535088.png)

### 详细步骤

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 设置 API 密钥
./set_api_keys.sh
```

#### 3. 配置交易参数

```bash
# 复制配置文件模板
cp config.example.yaml config.yaml
```

编辑 `config.yaml` 设置交易参数：

- 交易对 (symbol)
- 最大仓位 (max_position_size)
- 杠杆倍数 (leverage)
- 止损止盈比例 (stop_loss_pct, take_profit_pct)

#### 4. 运行交易程序

```bash
# 测试模式 (模拟执行，推荐首次使用)
python main.py --test --mode continuous

# 实盘模式 (谨慎运行！)
python main.py --mode continuous
```

---

## 📁 项目结构

### 目录树形图

![项目结构](./docs/project_structure_tree_1766232597202.png)

### 目录说明

```text
LLM-TradeBot/
├── src/                    # 核心源代码
│   ├── agents/            # 多 Agent 定义 (DataSync, Quant, Decision, Risk)
│   ├── api/               # Binance API 客户端
│   ├── data/              # 数据处理模块 (processor, validator)
│   ├── execution/         # 交易执行引擎
│   ├── features/          # 特征工程模块
│   ├── monitoring/        # 监控和日志
│   ├── risk/              # 风险管理
│   ├── strategy/          # LLM 决策引擎
│   └── utils/             # 工具函数 (DataSaver, TradeLogger 等)
│
├── docs/                  # 项目文档
│   ├── data_flow_analysis.md          # 数据流转分析文档
│   └── *.png                          # 架构图和流程图
│
├── data/                  # 结构化数据存储 (按日期归档)
│   ├── market_data/       # 原始 K 线数据
│   ├── indicators/        # 技术指标
│   ├── features/          # 特征快照
│   ├── decisions/         # 决策结果
│   └── execution/         # 执行记录
│
├── logs/                  # 系统运行日志
├── tests/                 # 单元测试
├── config/                # 配置文件
│
├── main.py                # 统一程序入口 (Multi-Agent 循环)
├── config.yaml            # 交易参数配置
├── .env                   # API 密钥配置
└── requirements.txt       # Python 依赖
```

---

## 🎯 核心架构

### 对抗式 Multi-Agent 协作流程

1. **🕵️ DataSyncAgent**: 异步并发获取多周期 (5m, 15m, 1h) K线及外部量化数据 (Netflow, Long/Short Ratio)，确保计算快照的一致性。
2. **👨‍🔬 QuantAnalystAgent**: 负责多维度信号提取。内部集成 3 个子 Agent（趋势、震荡、情绪），结合原生指标与外部量化数据输出综合分值。
3. **⚖️ DecisionCoreAgent**: **核心对抗层**。集成位置感知、状态检测及 6 信号源加权投票机制，根据市场环境对量化信号进行“洗礼”，输出高质决策。
4. **🛡️ RiskAuditAgent**: **安全终审官**。对 DecisionCore 的输出进行物理隔离审计，确保风险敞口和 R/R 符合对抗要求。
5. **🚀 ExecutionEngine**: 负责交易信号的最后 100 毫秒执行及全生命周期订单追踪。

### 协作时序图

![Multi-Agent 协作时序](./docs/multi_agent_sequence_1766232561419.png)

### 数据流转架构

![数据流转架构](./docs/data_flow_diagram_1766231460411.png)

> 📖 **详细文档**: 查看 [数据流转分析文档](./docs/data_flow_analysis.md) 了解完整的数据流转机制，或查看 [多Agent技术详解](./README_MULTI_AGENT.md) 了解底层实现细节。

---

## 📄 数据全链路审计

### 数据存储结构

![数据存储层级](./docs/data_storage_hierarchy_1766232628608.png)

### 存储组织

系统自动将每一循环的中间过程记录在 `data/` 目录下，按日期组织，方便复盘和调试：

```text
data/
├── market_data/           # 原始多周期 K 线
│   └── {date}/
│       ├── BTCUSDT_5m_{timestamp}.json
│       ├── BTCUSDT_5m_{timestamp}.csv
│       ├── BTCUSDT_5m_{timestamp}.parquet
│       ├── BTCUSDT_15m_{timestamp}.json
│       └── BTCUSDT_1h_{timestamp}.json
│
├── indicators/            # 全量技术指标 DataFrames
│   └── {date}/
│       ├── BTCUSDT_5m_{snapshot_id}.parquet
│       ├── BTCUSDT_15m_{snapshot_id}.parquet
│       └── BTCUSDT_1h_{snapshot_id}.parquet
│
├── features/              # 提取的特征快照
│   └── {date}/
│       ├── BTCUSDT_5m_{snapshot_id}_v1.parquet
│       ├── BTCUSDT_15m_{snapshot_id}_v1.parquet
│       └── BTCUSDT_1h_{snapshot_id}_v1.parquet
│
├── context/               # 量化分析摘要
│   └── {date}/
│       └── BTCUSDT_quant_analysis_{snapshot_id}.json
│
├── llm_logs/              # LLM 输入上下文及 voting 过程
│   └── {date}/
│       └── BTCUSDT_{snapshot_id}.md
│
├── decisions/             # 最终加权投票结果
│   └── {date}/
│       └── BTCUSDT_{snapshot_id}.json
│
└── execution/             # 执行追踪
    └── {date}/
        └── BTCUSDT_{timestamp}.json
```

### 数据格式

- **JSON**: 可读性强，用于配置和决策结果
- **CSV**: 兼容性好，方便导入 Excel 分析
- **Parquet**: 高效压缩，用于大规模时序数据

---

## 🛡️ 安全提示

⚠️ **重要安全措施**:

1. **API 密钥**: 妥善保管，不要提交到版本控制
2. **测试模式先行**: 使用 `--test` 参数运行模拟交易，验证逻辑后再上实盘
3. **风险控制**: 在 `config.yaml` 中设置合理的止损和仓位限制
4. **权限最小化**: 为 API 密钥仅分配必要的合约交易权限
5. **监控告警**: 定期检查 `logs/` 目录，关注异常情况

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 项目概览和快速开始 |
| [数据流转分析](./docs/data_flow_analysis.md) | 完整的数据流转机制和技术细节 |
| [API 密钥指南](./docs/API_KEYS_GUIDE.txt) | API 密钥配置说明 |
| [配置示例](./config.example.yaml) | 交易参数配置模板 |
| [环境变量示例](./.env.example) | 环境变量配置模板 |

---

## 🎉 最新更新

**2025-12-20**:

- ✅ **对抗式决策框架**: 引入 `PositionAnalyzer` 和 `RegimeDetector`，实现环境感知的对抗决策。
- ✅ **信心评分重构**: 实现动态信心惩罚机制，大幅降低震荡市误开仓率。
- ✅ **文档优化**: 更新 README 全面突出对抗式架构，新增 Mermaid 决策流图。
- ✅ **项目重命名**: 正式更名为 `LLM-TradeBot`。
- ✅ **全链路审计**: 实现从数据采集到决策执行的完整中间态归档。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

**由 AI 赋能，专注精准决策，开启智能量化新征程！** 🚀
