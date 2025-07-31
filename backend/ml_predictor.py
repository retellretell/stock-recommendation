"""
ML 예측 모델
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import onnxruntime as ort
import logging
import os
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class StockPredictor:
    """주식 상승/하락 예측 모델"""
    
    def __init__(self):
        self.models = {}
        self.model_urls = {
            'lstm': 'https://github.com/yourusername/stock-weather/releases/download/v1.0/lstm_model.onnx',
            'gru': 'https://github.com/yourusername/stock-weather/releases/download/v1.0/gru_model.onnx',
            'xgboost': 'https://github.com/yourusername/stock-weather/releases/download/v1.0/xgboost_model.onnx',
            'transformer': 'https://github.com/yourusername/stock-weather/releases/download/v1.0/transformer_model.onnx'
        }
        self.is_loaded = False
        
    async def load_models(self):
        """모델 로드 (ONNX)"""
        model_dir = "models"
        os.makedirs(model_dir, exist_ok=True)
        
        for model_name, url in self.model_urls.items():
            model_path = os.path.join(model_dir, f"{model_name}.onnx")
            
            # 모델 파일이 없으면 다운로드
            if not os.path.exists(model_path):
                logger.info(f"{model_name} 모델 다운로드 중...")
                await self._download_model(url, model_path)
            
            # ONNX 런타임 세션 생성
            try:
                self.models[model_name] = ort.InferenceSession(model_path)
                logger.info(f"{model_name} 모델 로드 완료")
            except Exception as e:
                logger.error(f"{model_name} 모델 로드 실패: {e}")
        
        self.is_loaded = len(self.models) > 0
        
        if not self.is_loaded:
            # 모델이 없을 경우 더미 예측기 사용
            logger.warning("ML 모델 로드 실패, 더미 예측기 사용")
            self.models['dummy'] = DummyPredictor()
    
    async def _download_model(self, url: str, path: str):
        """모델 파일 다운로드"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(path, 'wb') as f:
                            f.write(content)
                        logger.info(f"모델 다운로드 완료: {path}")
                    else:
                        logger.error(f"모델 다운로드 실패: {response.status}")
        except Exception as e:
            logger.error(f"모델 다운로드 오류: {e}")
    
    async def predict_single(self, stock_data: Dict) -> Dict[str, float]:
        """단일 종목 예측"""
        try:
            # 특징 추출
            features = self._extract_features(stock_data)
            
            # 각 모델 예측
            predictions = []
            confidences = []
            
            for model_name, model in self.models.items():
                if model_name == 'dummy':
                    pred = model.predict(features)
                else:
                    pred = self._run_onnx_inference(model, features)
                
                predictions.append(pred['probability'])
                confidences.append(pred.get('confidence', 0.5))
            
            # 앙상블 (Soft Voting)
            avg_probability = np.mean(predictions)
            avg_confidence = np.mean(confidences)
            
            # 예상 수익률 계산
            expected_return = self._calculate_expected_return(avg_probability, stock_data)
            
            return {
                'probability': float(avg_probability),
                'expected_return': float(expected_return),
                'confidence': float(avg_confidence)
            }
            
        except Exception as e:
            logger.error(f"예측 오류: {e}")
            # 기본값 반환
            return {
                'probability': 0.5,
                'expected_return': 0.0,
                'confidence': 0.3
            }
    
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
        
        # 시장 데이터 (섹터 더미 변수 등 추가 가능)
        
        return np.array(features, dtype=np.float32).reshape(1, -1)
    
    def _run_onnx_inference(self, session: ort.InferenceSession, features: np.ndarray) -> Dict:
        """ONNX 모델 추론"""
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        # 추론 실행
        outputs = session.run([output_name], {input_name: features})
        probability = outputs[0][0]
        
        # Sigmoid 적용 (필요한 경우)
        if probability < 0 or probability > 1:
            probability = 1 / (1 + np.exp(-probability))
        
        return {
            'probability': float(probability),
            'confidence': 0.7  # 실제 모델에서는 신뢰도도 출력
        }
    
    def _calculate_expected_return(self, probability: float, stock_data: Dict) -> float:
        """예상 수익률 계산"""
        # 과거 변동성 기반 예상 수익률
        price_history = stock_data.get('price_history', [])
        if len(price_history) >= 20:
            prices = [p['close'] for p in price_history[-20:]]
            returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
            avg_return = np.mean(returns)
            volatility = np.std(returns)
            
            # 확률 기반 방향성 조정
            if probability > 0.5:
                expected = avg_return + volatility * (probability - 0.5) * 2
            else:
                expected = avg_return - volatility * (0.5 - probability) * 2
            
            return expected * 100  # 퍼센트로 변환
        
        return 0.0
    
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


class DummyPredictor:
    """더미 예측기 (모델이 없을 때 사용)"""
    
    def predict(self, features: np.ndarray) -> Dict:
        """간단한 규칙 기반 예측"""
        # 최근 수익률과 펀더멘털 점수 기반
        recent_return = features[0][0]  # 5일 평균 수익률
        fundamental_score = np.mean(features[0][5:9])  # 펀더멘털 지표 평균
        
        # 단순 가중 평균
        probability = 0.5 + recent_return * 2 + fundamental_score * 0.3
        probability = max(0, min(1, probability))  # 0-1 범위로 제한
        
        return {
            'probability': float(probability),
            'confidence': 0.3  # 낮은 신뢰도
        }
