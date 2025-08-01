"""
펀더멘털 스코어 계산기 (개선된 버전)
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import structlog

from config import settings
from models import FinancialMetrics
from exceptions import DataValidationError

logger = structlog.get_logger()

class FundamentalScorer:
    """펀더멘털 지표 기반 스코어 계산"""
    
    def __init__(self):
        # 기본 가중치
        self.default_weights = {
            'ROE': 0.40,
            'EPS_YoY': 0.30,
            'Revenue_YoY': 0.30
        }
        
        # 업종별 가중치
        self.sector_weights = {
            'IT': {'ROE': 0.30, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.30},
            '전기전자': {'ROE': 0.30, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.30},
            'Technology': {'ROE': 0.30, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.30},
            
            '제조': {'ROE': 0.35, 'EPS_YoY': 0.25, 'Revenue_YoY': 0.40},
            'Manufacturing': {'ROE': 0.35, 'EPS_YoY': 0.25, 'Revenue_YoY': 0.40},
            'Industrials': {'ROE': 0.35, 'EPS_YoY': 0.25, 'Revenue_YoY': 0.40},
            
            '금융': {'ROE': 0.50, 'EPS_YoY': 0.30, 'Revenue_YoY': 0.20},
            'Financial': {'ROE': 0.50, 'EPS_YoY': 0.30, 'Revenue_YoY': 0.20},
            'Financials': {'ROE': 0.50, 'EPS_YoY': 0.30, 'Revenue_YoY': 0.20},
            
            '바이오': {'ROE': 0.20, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.40},
            'Healthcare': {'ROE': 0.20, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.40},
            'Pharmaceuticals': {'ROE': 0.20, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.40},
            
            '소비재': {'ROE': 0.35, 'EPS_YoY': 0.35, 'Revenue_YoY': 0.30},
            'Consumer': {'ROE': 0.35, 'EPS_YoY': 0.35, 'Revenue_YoY': 0.30},
            'Consumer Cyclical': {'ROE': 0.35, 'EPS_YoY': 0.35, 'Revenue_YoY': 0.30}
        }
    
    async def calculate_score(self, stock_data: Dict) -> float:
        """펀더멘털 스코어 계산"""
        try:
            ticker = stock_data.get('ticker', 'unknown')
            sector = stock_data.get('sector', 'Unknown')
            
            logger.debug("calculating_fundamental_score", ticker=ticker, sector=sector)
            
            # 재무 지표 추출 및 검증
            metrics = self._extract_and_validate_metrics(stock_data)
            # 섹터별 가중치 선택
            weights = self.sector_weights.get(sector, self.default_weights)
            
            # 정규화
            normalized = self._normalize_metrics(metrics)
            
            # 가중 평균 계산
            score = sum(weights[metric] * normalized[metric] for metric in weights)
            
            logger.info(
                "fundamental_score_calculated",
                ticker=ticker,
                score=round(score, 4),
                metrics=metrics
            )
            
            return round(score, 4)
            
        except Exception as e:
            logger.error("fundamental_score_calculation_error", error=str(e), ticker=stock_data.get('ticker'))
            return 0.5  # 기본값
    
    async def calculate_detailed_score(self, stock_data: Dict) -> Tuple[float, Dict[str, Dict[str, float]]]:
        """상세 펀더멘털 스코어 계산 (breakdown 포함)"""
        try:
            ticker = stock_data.get('ticker', 'unknown')
            sector = stock_data.get('sector', 'Unknown')
            
            # 재무 지표 추출 및 검증
            metrics = self._extract_and_validate_metrics(stock_data)
            
            # 섹터별 가중치 선택
            weights = self.sector_weights.get(sector, self.default_weights)
            
            # 정규화
            normalized = self._normalize_metrics(metrics)
            
            # 각 지표별 점수 상세
            breakdown = {}
            for metric, weight in weights.items():
                breakdown[metric] = {
                    'raw_value': round(metrics.get(metric, 0), 2),
                    'normalized': round(normalized.get(metric, 0), 4),
                    'weight': weight,
                    'contribution': round(weight * normalized.get(metric, 0), 4)
                }
            
            # 총 점수
            total_score = sum(item['contribution'] for item in breakdown.values())
            
            logger.info(
                "detailed_score_calculated",
                ticker=ticker,
                score=round(total_score, 4),
                breakdown=breakdown
            )
            
            return round(total_score, 4), breakdown
            
        except Exception as e:
            logger.error("detailed_score_calculation_error", error=str(e))
            return 0.5, {}
    
    def _extract_and_validate_metrics(self, stock_data: Dict) -> Dict[str, float]:
        """재무 지표 추출 및 검증 (Pydantic 모델 사용)"""
        # 기본 메트릭 추출
        raw_metrics = {
            'roe': stock_data.get('roe'),
            'eps_yoy': stock_data.get('eps_yoy'),
            'revenue_yoy': stock_data.get('revenue_yoy')
        }
        
        # Pydantic 모델로 검증
        try:
            financial_metrics = FinancialMetrics(**raw_metrics)
            
            # 과거 데이터로 누락값 채우기
            historical_data = {
                'roe_prev_quarter': stock_data.get('prev_roe', 0),
                'eps': stock_data.get('eps', 0),
                'eps_prev_year': stock_data.get('prev_year_eps', 1),
                'revenue': stock_data.get('revenue', 0),
                'revenue_prev_year': stock_data.get('prev_year_revenue', 1)
            }
            
            financial_metrics = financial_metrics.fill_missing_values(historical_data)
            
            # 딕셔너리로 변환 (정규화를 위해)
            return {
                'ROE': financial_metrics.roe or 0,
                'EPS_YoY': financial_metrics.eps_yoy or 0,
                'Revenue_YoY': financial_metrics.revenue_yoy or 0
            }
            
        except ValueError as e:
            logger.warning("metrics_validation_warning", error=str(e))
            # 검증 실패 시 기본값 사용
            return {
                'ROE': 0,
                'EPS_YoY': 0,
                'Revenue_YoY': 0
            }
    
    def _normalize_metrics(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """지표 정규화 (0-1 범위)"""
        normalized = {}
        
        # ROE: -20% ~ 30% 범위로 정규화
        roe = metrics['ROE']
        if roe < -20:
            normalized['ROE'] = 0
        elif roe > 30:
            normalized['ROE'] = 1
        else:
            normalized['ROE'] = (roe + 20) / 50  # -20을 0으로, 30을 1로 매핑
        
        # EPS YoY: -50% ~ +100% 범위
        eps_yoy = metrics['EPS_YoY']
        if eps_yoy < -50:
            normalized['EPS_YoY'] = 0
        elif eps_yoy > 100:
            normalized['EPS_YoY'] = 1
        else:
            normalized['EPS_YoY'] = (eps_yoy + 50) / 150
        
        # Revenue YoY: -30% ~ +50% 범위
        revenue_yoy = metrics['Revenue_YoY']
        if revenue_yoy < -30:
            normalized['Revenue_YoY'] = 0
        elif revenue_yoy > 50:
            normalized['Revenue_YoY'] = 1
        else:
            normalized['Revenue_YoY'] = (revenue_yoy + 30) / 80
        
        # 모든 값이 0-1 범위인지 확인
        for key, value in normalized.items():
            normalized[key] = max(0, min(1, value))
        
        return normalized
    
    def get_sector_weights(self, sector: str) -> Dict[str, float]:
        """섹터별 가중치 조회"""
        return self.sector_weights.get(sector, self.default_weights)
    
    def get_score_interpretation(self, score: float) -> Dict[str, str]:
        """스코어 해석"""
        if score >= 0.8:
            return {
                "grade": "A",
                "description": "매우 우수한 펀더멘털",
                "recommendation": "적극 매수 고려"
            }
        elif score >= 0.6:
            return {
                "grade": "B",
                "description": "양호한 펀더멘털",
                "recommendation": "매수 고려"
            }
        elif score >= 0.4:
            return {
                "grade": "C",
                "description": "보통 수준의 펀더멘털",
                "recommendation": "중립"
            }
        elif score >= 0.2:
            return {
                "grade": "D",
                "description": "미흡한 펀더멘털",
                "recommendation": "주의 필요"
            }
        else:
            return {
                "grade": "F",
                "description": "매우 취약한 펀더멘털",
                "recommendation": "매수 보류"
            }
