"""
DeepSeek 策略推理引擎
"""
import json
from typing import Dict, Optional
from openai import OpenAI
from src.config import config
from src.utils.logger import log
from src.strategy.llm_parser import LLMOutputParser
from src.strategy.decision_validator import DecisionValidator


class StrategyEngine:
    """DeepSeek驱动的策略决策引擎"""
    
    def __init__(self):
        self.api_key = config.deepseek.get('api_key')
        self.base_url = config.deepseek.get('base_url', 'https://api.deepseek.com')
        self.model = config.deepseek.get('model', 'deepseek-chat')
        self.temperature = config.deepseek.get('temperature', 0.3)
        self.max_tokens = config.deepseek.get('max_tokens', 2000)
        
        # 初始化OpenAI客户端（DeepSeek兼容OpenAI API）
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 初始化解析器和验证器
        self.parser = LLMOutputParser()
        self.validator = DecisionValidator({
            'max_leverage': config.risk.get('max_leverage', 5),
            'max_position_pct': config.risk.get('max_total_position_pct', 30.0),
            'min_risk_reward_ratio': 2.0
        })
        
        log.info("DeepSeek策略引擎初始化完成（已集成结构化输出解析）")
    
    def make_decision(self, market_context_text: str, market_context_data: Dict) -> Dict:
        """
        基于市场上下文做出交易决策
        
        Args:
            market_context_text: 格式化的市场上下文文本
            market_context_data: 原始市场数据
            
        Returns:
            决策结果字典
        """
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(market_context_text)
        
        # 记录 LLM 输入
        log.llm_input("正在发送市场数据到 DeepSeek...", market_context_text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 获取原始响应
            content = response.choices[0].message.content
            
            # 使用新解析器解析结构化输出
            parsed = self.parser.parse(content)
            decision = parsed['decision']
            reasoning = parsed['reasoning']
            
            # 标准化 action 字段
            if 'action' in decision:
                decision['action'] = self.parser.normalize_action(decision['action'])
            
            # 验证决策
            is_valid, errors = self.validator.validate(decision)
            if not is_valid:
                log.warning(f"LLM 决策验证失败: {errors}")
                log.warning(f"原始决策: {decision}")
                return self._get_fallback_decision(market_context_data)
            
            # 记录 LLM 输出
            log.llm_output("DeepSeek 返回决策结果", decision)
            if reasoning:
                log.info(f"推理过程:\n{reasoning}")
            
            # 记录决策
            log.llm_decision(
                action=decision.get('action', 'hold'),
                confidence=decision.get('confidence', 0),
                reasoning=decision.get('reasoning', reasoning)
            )
            
            # 添加元数据
            decision['timestamp'] = market_context_data['timestamp']
            decision['symbol'] = market_context_data['symbol']
            decision['model'] = self.model
            decision['raw_response'] = content
            decision['reasoning_detail'] = reasoning
            decision['validation_passed'] = True
            
            return decision
            
        except Exception as e:
            log.error(f"LLM决策失败: {e}")
            # 返回保守决策
            return self._get_fallback_decision(market_context_data)
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        
        return """你是一个专业的加密货币合约交易 AI Agent，采用科学严谨的量化交易方法论。

## 🎯 核心目标（按优先级排序）
1. **本金安全第一** - 单笔交易风险永不超过账户的1.5%，这是生存的底线
2. **追求长期稳定复利** - 目标年化夏普比率 > 2.0，而非短期暴利
3. **风控纪律严格执行** - 任何情况下不得违反预设风险参数

## 📋 输出格式要求（必须严格遵守）

你的输出必须使用以下结构化格式：

<reasoning>
在这里写出你的分析思路：
- 多周期趋势分析（1h/15m/5m）
- 关键指标判断（RSI/MACD/EMA）
- 风险评估（ATR/成交量/支撑阻力）
- 入场理由和时机
- 止损止盈设置逻辑
</reasoning>

<decision>
{
  "symbol": "BTCUSDT",
  "action": "open_long",
  "leverage": 2,
  "position_size_usd": 200.0,
  "stop_loss": 84710.0,
  "take_profit": 88580.0,
  "confidence": 75,
  "risk_usd": 30.0
}
</decision>

## 📊 字段说明

### 必填字段
- **symbol**: 交易对 (如 "BTCUSDT")
- **action**: 必须是以下之一
  * open_long: 开多仓
  * open_short: 开空仓
  * close_long: 平多仓
  * close_short: 平空仓
  * close_position: 平仓（通用）
  * hold: 观望
  * wait: 等待
- **confidence**: 信心度 0-100

### 开仓时必填
- **leverage**: 杠杆倍数 (1-5)
- **position_size_usd**: 仓位大小（美元）
- **stop_loss**: 止损价格（绝对价格，非百分比）
- **take_profit**: 止盈价格（绝对价格，非百分比）
- **risk_usd**: 风险金额

## ⚠️ 关键验证规则（必须遵守）

### 1. 数值格式
✅ 正确: "stop_loss": 84710.0
❌ 错误: "stop_loss": "86000 * 0.985"
❌ 错误: "stop_loss": "84,710"

⚠️ 所有数值必须是计算后的数字，不能是公式或表达式
⚠️ 数字不能包含千位分隔符逗号

### 2. 止损方向
✅ 做多: stop_loss < entry_price
✅ 做空: stop_loss > entry_price

⚠️ 止损方向必须正确，否则会被系统拦截

### 3. 风险回报比
⚠️ 必须 ≥ 2.0:1
计算公式: (take_profit - entry) / (entry - stop_loss) >= 2.0

## 📊 多周期分析框架

系统已为你准备了 **5m/15m/1h** 三个周期的完整技术分析数据：

### 周期权重与作用
- **1h 周期（权重40%）**: 主趋势判断，决定多空方向，禁止逆1h趋势重仓
- **15m 周期（权重35%）**: 中期共振验证，过滤5m假突破，确认入场时机
- **5m 周期（权重25%）**: 精确入场点位，短期动量确认，止损止盈设置

### 多周期共振原则
- **强信号**: 三个周期趋势一致（如：1h上涨 + 15m上涨 + 5m上涨）→ 可考虑加大仓位
- **矛盾信号**: 大周期与小周期冲突（如：1h下跌 + 5m上涨）→ 小仓位或观望
- **震荡市**: 三个周期趋势不一致且RSI在40-60区间 → 务必观望

## 🔍 技术指标解读

### 趋势指标（方向判断）
- **SMA_20 vs SMA_50**: 金叉看多，死叉看空
- **EMA_12 vs EMA_26**: 快速趋势确认
- **价格相对位置**: 价格在均线上方=强势，下方=弱势

### 动量指标（力度判断）
- **RSI**: <30超卖，>70超买，40-60震荡
- **MACD**: 柱状图扩大=动量增强，收缩=动量减弱
- **MACD信号线交叉**: 提前预警趋势变化

### 波动率指标（风险评估）
- **ATR**: 高ATR=高波动，需降低仓位和杠杆
- **布林带宽度**: 收窄=震荡蓄势，放宽=趋势启动

### 成交量指标（真实性验证）
- **Volume vs SMA_20**: 放量突破=真突破，缩量=假突破
- **OBV**: 价涨量涨=健康，价涨量跌=背离警告

## ⚠️ 决策铁律

### 1. 风险敞口控制
- 单笔风险 ≤ 1.5% 账户净值（硬性上限）
- 总持仓 ≤ 30% 账户净值
- 高波动环境（ATR > 历史均值2倍）：降低仓位50%

### 2. 趋势对齐原则
- **禁止逆1h趋势重仓**：如1h明确下跌，不允许开多仓位>5%
- **小周期仅在大周期支持下才可加仓**

### 3. 动态止损止盈
- **做多止损逻辑**: stop_loss_price < entry_price
- **做空止损逻辑**: stop_loss_price > entry_price
- **风险收益比**: 必须 ≥ 2:1

### 4. 极端市场规避
- RSI在所有周期都 > 80 或 < 20 → 等待回归
- 流动性（成交量） < 20周期均值50% → 避免交易

## 📝 输出示例

### 示例 1: 开多仓

<reasoning>
多周期分析：
- 1h: EMA12 > EMA26，MACD柱状图为正，RSI 65，上涨趋势确立
- 15m: 突破87000阻力位，成交量放大至20周期均值的1.8倍
- 5m: RSI从70回调至45，健康回踩，接近支撑位85500

风险评估：
- ATR 245，低于历史均值，波动率中等
- 成交量充足，流动性良好
- 无极端指标

入场逻辑：
- 三周期趋势共振做多
- 当前5m回调提供低风险入场点
- 支撑位85500明确

止损止盈：
- 止损设在支撑位下方1.5倍ATR: 84710（做多止损<入场价✓）
- 止盈设在阻力位88000附近
- 风险回报比: (88580-86000)/(86000-84710) = 2.0 ✓
</reasoning>

<decision>
{
  "symbol": "BTCUSDT",
  "action": "open_long",
  "leverage": 2,
  "position_size_usd": 200.0,
  "stop_loss": 84710.0,
  "take_profit": 88580.0,
  "confidence": 75,
  "risk_usd": 30.0
}
</decision>

### 示例 2: 观望

<reasoning>
多周期分析：
- 1h: EMA12 (88239.52) 微弱高于 EMA26 (88238.41)，差值仅1.11
- 15m: 趋势不明确，MACD接近零轴
- 5m: 震荡，无明确方向

综合判断：
- 多周期信号微弱，缺乏强烈方向性
- RSI均在中性区间，无超买超卖
- 建议观望，等待更明确的入场信号
</reasoning>

<decision>
{
  "symbol": "BTCUSDT",
  "action": "hold",
  "confidence": 45,
  "leverage": 1,
  "position_size_usd": 0,
  "stop_loss": 0,
  "take_profit": 0,
  "risk_usd": 0
}
</decision>

## 🚨 常见错误提醒

❌ **错误1**: 做空时设置 stop_loss < entry_price（方向反了！）
✅ **正确**: 做空时 stop_loss > entry_price

❌ **错误2**: 使用公式 "stop_loss": "price * 0.98"
✅ **正确**: 使用计算后的数字 "stop_loss": 84280.0

❌ **错误3**: 风险回报比 < 2.0
✅ **正确**: 确保 (TP-Entry)/(Entry-SL) >= 2.0

现在请严格按照上述格式输出你的分析和决策。
"""
    
    def _build_user_prompt(self, market_context: str) -> str:
        """构建用户提示词"""
        
        return f"""# 📊 实时市场数据（已完成技术分析）

以下是系统为你准备的 **5m/15m/1h** 三个周期的完整市场状态：

{market_context}

---

## 🎯 你的任务

请按照以下流程进行分析和决策：

### 1️⃣ 多周期趋势判断（必做）
- 分析 **1h** 周期的主趋势方向（SMA/MACD）
- 检查 **15m** 周期是否与1h共振
- 观察 **5m** 周期的短期动量

### 2️⃣ 关键指标确认（必做）
- 各周期的 RSI 是否在合理区间（30-70）？
- MACD 柱状图是否扩大（动量增强）还是收缩？
- 成交量是否支持当前趋势？
- ATR 是否显示异常波动？

### 3️⃣ 风险评估（必做）
- 是否存在极端指标（RSI>80或<20）？
- 多周期趋势是否矛盾？
- 流动性（成交量）是否充足？

### 4️⃣ 入场时机判断（如果开仓）
- 当前价格相对支撑/阻力位在哪里？
- 是否有明确的入场信号（突破/回调/交叉）？
- 风险收益比是否≥2？

### 5️⃣ 止损止盈设置（如果开仓）
- 根据ATR计算合理的止损幅度
- **验证止损方向**：
  - 做多：stop_loss_price < entry_price
  - 做空：stop_loss_price > entry_price
- 止盈至少是止损的2倍

---

## ⚡ 输出要求

1. **严格JSON格式**，包含所有必填字段
2. **analysis字段必须包含**：
   - `multi_timeframe_trend`: 各周期趋势描述
   - `timeframe_confluence`: 多周期共振程度
   - `technical_signals`: 关键技术信号
   - `risk_assessment`: 风险评估
   - `stop_loss_rationale`: 止损逻辑（必须说明方向验证）
3. **reasoning字段**：一句话总结（50字内）
4. **confidence字段**：诚实评估，<50时必须hold

---

## 🚨 特别提醒

- ⚠️ **做空止损方向**：stop_loss_price **必须大于** entry_price
- ⚠️ **做多止损方向**：stop_loss_price **必须小于** entry_price
- ⚠️ **逆大周期重仓**：1h下跌时不允许开多仓>5%
- ⚠️ **极端指标规避**：RSI>80或<20时谨慎开仓
- ⚠️ **风险收益比**：必须≥2，否则不值得交易

现在请开始分析并输出JSON格式的决策。
"""
    
    def _get_fallback_decision(self, context: Dict) -> Dict:
        """
        获取兜底决策（当LLM失败时）
        
        返回保守的hold决策
        """
        return {
            'action': 'hold',
            'symbol': context.get('symbol', 'BTCUSDT'),
            'confidence': 0,
            'leverage': 1,
            'position_size_pct': 0,
            'stop_loss_pct': 1.0,
            'take_profit_pct': 2.0,
            'reasoning': 'LLM决策失败，采用保守策略观望',
            'timestamp': context.get('timestamp'),
            'is_fallback': True
        }
    
    def validate_decision(self, decision: Dict) -> bool:
        """
        验证决策格式是否正确
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'action', 'symbol', 'confidence', 'leverage',
            'position_size_pct', 'stop_loss_pct', 'take_profit_pct', 'reasoning'
        ]
        
        # 检查必需字段
        for field in required_fields:
            if field not in decision:
                log.error(f"决策缺少必需字段: {field}")
                return False
        
        # 检查action合法性
        valid_actions = [
            'open_long', 'open_short', 'close_position',
            'add_position', 'reduce_position', 'hold'
        ]
        if decision['action'] not in valid_actions:
            log.error(f"无效的action: {decision['action']}")
            return False
        
        # 检查数值范围
        if not (0 <= decision['confidence'] <= 100):
            log.error(f"confidence超出范围: {decision['confidence']}")
            return False
        
        if not (1 <= decision['leverage'] <= config.risk.get('max_leverage', 5)):
            log.error(f"leverage超出范围: {decision['leverage']}")
            return False
        
        if not (0 <= decision['position_size_pct'] <= 100):
            log.error(f"position_size_pct超出范围: {decision['position_size_pct']}")
            return False
        
        return True
