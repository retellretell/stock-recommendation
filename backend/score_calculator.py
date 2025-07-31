"""
펀더멘털 스코어 계산기
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class FundamentalScorer:
    """펀더멘털 지표 기반 스코어 계산"""
    
    def __init__(self):
        # 기본 가중치
        self.default_weights = {
            'ROE': 0.40,
            'EPS_YoY': 0.30,
            'Revenue_YoY': 0.30
        }
        
        # 업종별 가중치 (로드맵)
        self.sector_weights = {
            'IT': {'ROE': 0.30, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.30},
            '제조': {'ROE': 0.35, 'EPS_YoY': 0.25, 'Revenue_YoY': 0.40},
            '금융': {'ROE': 0.50, 'EPS_YoY': 0.30, 'Revenue_YoY': 0.20},
            '바이오': {'ROE': 0.20, 'EPS_YoY': 0.40, 'Revenue_YoY': 0.40},
            '소비재': {'ROE': 0.35, 'EPS_YoY': 0.35, 'Revenue_YoY': 0.30}
        }
    
    async def calculate_score(self, stock_data: Dict) -> float:
        """펀더멘털 스코어 계산"""
        try:
            # 섹터별 가중치 선택
            sector = stock_data.get('sector', 'Unknown')
            weights = self.sector_weights.get(sector, self.default_weights)
            
            # 지표 추출
            metrics = self._extract_metrics(stock_data)
            
            # 정규화
            normalized = self._normalize_metrics(metrics)
            
            # 가중 평균 계산
            score = sum(weights[metric] * normalized[metric] for metric in weights)
            
            return round(score, 4)
            
        except Exception as e:
            logger.error(f"펀더멘털 스코어 계산 오류: {e}")
            return 0.5  # 기본값
    
    async def calculate_detailed_score(self, stock_data: Dict) -> Tuple[float, Dict[str, float]]:
        """상세 펀더멘털 스코어 계산 (breakdown 포함)"""
        try:
            sector = stock_data.get('sector', 'Unknown')
            weights = self.sector_weights.get(sector, self.default_weights)
            
            # 지표 추출
            metrics = self._extract_metrics(stock_data)
            
            # 정규화
            normalized = self._normalize_metrics(metrics)
            
            # 각 지표별 점수
            breakdown = {}
            for metric, weight in weights.items():
                breakdown[metric] = {
                    'raw_value': metrics[metric],
                    'normalized': normalized[metric],
                    'weight': weight,
                    'contribution': weight * normalized[metric]
                }
            
            # 총 점수
            total_score = sum(item['contribution'] for item in breakdown.values())
            
            return round(total_score, 4), breakdown
            
        except Exception as e:
            logger.error(f"상세 스코어 계산 오류: {e}")
            return 0.5, {}
    
    def _extract_metrics(self, stock_data: Dict) -> Dict[str, float]:
        """재무 지표 추출 (누락 처리 포함)"""
        metrics = {}
        
        # ROE
        roe = stock_data.get('roe', None)
        if roe is None or roe == 0:
            # 직전 분기 값 시도 (실제로는 과거 데이터 조회 필요)
            roe = stock_data.get('prev_roe', 0)
        metrics['ROE'] = roe
        
        # EPS YoY
        eps_yoy = stock_data.get('eps_yoy', None)
        if eps_yoy is None:
            # EPS 성장률 계산
            current_eps = stock_data.get('eps', 0)
            prev_eps = stock_data.get('prev_year_eps', 1)
            if prev_eps != 0:
                eps_yoy = ((current_eps - prev_eps) / abs(prev_eps)) * 100
            else:
                eps_yoy = 0
        metrics['EPS_YoY'] = eps_yoy
        
        # Revenue YoY
        revenue_yoy = stock_data.get('revenue_yoy', None)
        if revenue_yoy is None:
            # 매출 성장률 계산
            current_revenue = stock_data.get('revenue', 0)
            prev_revenue = stock_data.get('prev_year_revenue', 1)
            if prev_revenue != 0:
                revenue_yoy = ((current_revenue - prev_revenue) / abs(prev_revenue)) * 100
            else:
                revenue_yoy = 0
        metrics['Revenue_YoY'] = revenue_yoy
        
        return metrics
    
    def _normalize_metrics(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """지표 정규화 (0-1 범위)"""
        normalized = {}
        
        # ROE: 0-30% 범위로 정규화
        roe = metrics['ROE']
        if roe < 0:
            normalized['ROE'] = 0
        elif roe > 30:
            normalized['ROE'] = 1
        else:
            normalized['ROE'] = roe / 30
        
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
        
        return normalized
    
    def get_sector_weights(self, sector: str) -> Dict[str, float]:
        """섹터별 가중치 조회"""
        return self.sector_weights.get(sector, self.default_weights)
