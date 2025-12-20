"""
市场状态检测器 (Regime Detector)
识别当前市场处于趋势/震荡/高波动状态
"""

import pandas as pd
import numpy as np
from typing import Dict
from enum import Enum


class MarketRegime(Enum):
    """市场状态分类"""
    TRENDING_UP = "trending_up"       # 明确上涨趋势
    TRENDING_DOWN = "trending_down"   # 明确下跌趋势
    CHOPPY = "choppy"                 # 震荡市（垃圾时间）
    VOLATILE = "volatile"             # 高波动（危险）
    UNKNOWN = "unknown"               # 无法判断


class RegimeDetector:
    """
    市场状态检测器
    
    核心功能：
    1. 使用 ADX 判断趋势强度
    2. 使用布林带宽度判断波动性
    3. 使用 ATR 判断风险水平
    4. 综合判断市场状态
    
    决策规则：
    - CHOPPY（震荡市）：禁止追涨杀跌，只做区间交易
    - VOLATILE（高波动）：禁止开仓或降低杠杆
    - UNKNOWN（无法判断）：强制观望
    """
    
    def __init__(self,
                 adx_trend_threshold: float = 25.0,    # ADX > 25 为趋势
                 adx_choppy_threshold: float = 20.0,   # ADX < 20 为震荡
                 bb_width_volatile_ratio: float = 1.5,  # 布林带宽度 > 均值1.5倍为高波动
                 atr_high_threshold: float = 2.0):      # ATR% > 2% 为高波动
        """
        初始化市场状态检测器
        
        Args:
            adx_trend_threshold: ADX 趋势阈值
            adx_choppy_threshold: ADX 震荡阈值
            bb_width_volatile_ratio: 布林带宽度波动比率
            atr_high_threshold: ATR 高波动阈值（百分比）
        """
        self.adx_trend_threshold = adx_trend_threshold
        self.adx_choppy_threshold = adx_choppy_threshold
        self.bb_width_volatile_ratio = bb_width_volatile_ratio
        self.atr_high_threshold = atr_high_threshold
    
    def detect_regime(self, df: pd.DataFrame) -> Dict:
        """
        检测市场状态
        
        Args:
            df: K线数据（必须包含技术指标）
            
        Returns:
            {
                'regime': MarketRegime,
                'confidence': float,  # 0-100
                'adx': float,
                'bb_width_pct': float,
                'atr_pct': float,
                'trend_direction': str,  # 'up', 'down', 'neutral'
                'reason': str
            }
        """
        
        # 1. 计算 ADX（如果没有则计算）
        adx = self._get_or_calculate_adx(df)
        
        # 2. 计算布林带宽度百分比
        bb_width_pct = self._calculate_bb_width_pct(df)
        
        # 3. 计算 ATR 百分比
        atr_pct = self._calculate_atr_pct(df)
        
        # 4. 判断趋势方向
        trend_direction = self._detect_trend_direction(df)
        
        # 5. 综合判断市场状态
        regime, confidence, reason = self._classify_regime(
            adx, bb_width_pct, atr_pct, trend_direction
        )
        
        return {
            'regime': regime.value,
            'confidence': confidence,
            'adx': adx,
            'bb_width_pct': bb_width_pct,
            'atr_pct': atr_pct,
            'trend_direction': trend_direction,
            'reason': reason
        }
    
    def _get_or_calculate_adx(self, df: pd.DataFrame) -> float:
        """
        获取或计算 ADX
        
        ADX (Average Directional Index) 用于衡量趋势强度
        - ADX > 25: 强趋势
        - ADX < 20: 弱趋势/震荡
        """
        # 如果已有 ADX 列，直接使用
        if 'adx' in df.columns:
            return df['adx'].iloc[-1]
        
        # 否则简化计算（使用 EMA 差值作为替代）
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            ema_diff = abs(df['ema_12'].iloc[-1] - df['ema_26'].iloc[-1])
            price = df['close'].iloc[-1]
            adx_proxy = (ema_diff / price) * 100 * 10  # 转换为类似 ADX 的值
            return adx_proxy
        
        # 无法计算，返回中性值
        return 20.0
    
    def _calculate_bb_width_pct(self, df: pd.DataFrame) -> float:
        """
        计算布林带宽度百分比
        
        宽度 = (上轨 - 下轨) / 中轨 * 100
        """
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
            upper = df['bb_upper'].iloc[-1]
            lower = df['bb_lower'].iloc[-1]
            middle = df['bb_middle'].iloc[-1]
            
            if middle > 0:
                width_pct = ((upper - lower) / middle) * 100
                return width_pct
        
        # 无法计算，返回默认值
        return 2.0
    
    def _calculate_atr_pct(self, df: pd.DataFrame) -> float:
        """
        计算 ATR 百分比
        
        ATR% = ATR / 当前价格 * 100
        """
        if 'atr' in df.columns:
            atr = df['atr'].iloc[-1]
            price = df['close'].iloc[-1]
            
            if price > 0:
                atr_pct = (atr / price) * 100
                return atr_pct
        
        # 无法计算，返回默认值
        return 0.5
    
    def _detect_trend_direction(self, df: pd.DataFrame) -> str:
        """
        检测趋势方向
        
        使用 SMA20 和 SMA50 判断
        """
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            sma20 = df['sma_20'].iloc[-1]
            sma50 = df['sma_50'].iloc[-1]
            price = df['close'].iloc[-1]
            
            # 价格和均线关系
            if price > sma20 > sma50:
                return 'up'
            elif price < sma20 < sma50:
                return 'down'
        
        return 'neutral'
    
    def _classify_regime(self, 
                        adx: float,
                        bb_width_pct: float,
                        atr_pct: float,
                        trend_direction: str) -> tuple:
        """
        综合分类市场状态
        
        Returns:
            (regime, confidence, reason)
        """
        
        # 1. 高波动检测（最高优先级）
        if atr_pct > self.atr_high_threshold:
            return (
                MarketRegime.VOLATILE,
                80.0,
                f"高波动市场（ATR {atr_pct:.2f}% > {self.atr_high_threshold}%）"
            )
        
        # 2. 震荡市检测
        if adx < self.adx_choppy_threshold:
            return (
                MarketRegime.CHOPPY,
                70.0,
                f"震荡市（ADX {adx:.1f} < {self.adx_choppy_threshold}）"
            )
        
        # 3. 趋势市检测
        if adx > self.adx_trend_threshold:
            if trend_direction == 'up':
                return (
                    MarketRegime.TRENDING_UP,
                    75.0,
                    f"上涨趋势（ADX {adx:.1f} > {self.adx_trend_threshold}，价格在均线上方）"
                )
            elif trend_direction == 'down':
                return (
                    MarketRegime.TRENDING_DOWN,
                    75.0,
                    f"下跌趋势（ADX {adx:.1f} > {self.adx_trend_threshold}，价格在均线下方）"
                )
            else:
                # ADX 高但方向不明
                return (
                    MarketRegime.UNKNOWN,
                    50.0,
                    f"趋势强度高但方向不明（ADX {adx:.1f}）"
                )
        
        # 4. 无法判断
        return (
            MarketRegime.UNKNOWN,
            40.0,
            f"市场状态不明确（ADX {adx:.1f}）"
        )


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    dates = pd.date_range('2025-01-01', periods=100, freq='5min')
    
    # 模拟上涨趋势
    uptrend_prices = 87000 + np.cumsum(np.random.randn(100) * 10 + 5)
    
    df_uptrend = pd.DataFrame({
        'timestamp': dates,
        'close': uptrend_prices,
        'high': uptrend_prices + 50,
        'low': uptrend_prices - 50,
        'sma_20': uptrend_prices - 100,
        'sma_50': uptrend_prices - 200,
        'ema_12': uptrend_prices - 50,
        'ema_26': uptrend_prices - 150,
        'atr': np.full(100, 100),
        'bb_upper': uptrend_prices + 200,
        'bb_middle': uptrend_prices,
        'bb_lower': uptrend_prices - 200
    })
    
    # 模拟震荡市
    choppy_prices = 87000 + np.random.randn(100) * 50
    
    df_choppy = pd.DataFrame({
        'timestamp': dates,
        'close': choppy_prices,
        'high': choppy_prices + 30,
        'low': choppy_prices - 30,
        'sma_20': np.full(100, 87000),
        'sma_50': np.full(100, 87000),
        'ema_12': choppy_prices,
        'ema_26': choppy_prices,
        'atr': np.full(100, 50),
        'bb_upper': choppy_prices + 100,
        'bb_middle': choppy_prices,
        'bb_lower': choppy_prices - 100
    })
    
    detector = RegimeDetector()
    
    print("市场状态检测测试:\n")
    
    print("1. 上涨趋势测试:")
    result = detector.detect_regime(df_uptrend)
    print(f"   状态: {result['regime']}")
    print(f"   信心: {result['confidence']:.1f}%")
    print(f"   ADX: {result['adx']:.1f}")
    print(f"   趋势方向: {result['trend_direction']}")
    print(f"   原因: {result['reason']}")
    print()
    
    print("2. 震荡市测试:")
    result = detector.detect_regime(df_choppy)
    print(f"   状态: {result['regime']}")
    print(f"   信心: {result['confidence']:.1f}%")
    print(f"   ADX: {result['adx']:.1f}")
    print(f"   趋势方向: {result['trend_direction']}")
    print(f"   原因: {result['reason']}")
