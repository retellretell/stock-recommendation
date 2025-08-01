"""
펀더멘털 스코어 계산기 테스트
"""
import pytest
import asyncio
from backend.score_calculator import FundamentalScorer
from backend.models import FinancialMetrics

class TestFundamentalScorer:
    @pytest.fixture
    def scorer(self):
        return FundamentalScorer()
    
    @pytest.mark.asyncio
    async def test_normalize_metrics_boundary_cases(self, scorer):
        """경계값 테스트"""
        metrics = {
            'ROE': -25,  # 하한 초과
            'EPS_YoY': 150,  # 상한 초과
            'Revenue_YoY': -50  # 하한 초과
        }
        
        normalized = scorer._normalize_metrics(metrics)
        
        assert normalized['ROE'] == 0
        assert normalized['EPS_YoY'] == 1
        assert normalized['Revenue_YoY'] == 0
        
        # 정상 범위 테스트
        metrics_normal = {
            'ROE': 15,  # 정상
            'EPS_YoY': 30,  # 정상
            'Revenue_YoY': 10  # 정상
        }
        
        normalized_normal = scorer._normalize_metrics(metrics_normal)
        
        assert 0 < normalized_normal['ROE'] < 1
        assert 0 < normalized_normal['EPS_YoY'] < 1
        assert 0 < normalized_normal['Revenue_YoY'] < 1
    
    @pytest.mark.asyncio
    async def test_calculate_score_with_missing_data(self, scorer):
        """누락 데이터 처리 테스트"""
        stock_data = {
            'ticker': 'TEST001',
            'sector': 'IT',
            'roe': None,
            'eps_yoy': 20,
            'revenue_yoy': 15
        }
        
        score = await scorer.calculate_score(stock_data)
        
        assert 0 <= score <= 1
        assert isinstance(score, float)
    
    @pytest.mark.asyncio
    async def test_sector_weights_application(self, scorer):
        """섹터별 가중치 적용 테스트"""
        # IT 섹터 데이터
        it_stock = {
            'ticker': 'IT001',
            'sector': 'IT',
            'roe': 20,
            'eps_yoy': 50,
            'revenue_yoy': 30
        }
        
        # 금융 섹터 데이터 (같은 지표)
        financial_stock = {
            'ticker': 'FIN001',
            'sector': '금융',
            'roe': 20,
            'eps_yoy': 50,
            'revenue_yoy': 30
        }
        
        it_score = await scorer.calculate_score(it_stock)
        financial_score = await scorer.calculate_score(financial_stock)
        
        # 섹터별 가중치가 다르므로 점수도 달라야 함
        assert it_score != financial_score
    
    @pytest.mark.asyncio
    async def test_detailed_score_breakdown(self, scorer):
        """상세 점수 분석 테스트"""
        stock_data = {
            'ticker': 'TEST002',
            'sector': 'Technology',
            'roe': 15,
            'eps_yoy': 25,
            'revenue_yoy': 20
        }
        
        score, breakdown = await scorer.calculate_detailed_score(stock_data)
        
        assert isinstance(score, float)
        assert isinstance(breakdown, dict)
        assert 'ROE' in breakdown
        assert 'EPS_YoY' in breakdown
        assert 'Revenue_YoY' in breakdown
        
        # 각 항목의 기여도 합이 총 점수와 일치해야 함
        total_contribution = sum(item['contribution'] for item in breakdown.values())
        assert abs(total_contribution - score) < 0.001
    
    def test_financial_metrics_validation(self):
        """FinancialMetrics 모델 검증 테스트"""
        # 정상 데이터
        valid_metrics = FinancialMetrics(
            roe=15.5,
            eps_yoy=20.3,
            revenue_yoy=10.2
        )
        assert valid_metrics.roe == 15.5
        
        # 비정상 데이터
        with pytest.raises(ValueError):
            FinancialMetrics(
                roe=150,  # 범위 초과
                eps_yoy=20,
                revenue_yoy=10
            )
    
    def test_score_interpretation(self, scorer):
        """점수 해석 테스트"""
        interpretations = [
            (0.9, "A"),
            (0.7, "B"),
            (0.5, "C"),
            (0.3, "D"),
            (0.1, "F")
        ]
        
        for score, expected_grade in interpretations:
            result = scorer.get_score_interpretation(score)
            assert result['grade'] == expected_grade
            assert 'description' in result
            assert 'recommendation' in result
