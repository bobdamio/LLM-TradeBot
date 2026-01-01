"""
量化策略师 (The Strategist) Agent - 重构版

职责：
按时间周期组织技术分析，而非按指标类型
- 6小时分析：完整技术指标集
- 2小时分析：完整技术指标集
- 半小时分析：完整技术指标集

优化点：
- 时间周期为中心的组织方式
- 便于LLM理解每个时间周期的完整技术面
- 扩展指标集：EMA, MA, BOLL, RSI, MACD, KDJ, ATR, OBV
"""

import pandas as pd
from typing import Dict
from dataclasses import asdict

from src.agents.data_sync_agent import MarketSnapshot
# from src.agents.timeframe_analyzer import TimeframeAnalyzer, TimeframeAnalysis  # Not needed - using real 1h/15m data
from src.utils.logger import log
from src.utils.oi_tracker import oi_tracker


class QuantAnalystAgent:
    """
    量化策略师 (The Strategist)
    
    提供情绪分析和OI燃料验证
    技术指标分析现在直接在main.py中使用真实1h/15m/5m数据
    """
    
    def __init__(self):
        """初始化量化策略师"""
        log.info("👨‍🔬 The Strategist (QuantAnalyst Agent) initialized - Full Analysis Mode")
        
    @staticmethod
    def calculate_ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        loss = loss.replace(0, 1e-10)
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9, m1: int = 3, m2: int = 3):
        low_min = low.rolling(window=n).min()
        high_max = high.rolling(window=n).max()
        rsv = 100 * (close - low_min) / (high_max - low_min)
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        return k, d, j
        
    def analyze_trend(self, df: pd.DataFrame) -> Dict:
        """Calculate trend score (-100 to +100)"""
        if df is None or len(df) < 60:
            return {'score': 0, 'signal': 'neutral', 'details': {}}
            
        close = df['close']
        ema20 = self.calculate_ema(close, 20)
        ema60 = self.calculate_ema(close, 60)
        
        curr_close = close.iloc[-1]
        curr_ema20 = ema20.iloc[-1]
        curr_ema60 = ema60.iloc[-1]
        
        score = 0
        details = {'ema_status': 'neutral'}
        
        # Basic EMA Alignment
        if curr_close > curr_ema20 > curr_ema60:
            score = 60
            details['ema_status'] = 'bullish_alignment'
        elif curr_close < curr_ema20 < curr_ema60:
            score = -60
            details['ema_status'] = 'bearish_alignment'
        elif curr_close > curr_ema20 and curr_ema20 < curr_ema60:
             score = 20 # Potential reversal up
             details['ema_status'] = 'potential_reversal_up'
        elif curr_close < curr_ema20 and curr_ema20 > curr_ema60:
             score = -20 # Potential reversal down
             details['ema_status'] = 'potential_reversal_down'
             
        return {'score': score, 'signal': 'long' if score > 0 else 'short', 'details': details}

    def analyze_oscillator(self, df: pd.DataFrame) -> Dict:
        """Calculate oscillator score (-100 to +100)"""
        if df is None or len(df) < 30:
            return {'score': 0, 'signal': 'neutral', 'details': {}}
            
        close = df['close']
        high = df['high']
        low = df['low']
        
        # RSI
        rsi = self.calculate_rsi(close, 14)
        curr_rsi = rsi.iloc[-1]
        
        # KDJ
        k, d, j = self.calculate_kdj(high, low, close)
        curr_j = j.iloc[-1]
        
        score = 0
        details = {'rsi_value': round(curr_rsi, 1), 'kdj_j': round(curr_j, 1)}
        
        # RSI Logic
        if curr_rsi < 30:
            score += 40 # Oversold -> Bullish
        elif curr_rsi > 70:
            score -= 40 # Overbought -> Bearish
            
        # KDJ Logic
        if curr_j < 20:
             score += 30
        elif curr_j > 80:
             score -= 30
             
        return {'score': score, 'signal': 'long' if score > 0 else 'short', 'details': details}

    async def analyze_all_timeframes(self, snapshot: MarketSnapshot) -> Dict:
        """
        执行完整技术分析
        
        Args:
            snapshot: 市场快照
            
        Returns:
            分析结果字典，包含趋势、震荡、情绪等完整维度
        """
        # 1. 情绪分析
        sentiment = self._analyze_sentiment(snapshot)
        
        # 2. 趋势分析
        t_5m = self.analyze_trend(snapshot.stable_5m)
        t_15m = self.analyze_trend(snapshot.stable_15m)
        t_1h = self.analyze_trend(snapshot.stable_1h)
        
        # 3. 震荡分析
        o_5m = self.analyze_oscillator(snapshot.stable_5m)
        o_15m = self.analyze_oscillator(snapshot.stable_15m)
        o_1h = self.analyze_oscillator(snapshot.stable_1h)
        
        # 4. 计算综合得分 (简单平均)
        total_trend_score = (t_5m['score'] + t_15m['score'] + t_1h['score']) / 3
        total_osc_score = (o_5m['score'] + o_15m['score'] + o_1h['score']) / 3
        
        result = {
            'sentiment': sentiment,
            # 保留空的占位符以兼容
            'timeframe_6h': {}, 
            'timeframe_2h': {},
            'timeframe_30m': {},
            
            # 完整的技术信号
            'trend': {
                'trend_5m_score': t_5m['score'],
                'trend_15m_score': t_15m['score'],
                'trend_1h_score': t_1h['score'],
                'total_trend_score': total_trend_score,
                'trend_5m': t_5m,
                'trend_15m': t_15m,
                'trend_1h': t_1h
            },
            'oscillator': {
                'osc_5m_score': o_5m['score'],
                'osc_15m_score': o_15m['score'],
                'osc_1h_score': o_1h['score'],
                'total_osc_score': total_osc_score,
                'oscillator_5m': o_5m,
                'oscillator_15m': o_15m,
                'oscillator_1h': o_1h
            },
            'overall_score': (total_trend_score + total_osc_score) / 2
        }
        
        return result
    
    def analyze(self, snapshot: MarketSnapshot) -> Dict:
        """
        [Legacy] 执行多时间周期技术分析
        This method is kept for backward compatibility but redirects to analyze_all_timeframes logic partially
        """
        # For legacy callers, we might need a different return structure or just point them to new logic
        # But for now, let's keep it minimally functional or raise deprecation warning
        # Since analyze_all_timeframes is the primary entry point now
        return {} # Placeholder

    def _analyze_sentiment(self, snapshot: MarketSnapshot) -> Dict:
        """
        分析市场情绪 (Modified: Use Volume as OI Proxy)
        
        基于：
        - 资金费率 (Funding Rate)
        - 成交量变化 (Volume Change as Proxy for OI)
        """
        details = {}
        # q_data = getattr(snapshot, 'quant_data', {})
        b_funding = getattr(snapshot, 'binance_funding', {})
        # b_oi = getattr(snapshot, 'binance_oi', {}) # Disabled
        
        has_data = False
        score = 0
        
        # 1. 资金费率分析
        if b_funding and 'funding_rate' in b_funding:
            has_data = True
            funding_rate = float(b_funding['funding_rate']) * 100
            details['funding_rate'] = funding_rate
            
            if funding_rate > 0.05:
                score -= 30
                details['funding_signal'] = "极度贪婪（高资金费率）"
            elif funding_rate > 0.01:
                score -= 15
                details['funding_signal'] = "贪婪"
            elif funding_rate < -0.05:
                score += 30
                details['funding_signal'] = "极度恐惧（负资金费率）"
            elif funding_rate < -0.01:
                score += 15
                details['funding_signal'] = "恐惧"
            else:
                details['funding_signal'] = "中性"
        
        # 2. Volume Fuel Proxy (Replacing OI)
        # Use 1h Volume Change as a proxy for "Fuel"
        # Logic: High relative volume = High fuel/interest
        
        vol_change_pct = 0.0
        fuel_signal = "neutral"
        
        df_1h = snapshot.stable_1h
        if df_1h is not None and len(df_1h) >= 24:
            has_data = True
            # Calculate average volume of last 24 hours
            current_vol = df_1h['volume'].iloc[-1]
            avg_vol = df_1h['volume'].iloc[-25:-1].mean()
            
            if avg_vol > 0:
                vol_ratio = current_vol / avg_vol
                # Convert ratio to percentage change for compatibility: 1.5x -> +50%
                vol_change_pct = (vol_ratio - 1) * 100
                # 🔧 FIX C1: Clamp extreme values to prevent display issues
                vol_change_pct = max(min(vol_change_pct, 200), -100)
            else:
                vol_change_pct = 0
            
            details['oi_change_24h_pct'] = vol_change_pct # Map to existing field
            details['is_volume_proxy'] = True
            
            if vol_change_pct > 50: # > 1.5x volume
                score += 20
                fuel_signal = "strong"
                details['oi_signal'] = f"High Volume (1.5x avg)"
            elif vol_change_pct > 20: # > 1.2x volume
                score += 10
                fuel_signal = "moderate"
                details['oi_signal'] = f"Elevated Volume (1.2x avg)"
            elif vol_change_pct < -50: # < 0.5x volume
                score -= 10
                fuel_signal = "weak" 
                details['oi_signal'] = f"Low Volume (0.5x avg)"
            else:
                details['oi_signal'] = "Normal Volume"
        else:
            details['oi_signal'] = "Insufficient Data for Vol"

        # 🔥 Construct Proxy OI Fuel
        oi_fuel = {
            'oi_change_24h': vol_change_pct,
            'fuel_signal': fuel_signal,
            'fuel_score': min(100, max(-100, int(vol_change_pct))),
            'whale_trap_risk': False, # Volume proxy doesn't detect whale traps easily
            'fuel_strength': fuel_signal, 
            'divergence_alert': False,
            'data_error': False,
            'is_proxy': True
        }
        
        return {
            'score': score if has_data else 0,
            'details': details,
            'has_data': has_data,
            'total_sentiment_score': score if has_data else 0,
            'oi_change_24h_pct': vol_change_pct,
            'oi_fuel': oi_fuel, 
        }
