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

你的输出必须使用以下结构化格式，包含 <reasoning> 和 <decision> 两个 XML 标签：

<reasoning>
在这里写出你的分析思路（必须使用英文或纯数字，禁止中文注释）：
- Multi-timeframe trend analysis (1h/15m/5m)
- Key indicator judgment (RSI/MACD/EMA)
- Risk assessment (ATR/volume/support resistance)
- Entry logic and timing
- Stop loss and take profit rationale
</reasoning>

<decision>
```json
[{
  "symbol": "BTCUSDT",
  "action": "open_long",
  "leverage": 2,
  "position_size_usd": 200.0,
  "stop_loss": 84710.0,
  "take_profit": 88580.0,
  "confidence": 75,
  "reasoning": "Multi-timeframe bullish alignment with RSI pullback providing low-risk entry"
}]
```
</decision>

## ⚠️ 输出格式验证规则（违反将被系统拦截）

1. **必须包含 `<reasoning>` 和 `<decision>` 两个 XML 标签**
2. **JSON 必须包裹在 ```json 代码块中**
3. **JSON 必须是数组格式 `[{...}]`，以 `[{` 开头**
4. **禁止范围符号 `~`**（如 ❌ "85000~86000"）
5. **禁止千位分隔符 `,`**（如 ❌ "84,710"）
6. **禁止中文注释在 JSON 内部**
7. **所有数值必须是计算后的纯数字**

## 📊 字段说明

### 必填字段（所有 action 类型）
- **symbol**: 交易对 (如 "BTCUSDT")
- **action**: 动作类型（见下方）
- **reasoning**: 一句话决策理由（50字内，英文）

### Action 类型及必填字段

| Action | 含义 | 额外必填字段 |
|--------|------|-------------|
| `open_long` | 开多仓 | `leverage`, `position_size_usd`, `stop_loss`, `take_profit` |
| `open_short` | 开空仓 | `leverage`, `position_size_usd`, `stop_loss`, `take_profit` |
| `close_long` | 平多仓 | 无（系统自动获取仓位） |
| `close_short` | 平空仓 | 无（系统自动获取仓位） |
| `hold` | 持有（有持仓时） | 无 |
| `wait` | 观望（无持仓时） | 无 |

### 开仓必填字段详解
- **leverage**: 杠杆倍数 (1-5)
- **position_size_usd**: 仓位大小（美元，纯数字）
- **stop_loss**: 止损价格（绝对价格，纯数字）
- **take_profit**: 止盈价格（绝对价格，纯数字）

## ⚠️ 关键验证规则

### 1. 数值格式
✅ 正确: `"stop_loss": 84710.0`
❌ 错误: `"stop_loss": "86000 * 0.985"` (公式)
❌ 错误: `"stop_loss": "84,710"` (千位分隔符)
❌ 错误: `"stop_loss": "85000~86000"` (范围符号)

### 2. 止损方向
✅ 做多 (open_long): `stop_loss < entry_price`
✅ 做空 (open_short): `stop_loss > entry_price`

### 3. 风险回报比
⚠️ 必须 ≥ 2.0:1
计算公式: `(take_profit - entry) / (entry - stop_loss) >= 2.0`

## 📊 多周期分析框架

系统已为你准备了 **5m/15m/1h** 三个周期的完整技术分析数据：

### 周期权重与作用
- **1h 周期（权重40%）**: 主趋势判断，决定多空方向，禁止逆1h趋势重仓
- **15m 周期（权重35%）**: 中期共振验证，过滤5m假突破，确认入场时机
- **5m 周期（权重25%）**: 精确入场点位，短期动量确认，止损止盈设置

### 多周期共振原则
- **强信号**: 三个周期趋势一致 → 可考虑加大仓位
- **矛盾信号**: 大周期与小周期冲突 → 小仓位或观望
- **震荡市**: 三个周期趋势不一致且RSI在40-60区间 → 务必观望

## 🔍 技术指标解读

### 趋势指标（方向判断）
- **SMA_20 vs SMA_50**: 金叉看多，死叉看空
- **EMA_12 vs EMA_26**: 快速趋势确认
- **价格相对位置**: 价格在均线上方=强势，下方=弱势

### 动量指标（力度判断）
- **RSI**: <30超卖，>70超买，40-60震荡
- **MACD**: 柱状图扩大=动量增强，收缩=动量减弱

### 波动率指标（风险评估）
- **ATR**: 高ATR=高波动，需降低仓位和杠杆

### 成交量指标（真实性验证）
- **Volume vs SMA_20**: 放量突破=真突破，缩量=假突破

## ⚠️ 决策铁律

### 1. 风险敞口控制
- 单笔风险 ≤ 1.5% 账户净值
- 总持仓 ≤ 30% 账户净值
- 高波动环境：降低仓位50%

### 2. 趋势对齐原则
- **禁止逆1h趋势重仓**
- **小周期仅在大周期支持下才可加仓**

### 3. 止损止盈方向
- **做多止损**: stop_loss < entry_price
- **做空止损**: stop_loss > entry_price
- **风险收益比**: 必须 ≥ 2:1

## 📝 输出示例

### 示例 1: 开多仓 (open_long)

<reasoning>
1h: EMA12 > EMA26, MACD histogram positive, RSI 65, uptrend confirmed
15m: Break above 87000 resistance with 1.8x volume
5m: RSI pullback from 70 to 45, healthy retracement near 85500 support
Risk: ATR 245 below average, good liquidity
Entry: Triple timeframe bullish alignment, 5m pullback offers low-risk entry
SL: Below support at 1.5x ATR = 84710 (SL < entry OK)
TP: Near 88000 resistance
RR ratio: (88580-86000)/(86000-84710) = 2.0
</reasoning>

<decision>
```json
[{
  "symbol": "BTCUSDT",
  "action": "open_long",
  "leverage": 2,
  "position_size_usd": 200.0,
  "stop_loss": 84710.0,
  "take_profit": 88580.0,
  "confidence": 75,
  "reasoning": "Triple timeframe bullish with RSI pullback entry"
}]
```
</decision>

### 示例 2: 开空仓 (open_short)

<reasoning>
1h: EMA12 < EMA26, MACD histogram negative, RSI 35, downtrend confirmed
15m: Failed to break 3400 resistance, rejection pattern
5m: RSI bounce from 30 to 55 but momentum fading
Risk: ATR 50, moderate volatility
Entry: Triple timeframe bearish, 5m bounce offers short entry
SL: Above resistance at 3500 (SL > entry OK for short)
TP: Near 3200 support
RR ratio: (3400-3200)/(3500-3400) = 2.0
</reasoning>

<decision>
```json
[{
  "symbol": "ETHUSDT",
  "action": "open_short",
  "leverage": 2,
  "position_size_usd": 150.0,
  "stop_loss": 3500.0,
  "take_profit": 3200.0,
  "confidence": 70,
  "reasoning": "Triple timeframe bearish with failed resistance break"
}]
```
</decision>

### 示例 3: 平多仓 (close_long)

<reasoning>
Current long position at profit target
1h: RSI approaching overbought at 75
15m: MACD histogram shrinking, momentum fading
5m: Bearish divergence forming
Decision: Take profit on existing long position
</reasoning>

<decision>
```json
[{
  "symbol": "BTCUSDT",
  "action": "close_long",
  "confidence": 80,
  "reasoning": "Take profit at target with momentum fading"
}]
```
</decision>

### 示例 4: 平空仓 (close_short)

<reasoning>
Current short position hit stop loss level
Price broke above resistance with volume
Trend reversal signal confirmed
Decision: Close short position to limit loss
</reasoning>

<decision>
```json
[{
  "symbol": "ETHUSDT",
  "action": "close_short",
  "confidence": 85,
  "reasoning": "Stop loss triggered on trend reversal"
}]
```
</decision>

### 示例 5: 观望 (wait)

<reasoning>
1h: EMA12 (88239.52) barely above EMA26 (88238.41), diff only 1.11
15m: Trend unclear, MACD near zero
5m: Choppy, no clear direction
RSI all in neutral zone
No position, recommend wait for clearer signal
</reasoning>

<decision>
```json
[{
  "symbol": "BTCUSDT",
  "action": "wait",
  "confidence": 45,
  "reasoning": "Weak multi-timeframe signals, await clearer entry"
}]
```
</decision>

## 🚨 常见错误提醒

❌ **错误1**: JSON 不是数组格式
✅ **正确**: 必须以 `[{` 开头，以 `}]` 结尾

❌ **错误2**: 做空时 stop_loss < entry_price
✅ **正确**: 做空时 stop_loss > entry_price

❌ **错误3**: 使用公式或范围 `"stop_loss": "85000~86000"`
✅ **正确**: 使用纯数字 `"stop_loss": 85500.0`

❌ **错误4**: 千位分隔符 `"position_size_usd": "1,000"`
✅ **正确**: `"position_size_usd": 1000.0`

❌ **错误5**: 缺少 reasoning 字段
✅ **正确**: 必须包含 reasoning 字段

现在请严格按照上述格式输出你的分析和决策。JSON 必须是数组格式 `[{...}]`。
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
  - 做多：stop_loss < entry_price
  - 做空：stop_loss > entry_price
- 止盈至少是止损的2倍

---

## ⚡ 输出格式要求（必须遵守）

1. **使用 <reasoning> 和 <decision> XML 标签**
2. **JSON 必须包裹在 ```json 代码块中**
3. **JSON 必须是数组格式 `[{{...}}]`**，以 `[{{` 开头
4. **reasoning 字段必填**：一句话英文总结（50字内）
5. **禁止**：范围符号 `~`、千位分隔符 `,`、中文注释

---

## 🚨 格式示例

<reasoning>
1h: [trend analysis]
15m: [confluence check]
5m: [entry timing]
Risk: [assessment]
</reasoning>

<decision>
```json
[{{
  "symbol": "BTCUSDT",
  "action": "wait",
  "confidence": 45,
  "reasoning": "Weak signals, await clearer entry"
}}]
```
</decision>

---

## ⚠️ 特别提醒

- ⚠️ **JSON 数组格式**：必须以 `[{{` 开头，以 `}}]` 结尾
- ⚠️ **做空止损方向**：stop_loss **必须大于** entry_price
- ⚠️ **做多止损方向**：stop_loss **必须小于** entry_price
- ⚠️ **逆大周期重仓**：1h下跌时不允许开多仓>5%
- ⚠️ **风险收益比**：必须≥2，否则不值得交易

现在请开始分析并输出 JSON 数组格式 `[{{...}}]` 的决策。
"""
    
    def _get_fallback_decision(self, context: Dict) -> Dict:
        """
        获取兜底决策（当LLM失败时）
        
        返回保守的hold决策
        """
        return {
            'action': 'wait',
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
