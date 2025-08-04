"""
거래 규칙 엔진
기술적 지표와 펀더멘털을 조합한 매매 신호 생성
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()

@dataclass
class TradingSignal:
    """거래 신호 데이터 클래스"""
    direction: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0.0 ~ 1.0
    confidence: float  # 0.0 ~ 1.0
    reasons: List[str]
    risk_level: str  # 'low', 'medium', 'high'

class TradingRules:
    """거래 규칙 기반 신호 생성"""
    
    def __init__(self):
        # 각 규칙의 가중치
        self.weights = {
            'trend': 0.25,
            'momentum': 0.25,
            'volatility': 0.15,
            'volume': 0.15,
            'pattern': 0.20
        }
        
        # 리스크 레벨 임계값
        self.risk_thresholds = {
            'low': {'volatility': 0.15, 'atr_ratio': 0.02},
            'medium': {'volatility': 0.25, 'atr_ratio': 0.04},
            'high': {'volatility': 0.35, 'atr_ratio': 0.06}
        }
    
    def generate_signal(self, technical: Dict, fundamental: Dict) -> TradingSignal:
        """종합적인 거래 신호 생성"""
        
        # 각 카테고리별 신호 계산
        trend_signal = self._analyze_trend(technical)
        momentum_signal = self._analyze_momentum(technical)
        volatility_signal = self._analyze_volatility(technical)
        volume_signal = self._analyze_volume(technical)
        pattern_signal = self._analyze_patterns(technical)
        
        # 신호 집계
        signals = {
            'trend': trend_signal,
            'momentum': momentum_signal,
            'volatility': volatility_signal,
            'volume': volume_signal,
            'pattern': pattern_signal
        }
        
        # 가중 평균 계산
        total_score = 0
        total_confidence = 0
        all_reasons = []
        
        for category, (score, confidence, reasons) in signals.items():
            weight = self.weights[category]
            total_score += score * weight
            total_confidence += confidence * weight
            all_reasons.extend(reasons)
        
        # 펀더멘털 보정
        fundamental_adjustment = self._apply_fundamental_adjustment(fundamental)
        total_score = total_score * 0.7 + fundamental_adjustment * 0.3
        
        # 방향 결정
        if total_score > 0.6:
            direction = 'BUY'
            strength = min(1.0, (total_score - 0.5) * 2)
        elif total_score < 0.4:
            direction = 'SELL'
            strength = min(1.0, (0.5 - total_score) * 2)
        else:
            direction = 'HOLD'
            strength = 0.5
        
        # 리스크 레벨 계산
        risk_level = self._calculate_risk_level(technical)
        
        # 신뢰도 조정 (리스크가 높으면 신뢰도 감소)
        if risk_level == 'high':
            total_confidence *= 0.8
        elif risk_level == 'medium':
            total_confidence *= 0.9
        
        return TradingSignal(
            direction=direction,
            strength=strength,
            confidence=total_confidence,
            reasons=all_reasons[:5],  # 상위 5개 이유만
            risk_level=risk_level
        )
    
    def _analyze_trend(self, technical: Dict) -> Tuple[float, float, List[str]]:
        """추세 분석"""
        score = 0.5  # 중립
        confidence = 0.0
        reasons = []
        
        # 이동평균선 분석
        if technical.get('sma20') and technical.get('sma60'):
            current_price = technical.get('current_price', 0)
            sma20 = technical['sma20']
            sma60 = technical['sma60']
            
            # 정배열 체크
            if current_price > sma20 > sma60:
                score += 0.3
                confidence += 0.3
                reasons.append("완벽한 상승 추세 (가격 > 20일선 > 60일선)")
            elif sma20 > sma60:
                score += 0.2
                confidence += 0.2
                reasons.append("골든크로스 발생 (20일선 > 60일선)")
            elif current_price < sma20 < sma60:
                score -= 0.3
                confidence += 0.3
                reasons.append("완벽한 하락 추세 (가격 < 20일선 < 60일선)")
            elif sma20 < sma60:
                score -= 0.2
                confidence += 0.2
                reasons.append("데드크로스 발생 (20일선 < 60일선)")
        
        # 패턴 분석
        patterns = technical.get('patterns', {})
        if patterns.get('strong_uptrend'):
            score += 0.2
            confidence += 0.2
            reasons.append("강한 상승 추세 지속 중")
        elif patterns.get('strong_downtrend'):
            score -= 0.2
            confidence += 0.2
            reasons.append("강한 하락 추세 지속 중")
        
        return score, confidence, reasons
    
    def _analyze_momentum(self, technical: Dict) -> Tuple[float, float, List[str]]:
        """모멘텀 분석"""
        score = 0.5
        confidence = 0.0
        reasons = []
        
        # RSI 분석
        rsi = technical.get('rsi')
        if rsi is not None:
            if rsi < 30:
                score += 0.25
                confidence += 0.3
                reasons.append(f"RSI {rsi:.1f} - 과매도 구간에서 반등 가능")
            elif rsi > 70:
                score -= 0.25
                confidence += 0.3
                reasons.append(f"RSI {rsi:.1f} - 과매수 구간에서 조정 가능")
            elif 40 <= rsi <= 60:
                confidence += 0.1
                reasons.append(f"RSI {rsi:.1f} - 중립 구간")
        
        # MACD 분석
        macd_data = technical.get('macd')
        if macd_data:
            macd = macd_data.get('macd', 0)
            signal = macd_data.get('signal', 0)
            histogram = macd_data.get('histogram', 0)
            
            if histogram > 0 and macd > 0:
                score += 0.2
                confidence += 0.2
                reasons.append("MACD 히스토그램 양수 - 상승 모멘텀")
            elif histogram < 0 and macd < 0:
                score -= 0.2
                confidence += 0.2
                reasons.append("MACD 히스토그램 음수 - 하락 모멘텀")
        
        # 스토캐스틱 분석
        stochastic = technical.get('stochastic')
        if stochastic:
            if stochastic.get('oversold'):
                score += 0.15
                confidence += 0.2
                reasons.append("스토캐스틱 과매도 - 반등 신호")
            elif stochastic.get('overbought'):
                score -= 0.15
                confidence += 0.2
                reasons.append("스토캐스틱 과매수 - 조정 신호")
        
        return score, confidence, reasons
    
    def _analyze_volatility(self, technical: Dict) -> Tuple[float, float, List[str]]:
        """변동성 분석"""
        score = 0.5
        confidence = 0.0
        reasons = []
        
        # 볼린저 밴드 분석
        bollinger = technical.get('bollinger')
        if bollinger:
            current_price = technical.get('current_price', 0)
            upper = bollinger.get('upper', 0)
            lower = bollinger.get('lower', 0)
            percent_b = bollinger.get('percent_b', 0.5)
            
            if percent_b < 0.2:
                score += 0.2
                confidence += 0.25
                reasons.append("볼린저 밴드 하단 접근 - 반등 가능성")
            elif percent_b > 0.8:
                score -= 0.2
                confidence += 0.25
                reasons.append("볼린저 밴드 상단 접근 - 조정 가능성")
            
            # 밴드폭 분석
            bandwidth = bollinger.get('bandwidth', 0)
            if bandwidth < 0.1:
                confidence += 0.15
                reasons.append("볼린저 밴드 수축 - 변동성 확대 예상")
        
        return score, confidence, reasons
    
    def _analyze_volume(self, technical: Dict) -> Tuple[float, float, List[str]]:
        """거래량 분석"""
        score = 0.5
        confidence = 0.0
        reasons = []
        
        volume_data = technical.get('volume', {})
        if volume_data:
            volume_ratio = volume_data.get('volume_ratio', 1.0)
            obv_trend = volume_data.get('obv_trend', '중립')
            
            # 거래량 급증
            if volume_data.get('high_volume', False):
                price_change = technical.get('price_change_percent', 0)
                if price_change > 0:
                    score += 0.2
                    confidence += 0.25
                    reasons.append(f"거래량 {volume_ratio:.1f}배 증가 + 가격 상승")
                else:
                    score -= 0.2
                    confidence += 0.25
                    reasons.append(f"거래량 {volume_ratio:.1f}배 증가 + 가격 하락")
            
            # OBV 추세
            if obv_trend == "상승":
                score += 0.1
                confidence += 0.15
                reasons.append("OBV 상승 추세 - 매집 진행")
            elif obv_trend == "하락":
                score -= 0.1
                confidence += 0.15
                reasons.append("OBV 하락 추세 - 매도세 우위")
        
        return score, confidence, reasons
    
    def _analyze_patterns(self, technical: Dict) -> Tuple[float, float, List[str]]:
        """패턴 분석"""
        score = 0.5
        confidence = 0.0
        reasons = []
        
        patterns = technical.get('patterns', {})
        
        # 주요 패턴 체크
        if patterns.get('golden_cross'):
            score += 0.3
            confidence += 0.35
            reasons.append("골든크로스 패턴 - 강한 매수 신호")
        elif patterns.get('death_cross'):
            score -= 0.3
            confidence += 0.35
            reasons.append("데드크로스 패턴 - 강한 매도 신호")
        
        if patterns.get('breakout_high'):
            score += 0.25
            confidence += 0.3
            reasons.append("저항선 돌파 - 추가 상승 가능")
        elif patterns.get('breakdown_low'):
            score -= 0.25
            confidence += 0.3
            reasons.append("지지선 붕괴 - 추가 하락 가능")
        
        if patterns.get('perfect_order'):
            score += 0.2
            confidence += 0.25
            reasons.append("이동평균선 정배열 - 안정적 상승 추세")
        elif patterns.get('reverse_order'):
            score -= 0.2
            confidence += 0.25
            reasons.append("이동평균선 역배열 - 안정적 하락 추세")
        
        return score, confidence, reasons
    
    def _apply_fundamental_adjustment(self, fundamental: Dict) -> float:
        """펀더멘털 점수로 조정"""
        # 펀더멘털 점수가 없으면 중립
        if not fundamental:
            return 0.5
        
        fundamental_score = fundamental.get('score', 0.5)
        
        # 펀더멘털이 매우 좋으면 가점
        if fundamental_score > 0.7:
            return 0.7
        # 펀더멘털이 매우 나쁘면 감점
        elif fundamental_score < 0.3:
            return 0.3
        # 보통이면 중립
        else:
            return 0.5
    
    def _calculate_risk_level(self, technical: Dict) -> str:
        """리스크 수준 계산"""
        # ATR 기반 변동성
        atr = technical.get('atr', 0)
        current_price = technical.get('current_price', 1)
        atr_ratio = atr / current_price if current_price > 0 else 0
        
        # 가격 변동성
        bollinger = technical.get('bollinger', {})
        bandwidth = bollinger.get('bandwidth', 0)
        
        # 리스크 레벨 결정
        if atr_ratio > self.risk_thresholds['high']['atr_ratio'] or bandwidth > 0.3:
            return 'high'
        elif atr_ratio > self.risk_thresholds['medium']['atr_ratio'] or bandwidth > 0.2:
            return 'medium'
        else:
            return 'low'
    
    def get_signal_explanation(self, signal: TradingSignal) -> str:
        """신호에 대한 자연어 설명"""
        direction_text = {
            'BUY': '매수',
            'SELL': '매도',
            'HOLD': '관망'
        }
        
        risk_text = {
            'low': '낮음',
            'medium': '보통',
            'high': '높음'
        }
        
        explanation = f"📊 AI 분석 결과: **{direction_text[signal.direction]}** 신호\n\n"
        explanation += f"신호 강도: {'🟢' * int(signal.strength * 5)}{'⚪' * (5 - int(signal.strength * 5))} ({signal.strength:.1%})\n"
        explanation += f"신뢰도: {signal.confidence:.1%}\n"
        explanation += f"리스크: {risk_text[signal.risk_level]}\n\n"
        
        if signal.reasons:
            explanation += "주요 근거:\n"
            for i, reason in enumerate(signal.reasons, 1):
                explanation += f"{i}. {reason}\n"
        
        return explanation
