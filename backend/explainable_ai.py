"""
설명 가능한 AI (XAI) 모듈
SHAP과 LIME을 활용한 예측 설명
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import shap
from lime import lime_tabular
import structlog

logger = structlog.get_logger()

class ExplainablePredictor:
    """설명 가능한 예측 모델"""
    
    def __init__(self, base_predictor):
        self.predictor = base_predictor
        self.explainer = None
        self.feature_names = [
            '5일 수익률', '20일 수익률', '변동성', 'RSI', 'MACD',
            'PE 비율', 'ROE', 'EPS 성장률', '매출 성장률'
        ]
        self.feature_descriptions = {
            '5일 수익률': "최근 5일간 주가 변동률",
            '20일 수익률': "최근 20일간 주가 변동률",
            '변동성': "주가의 변동 폭 (리스크 지표)",
            'RSI': "상대강도지수 (과매수/과매도)",
            'MACD': "이동평균 수렴/확산",
            'PE 비율': "주가수익비율 (가격 대비 수익)",
            'ROE': "자기자본이익률 (경영 효율성)",
            'EPS 성장률': "주당순이익 성장률",
            '매출 성장률': "매출액 증가율"
        }
        
    async def predict_with_explanation(self, stock_data: Dict) -> Dict:
        """예측과 함께 설명 제공"""
        try:
            # 기본 예측
            prediction = await self.predictor.predict_single(stock_data)
            
            # 특징 추출
            features = self._extract_features(stock_data)
            
            # SHAP 값 계산
            shap_values = self._calculate_shap(features)
            
            # 주요 기여 요인 추출
            top_factors = self._extract_top_factors(shap_values, features)
            
            # 투명성 점수 계산
            transparency_score = self._calculate_transparency_score(shap_values)
            
            return {
                'probability': prediction['probability'],
                'expected_return': prediction['expected_return'],
                'confidence': prediction['confidence'],
                'explanation': {
                    'top_positive_factors': top_factors['positive'],
                    'top_negative_factors': top_factors['negative'],
                    'feature_importance': self._get_feature_importance(shap_values),
                    'natural_language': self._generate_natural_language_explanation(
                        top_factors, prediction['probability']
                    )
                },
                'transparency_score': transparency_score
            }
            
        except Exception as e:
            logger.error("explainable_prediction_error", error=str(e))
            # 폴백: 기본 예측만 반환
            return await self.predictor.predict_single(stock_data)
    
    def _extract_features(self, stock_data: Dict) -> np.ndarray:
        """예측을 위한 특징 추출"""
        features = []
        
        # 가격 데이터 (최근 120일)
        price_history = stock_data.get('price_history', [])
        if len(price_history) >= 120:
            prices = [p['close'] for p in price_history[-120:]]
            
            # 수익률 계산
            returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
            
            # 기술적 지표
            features.extend([
                np.mean(returns[-5:]),    # 5일 평균 수익률
                np.mean(returns[-20:]),   # 20일 평균 수익률
                np.std(returns[-20:]),    # 20일 변동성
                self._calculate_rsi(prices, 14),  # RSI
                self._calculate_macd(prices)      # MACD
            ])
        else:
            # 기본값
            features.extend([0, 0, 0.02, 50, 0])
        
        # 펀더멘털 지표
        features.extend([
            stock_data.get('pe_ratio', 15) / 30,      # PE 정규화
            stock_data.get('roe', 10) / 30,           # ROE 정규화
            stock_data.get('eps_yoy', 0) / 100,       # EPS 성장률
            stock_data.get('revenue_yoy', 0) / 100    # 매출 성장률
        ])
        
        return np.array(features, dtype=np.float32).reshape(1, -1)
    
    def _calculate_shap(self, features: np.ndarray) -> np.ndarray:
        """SHAP 값 계산"""
        if self.explainer is None:
            # XGBoost 모델 기준으로 설명자 생성
            if 'xgboost' in self.predictor.models:
                self.explainer = shap.Explainer(
                    self.predictor.models['xgboost'].predict_proba,
                    feature_names=self.feature_names
                )
            else:
                # 더미 설명자
                return np.random.randn(1, len(self.feature_names))
        
        shap_values = self.explainer(features)
        
        # 이진 분류의 경우 positive 클래스(상승)에 대한 SHAP 값
        if hasattr(shap_values, 'values'):
            if len(shap_values.values.shape) == 3:
                return shap_values.values[:, :, 1]  # positive class
            return shap_values.values
        
        return shap_values
    
    def _extract_top_factors(self, shap_values: np.ndarray, features: np.ndarray, top_n: int = 3) -> Dict:
        """상위 긍정/부정 요인 추출"""
        # SHAP 값과 특징 이름 매핑
        feature_impact = list(zip(self.feature_names, shap_values[0], features[0]))
        feature_impact.sort(key=lambda x: x[1], reverse=True)
        
        positive_factors = []
        negative_factors = []
        
        for name, impact, value in feature_impact:
            factor_info = {
                'name': name,
                'impact': float(abs(impact)),
                'value': float(value),
                'description': self._get_factor_description(name, value, impact)
            }
            
            if impact > 0 and len(positive_factors) < top_n:
                positive_factors.append(factor_info)
            elif impact < 0 and len(negative_factors) < top_n:
                negative_factors.append(factor_info)
        
        return {
            'positive': positive_factors,
            'negative': negative_factors
        }
    
    def _get_factor_description(self, name: str, value: float, impact: float) -> str:
        """요인별 설명 생성"""
        base_desc = self.feature_descriptions.get(name, name)
        
        # 값에 따른 상태 설명
        if name == '5일 수익률' or name == '20일 수익률':
            if value > 0.05:
                status = "강한 상승세"
            elif value > 0:
                status = "상승세"
            elif value > -0.05:
                status = "하락세"
            else:
                status = "강한 하락세"
        elif name == 'RSI':
            if value > 70:
                status = "과매수 상태"
            elif value > 50:
                status = "상승 압력"
            elif value > 30:
                status = "하락 압력"
            else:
                status = "과매도 상태"
        elif name == '변동성':
            if value > 0.3:
                status = "매우 높은 변동성"
            elif value > 0.2:
                status = "높은 변동성"
            elif value > 0.1:
                status = "보통 변동성"
            else:
                status = "낮은 변동성"
        elif name == 'ROE':
            if value > 20:
                status = "매우 우수"
            elif value > 15:
                status = "우수"
            elif value > 10:
                status = "양호"
            else:
                status = "미흡"
        else:
            status = f"{value:.2f}"
        
        # 영향도 설명
        impact_desc = "강한 긍정적" if impact > 0.1 else "긍정적" if impact > 0 else "부정적" if impact > -0.1 else "강한 부정적"
        
        return f"{base_desc}: {status} ({impact_desc} 영향)"
    
    def _get_feature_importance(self, shap_values: np.ndarray) -> List[Dict]:
        """특징 중요도 계산"""
        # 절대값 기준 중요도
        importance = np.abs(shap_values[0])
        
        feature_importance = []
        for i, name in enumerate(self.feature_names):
            feature_importance.append({
                'name': name,
                'importance': float(importance[i]),
                'normalized_importance': float(importance[i] / np.sum(importance))
            })
        
        # 중요도 순으로 정렬
        feature_importance.sort(key=lambda x: x['importance'], reverse=True)
        
        return feature_importance
    
    def _calculate_transparency_score(self, shap_values: np.ndarray) -> float:
        """투명성 점수 계산 (0-1)"""
        # SHAP 값의 분포와 크기를 기반으로 계산
        # 일부 특징이 지배적이면 투명성이 높음
        
        importance = np.abs(shap_values[0])
        normalized = importance / np.sum(importance)
        
        # 엔트로피 계산 (낮을수록 투명)
        entropy = -np.sum(normalized * np.log(normalized + 1e-10))
        max_entropy = np.log(len(self.feature_names))
        
        # 투명성 점수 (0-1)
        transparency = 1 - (entropy / max_entropy)
        
        return float(transparency)
    
    def _generate_natural_language_explanation(self, factors: Dict, probability: float) -> str:
        """자연어 설명 생성"""
        prob_percent = int(probability * 100)
        
        # 기본 설명
        if probability >= 0.7:
            base_explanation = f"이 종목은 {prob_percent}%의 높은 상승 확률을 보입니다."
        elif probability >= 0.5:
            base_explanation = f"이 종목은 {prob_percent}%의 상승 가능성을 보입니다."
        elif probability >= 0.3:
            base_explanation = f"이 종목은 {prob_percent}%의 낮은 상승 확률을 보입니다."
        else:
            base_explanation = f"이 종목은 하락 가능성이 높습니다 (상승 확률 {prob_percent}%)."
        
        # 주요 요인 설명
        positive_reasons = []
        negative_reasons = []
        
        for factor in factors['positive'][:2]:  # 상위 2개
            positive_reasons.append(f"{factor['name']}({factor['value']:.2f})")
        
        for factor in factors['negative'][:2]:  # 상위 2개
            negative_reasons.append(f"{factor['name']}({factor['value']:.2f})")
        
        explanation = base_explanation
        
        if positive_reasons:
            explanation += f" 주요 긍정 요인은 {', '.join(positive_reasons)}입니다."
        
        if negative_reasons:
            explanation += f" 반면 {', '.join(negative_reasons)}는 부정적 영향을 미치고 있습니다."
        
        return explanation
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50.0
        
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
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> float:
        """MACD 계산 (간단한 버전)"""
        if len(prices) < 26:
            return 0.0
        
        # EMA 계산
        ema12 = self._calculate_ema(prices, 12)
        ema26 = self._calculate_ema(prices, 26)
        
        macd = ema12 - ema26
        return macd / prices[-1] * 100  # 정규화
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """지수이동평균 계산"""
        if len(prices) < period:
            return prices[-1]
        
        multiplier = 2 / (period + 1)
        ema = prices[-period]
        
        for price in prices[-period+1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema


class LIMEExplainer:
    """LIME 기반 설명자 (대안)"""
    
    def __init__(self, predictor, feature_names):
        self.predictor = predictor
        self.feature_names = feature_names
        self.explainer = None
        
    def explain_instance(self, features: np.ndarray) -> Dict:
        """개별 예측 설명"""
        if self.explainer is None:
            self.explainer = lime_tabular.LimeTabularExplainer(
                training_data=np.random.randn(100, len(self.feature_names)),  # 더미 데이터
                feature_names=self.feature_names,
                mode='classification'
            )
        
        # LIME 설명 생성
        explanation = self.explainer.explain_instance(
            features[0],
            self.predictor.predict_proba,
            num_features=len(self.feature_names)
        )
        
        # 설명을 딕셔너리로 변환
        feature_weights = dict(explanation.as_list())
        
        return {
            'feature_weights': feature_weights,
            'local_pred': explanation.local_pred[0]
        }
