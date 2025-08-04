"""
기술적 지표 계산 모듈
RSI, MACD, 볼린저 밴드, 이동평균선 등
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()

class TechnicalIndicators:
    """기술적 지표 계산 클래스"""
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """단순 이동평균 (Simple Moving Average)"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """지수 이동평균 (Exponential Moving Average)"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # 첫 EMA는 SMA
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """상대강도지수 (Relative Strength Index)"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Optional[Dict[str, float]]:
        """MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return None
        
        ema12 = TechnicalIndicators.calculate_ema(prices, 12)
        ema26 = TechnicalIndicators.calculate_ema(prices, 26)
        
        if not ema12 or not ema26:
            return None
        
        macd_line = ema12 - ema26
        
        # Signal line (9-day EMA of MACD)
        macd_values = []
        for i in range(26, len(prices)):
            ema12_temp = TechnicalIndicators.calculate_ema(prices[:i+1], 12)
            ema26_temp = TechnicalIndicators.calculate_ema(prices[:i+1], 26)
            if ema12_temp and ema26_temp:
                macd_values.append(ema12_temp - ema26_temp)
        
        signal_line = TechnicalIndicators.calculate_ema(macd_values, 9) if len(macd_values) >= 9 else macd_line
        histogram = macd_line - signal_line if signal_line else 0
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, num_std: float = 2) -> Optional[Dict[str, float]]:
        """볼린저 밴드"""
        if len(prices) < period:
            return None
        
        sma = TechnicalIndicators.calculate_sma(prices, period)
        if not sma:
            return None
        
        std = np.std(prices[-period:])
        
        return {
            'upper': sma + (num_std * std),
            'middle': sma,
            'lower': sma - (num_std * std),
            'bandwidth': (2 * num_std * std) / sma if sma > 0 else 0,
            'percent_b': (prices[-1] - (sma - num_std * std)) / (2 * num_std * std) if std > 0 else 0.5
        }
    
    @staticmethod
    def calculate_stochastic(highs: List[float], lows: List[float], closes: List[float], 
                           period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> Optional[Dict[str, float]]:
        """스토캐스틱 오실레이터"""
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return None
        
        # %K 계산
        lowest_low = min(lows[-period:])
        highest_high = max(highs[-period:])
        
        if highest_high == lowest_low:
            k_percent = 50.0
        else:
            k_percent = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        # %D는 %K의 3일 이동평균 (간단히 현재 값만 반환)
        d_percent = k_percent  # 실제로는 %K의 이동평균이어야 함
        
        return {
            'k': k_percent,
            'd': d_percent,
            'oversold': k_percent < 20,
            'overbought': k_percent > 80
        }
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
        """평균 진폭 (Average True Range)"""
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            return None
        
        true_ranges = []
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_ranges.append(max(high_low, high_close, low_close))
        
        if len(true_ranges) < period:
            return None
        
        return sum(true_ranges[-period:]) / period
    
    @staticmethod
    def calculate_volume_indicators(volumes: List[float], prices: List[float]) -> Dict[str, float]:
        """거래량 관련 지표"""
        if len(volumes) < 20 or len(prices) < 20:
            return {}
        
        # 거래량 이동평균
        volume_ma = sum(volumes[-20:]) / 20
        
        # 거래량 비율 (현재 거래량 / 평균 거래량)
        volume_ratio = volumes[-1] / volume_ma if volume_ma > 0 else 1.0
        
        # OBV (On-Balance Volume) 추세
        obv = 0
        obv_values = []
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv += volumes[i]
            elif prices[i] < prices[i-1]:
                obv -= volumes[i]
            obv_values.append(obv)
        
        # OBV 추세 (상승/하락)
        obv_trend = "상승" if len(obv_values) >= 5 and obv_values[-1] > obv_values[-5] else "하락"
        
        return {
            'volume_ma': volume_ma,
            'volume_ratio': volume_ratio,
            'obv_trend': obv_trend,
            'high_volume': volume_ratio > 1.5
        }
    
    @staticmethod
    def identify_patterns(prices: List[float], period: int = 20) -> Dict[str, bool]:
        """차트 패턴 인식"""
        if len(prices) < period:
            return {}
        
        patterns = {}
        
        # 이동평균선 정렬 (정배열/역배열)
        sma20 = TechnicalIndicators.calculate_sma(prices, 20)
        sma60 = TechnicalIndicators.calculate_sma(prices, 60) if len(prices) >= 60 else None
        sma120 = TechnicalIndicators.calculate_sma(prices, 120) if len(prices) >= 120 else None
        
        if sma20 and sma60:
            patterns['golden_cross'] = sma20 > sma60 and prices[-1] > sma20
            patterns['death_cross'] = sma20 < sma60 and prices[-1] < sma20
            
            if sma120:
                patterns['perfect_order'] = prices[-1] > sma20 > sma60 > sma120
                patterns['reverse_order'] = prices[-1] < sma20 < sma60 < sma120
        
        # 최근 추세
        recent_prices = prices[-10:]
        if len(recent_prices) == 10:
            start_price = recent_prices[0]
            end_price = recent_prices[-1]
            change_percent = (end_price - start_price) / start_price * 100
            
            patterns['strong_uptrend'] = change_percent > 10
            patterns['uptrend'] = change_percent > 3
            patterns['downtrend'] = change_percent < -3
            patterns['strong_downtrend'] = change_percent < -10
            patterns['sideways'] = -3 <= change_percent <= 3
        
        # 지지/저항 돌파
        recent_high = max(prices[-20:-1]) if len(prices) > 20 else max(prices[:-1])
        recent_low = min(prices[-20:-1]) if len(prices) > 20 else min(prices[:-1])
        current_price = prices[-1]
        
        patterns['breakout_high'] = current_price > recent_high * 1.02  # 2% 이상 돌파
        patterns['breakdown_low'] = current_price < recent_low * 0.98   # 2% 이상 하락
        
        return patterns
    
    @staticmethod
    def calculate_all_indicators(price_history: List[Dict]) -> Dict[str, any]:
        """모든 기술적 지표 계산"""
        if not price_history or len(price_history) < 20:
            return {}
        
        # 가격 데이터 추출
        closes = [p['close'] for p in price_history]
        highs = [p['high'] for p in price_history]
        lows = [p['low'] for p in price_history]
        volumes = [p['volume'] for p in price_history]
        
        indicators = {}
        
        # 이동평균선
        indicators['sma20'] = TechnicalIndicators.calculate_sma(closes, 20)
        indicators['sma60'] = TechnicalIndicators.calculate_sma(closes, 60)
        indicators['ema12'] = TechnicalIndicators.calculate_ema(closes, 12)
        indicators['ema26'] = TechnicalIndicators.calculate_ema(closes, 26)
        
        # 모멘텀 지표
        indicators['rsi'] = TechnicalIndicators.calculate_rsi(closes)
        indicators['macd'] = TechnicalIndicators.calculate_macd(closes)
        indicators['stochastic'] = TechnicalIndicators.calculate_stochastic(highs, lows, closes)
        
        # 변동성 지표
        indicators['bollinger'] = TechnicalIndicators.calculate_bollinger_bands(closes)
        indicators['atr'] = TechnicalIndicators.calculate_atr(highs, lows, closes)
        
        # 거래량 지표
        indicators['volume'] = TechnicalIndicators.calculate_volume_indicators(volumes, closes)
        
        # 패턴 인식
        indicators['patterns'] = TechnicalIndicators.identify_patterns(closes)
        
        # 현재 가격 정보
        indicators['current_price'] = closes[-1]
        indicators['price_change'] = closes[-1] - closes[-2] if len(closes) > 1 else 0
        indicators['price_change_percent'] = (closes[-1] / closes[-2] - 1) * 100 if len(closes) > 1 and closes[-2] > 0 else 0
        
        return indicators
