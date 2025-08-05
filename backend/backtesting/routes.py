"""
백테스팅 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, List

from .tracker import PredictionTracker
from .paper_trading import PaperTradingEngine
from .analyzer import PerformanceAnalyzer
from .models import BacktestConfig

router = APIRouter(prefix="/api/backtest", tags=["backtesting"])

# 전역 인스턴스
tracker = PredictionTracker()
paper_trading = PaperTradingEngine()
analyzer = PerformanceAnalyzer()

@router.on_event("startup")
async def startup():
    """초기화"""
    await tracker.initialize()
    await paper_trading.initialize()

@router.get("/predictions")
async def get_predictions(
    ticker: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, le=1000)
):
    """예측 기록 조회"""
    try:
        predictions = await tracker.get_recent_predictions(ticker, limit)
        
        # 필터링
        if status:
            predictions = [p for p in predictions if p['status'] == status]
            
        if start_date:
            start = datetime.fromisoformat(start_date)
            predictions = [
                p for p in predictions 
                if datetime.fromisoformat(p['prediction_date']) >= start
            ]
            
        if end_date:
            end = datetime.fromisoformat(end_date)
            predictions = [
                p for p in predictions 
                if datetime.fromisoformat(p['prediction_date']) <= end
            ]
            
        return {
            'predictions': predictions,
            'total': len(predictions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/{prediction_id}")
async def get_prediction_detail(prediction_id: int):
    """예측 상세 조회"""
    predictions = await tracker.get_recent_predictions(limit=1000)
    
    for pred in predictions:
        if pred['id'] == prediction_id:
            return pred
            
    raise HTTPException(status_code=404, detail="Prediction not found")

@router.get("/portfolio")
async def get_portfolio():
    """현재 포트폴리오 상태"""
    try:
        summary = await paper_trading.get_portfolio_summary()
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades")
async def get_trades(
    ticker: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, le=1000)
):
    """거래 내역 조회"""
    # TODO: 실제 구현
    return {
        'trades': [],
        'total': 0
    }

@router.get("/performance/summary")
async def get_performance_summary(period: str = "daily"):
    """성과 요약"""
    try:
        if period not in ["daily", "weekly", "monthly", "all-time"]:
            raise HTTPException(status_code=400, detail="Invalid period")
            
        metrics = await tracker.calculate_performance_metrics(period)
        
        return metrics.dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/report")
async def get_performance_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """상세 성과 리포트"""
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
        else:
            start = datetime.now() - timedelta(days=30)
            
        if end_date:
            end = datetime.fromisoformat(end_date)
        else:
            end = datetime.now()
            
        report = await analyzer.generate_report(start, end)
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/comparison")
async def compare_periods(
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str
):
    """기간별 성과 비교"""
    try:
        comparison = await analyzer.generate_comparison_report(
            datetime.fromisoformat(period1_start),
            datetime.fromisoformat(period1_end),
            datetime.fromisoformat(period2_start),
            datetime.fromisoformat(period2_end)
        )
        
        return comparison
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def update_config(config: BacktestConfig):
    """백테스팅 설정 업데이트"""
    try:
        paper_trading.config = config
        
        return {
            'status': 'updated',
            'config': config.dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_config():
    """현재 백테스팅 설정"""
    return paper_trading.config.dict()

@router.post("/trades/close/{ticker}")
async def close_position(ticker: str, reason: str = "manual"):
    """포지션 수동 청산"""
    try:
        trade = await paper_trading.close_position(ticker, reason)
        
        if trade:
            return {
                'status': 'closed',
                'trade': trade.dict()
            }
        else:
            raise HTTPException(status_code=404, detail="Position not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights")
async def get_insights():
    """AI 인사이트"""
    try:
        # 최근 7일 분석
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        report = await analyzer.generate_report(start_date, end_date)
        
        return {
            'insights': report.get('insights', []),
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
