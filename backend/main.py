"""
주식 날씨 예보판 - FastAPI 메인 서버
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import os
from dotenv import load_dotenv

from data_pipeline import DataPipeline
from score_calculator import FundamentalScorer
from ml_predictor import StockPredictor
from cache_manager import CacheManager

# 환경 설정
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="주식 날씨 예보판 API",
    description="AI 기반 주식 상승/하락 확률 예측 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 인스턴스
data_pipeline = DataPipeline()
scorer = FundamentalScorer()
predictor = StockPredictor()
cache = CacheManager()

# 데이터 모델
class StockRanking(BaseModel):
    ticker: str
    name: str
    sector: str
    probability: float
    expected_return: float
    fundamental_score: float
    weather_icon: str
    confidence: float

class DetailedStock(BaseModel):
    ticker: str
    name: str
    sector: str
    current_price: float
    probability: float
    expected_return: float
    fundamental_breakdown: Dict[str, float]
    price_history: List[Dict[str, float]]
    news_sentiment: Optional[float]
    technical_indicators: Dict[str, float]
    last_updated: datetime

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    logger.info("주식 날씨 예보판 서버 시작...")
    
    # 캐시 초기화
    await cache.initialize()
    
    # ML 모델 로드
    await predictor.load_models()
    
    # 초기 데이터 수집 (백그라운드)
    asyncio.create_task(initial_data_collection())

async def initial_data_collection():
    """초기 데이터 수집"""
    try:
        # 한국 주식
        kr_tickers = await data_pipeline.get_kr_tickers()
        await data_pipeline.fetch_batch_data(kr_tickers[:100], market='KR')
        
        # 미국 주식
        us_tickers = await data_pipeline.get_us_tickers()
        await data_pipeline.fetch_batch_data(us_tickers[:100], market='US')
        
        logger.info("초기 데이터 수집 완료")
    except Exception as e:
        logger.error(f"초기 데이터 수집 실패: {e}")

@app.get("/")
async def root():
    """API 정보"""
    return {
        "service": "Stock Weather Dashboard",
        "version": "1.0.0",
        "endpoints": {
            "/rankings": "상승/하락 확률 랭킹",
            "/detail/{ticker}": "종목 상세 정보",
            "/sectors": "섹터별 날씨 지도",
            "/health": "서버 상태"
        }
    }

@app.get("/rankings", response_model=Dict[str, List[StockRanking]])
async def get_rankings(
    market: str = "ALL",
    limit: int = 20,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """상승/하락 확률 랭킹 조회"""
    try:
        # 캐시 확인
        cache_key = f"rankings_{market}_{limit}"
        cached = await cache.get(cache_key)
        
        if cached and not await should_refresh_cache(cached):
            return cached
        
        # 새로운 데이터 수집 및 예측
        stocks = await get_stock_predictions(market)
        
        # 상승/하락 확률로 정렬
        top_gainers = sorted(stocks, key=lambda x: x['probability'], reverse=True)[:limit]
        top_losers = sorted(stocks, key=lambda x: x['probability'])[:limit]
        
        # 날씨 아이콘 추가
        for stock in top_gainers + top_losers:
            stock['weather_icon'] = get_weather_icon(stock['probability'])
        
        rankings = {
            "top_gainers": [StockRanking(**s) for s in top_gainers],
            "top_losers": [StockRanking(**s) for s in top_losers],
            "updated_at": datetime.now().isoformat()
        }
        
        # 캐시 업데이트 (백그라운드)
        background_tasks.add_task(cache.set, cache_key, rankings, ttl=3600)
        
        return rankings
        
    except Exception as e:
        logger.error(f"랭킹 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detail/{ticker}", response_model=DetailedStock)
async def get_stock_detail(ticker: str):
    """종목 상세 정보 조회"""
    try:
        # 캐시 확인
        cache_key = f"detail_{ticker}"
        cached = await cache.get(cache_key)
        
        if cached and (datetime.now() - cached['last_updated']).seconds < 3600:
            return DetailedStock(**cached)
        
        # 데이터 수집
        stock_data = await data_pipeline.get_stock_data(ticker)
        
        if not stock_data:
            raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
        
        # 펀더멘털 분석
        fundamental_score, breakdown = await scorer.calculate_detailed_score(stock_data)
        
        # 가격 예측
        prediction = await predictor.predict_single(stock_data)
        
        # 기술적 지표 계산
        technical = calculate_technical_indicators(stock_data['price_history'])
        
        # 뉴스 감성 분석 (옵션)
        news_sentiment = await analyze_news_sentiment(ticker) if ticker.endswith('.KS') else None
        
        detailed_info = {
            "ticker": ticker,
            "name": stock_data['name'],
            "sector": stock_data['sector'],
            "current_price": stock_data['current_price'],
            "probability": prediction['probability'],
            "expected_return": prediction['expected_return'],
            "fundamental_breakdown": breakdown,
            "price_history": stock_data['price_history'][-120:],  # 최근 120일
            "news_sentiment": news_sentiment,
            "technical_indicators": technical,
            "last_updated": datetime.now()
        }
        
        # 캐시 저장
        await cache.set(cache_key, detailed_info, ttl=3600)
        
        return DetailedStock(**detailed_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상세 정보 조회 오류 {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sectors")
async def get_sector_weather():
    """섹터별 날씨 지도"""
    try:
        # 섹터별 평균 확률 계산
        sector_data = await data_pipeline.get_sector_aggregates()
        
        sector_weather = []
        for sector, data in sector_data.items():
            avg_probability = data['avg_probability']
            weather = {
                "sector": sector,
                "probability": avg_probability,
                "weather_icon": get_weather_icon(avg_probability),
                "weather_desc": get_weather_description(avg_probability),
                "stock_count": data['count'],
                "top_stock": data['top_stock']
            }
            sector_weather.append(weather)
        
        return {
            "sectors": sorted(sector_weather, key=lambda x: x['probability'], reverse=True),
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"섹터 날씨 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    try:
        # 각 컴포넌트 상태 확인
        cache_status = await cache.health_check()
        model_status = predictor.is_loaded
        
        return {
            "status": "healthy" if cache_status and model_status else "unhealthy",
            "cache": "ok" if cache_status else "error",
            "models": "loaded" if model_status else "not loaded",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 헬퍼 함수들
async def should_refresh_cache(cached_data: Dict) -> bool:
    """캐시 갱신 필요 여부 확인"""
    if not cached_data:
        return True
    
    # 3시간 TTL
    if 'updated_at' in cached_data:
        age = (datetime.now() - datetime.fromisoformat(cached_data['updated_at'])).seconds
        if age > 10800:  # 3시간
            return True
    
    # 최근 1시간 이내 데이터는 유지
    if age < 3600:
        return False
    
    # ±5% 변동 체크 (구현 필요)
    # TODO: 실시간 가격과 비교하여 큰 변동이 있으면 True
    
    return False

async def get_stock_predictions(market: str) -> List[Dict]:
    """주식 예측 데이터 생성"""
    # 티커 목록 가져오기
    if market == "KR":
        tickers = await data_pipeline.get_kr_tickers()
    elif market == "US":
        tickers = await data_pipeline.get_us_tickers()
    else:  # ALL
        kr_tickers = await data_pipeline.get_kr_tickers()
        us_tickers = await data_pipeline.get_us_tickers()
        tickers = kr_tickers[:50] + us_tickers[:50]
    
    predictions = []
    
    # 배치 처리
    for i in range(0, len(tickers), 100):
        batch = tickers[i:i+100]
        batch_data = await data_pipeline.fetch_batch_data(batch, market)
        
        for ticker, data in batch_data.items():
            if data:
                # 펀더멘털 스코어
                fundamental_score = await scorer.calculate_score(data)
                
                # ML 예측
                prediction = await predictor.predict_single(data)
                
                predictions.append({
                    "ticker": ticker,
                    "name": data.get('name', ticker),
                    "sector": data.get('sector', 'Unknown'),
                    "probability": prediction['probability'],
                    "expected_return": prediction['expected_return'],
                    "fundamental_score": fundamental_score,
                    "confidence": prediction.get('confidence', 0.5)
                })
    
    return predictions

def get_weather_icon(probability: float) -> str:
    """확률에 따른 날씨 아이콘"""
    if probability >= 0.7:
        return "☀️"  # 맑음
    elif probability >= 0.6:
        return "🌤️"  # 약간 구름
    elif probability >= 0.4:
        return "⛅"  # 구름 많음
    elif probability >= 0.3:
        return "🌥️"  # 흐림
    else:
        return "🌧️"  # 비

def get_weather_description(probability: float) -> str:
    """확률에 따른 날씨 설명"""
    if probability >= 0.7:
        return "맑고 화창한 상승세가 예상됩니다"
    elif probability >= 0.6:
        return "대체로 맑은 상승 가능성이 있습니다"
    elif probability >= 0.4:
        return "변동성이 있는 구름 낀 날씨입니다"
    elif probability >= 0.3:
        return "흐린 날씨로 조정 가능성이 있습니다"
    else:
        return "비 오는 날씨, 하락 주의가 필요합니다"

def calculate_technical_indicators(price_history: List[Dict]) -> Dict[str, float]:
    """기술적 지표 계산"""
    if len(price_history) < 20:
        return {}
    
    closes = [p['close'] for p in price_history]
    
    # 이동평균
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
    
    # RSI
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    avg_gain = sum(gains[-14:]) / 14 if gains else 0
    avg_loss = sum(losses[-14:]) / 14 if losses else 0
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    return {
        "ma20": ma20,
        "ma60": ma60,
        "rsi": rsi,
        "volatility": calculate_volatility(closes[-20:])
    }

def calculate_volatility(prices: List[float]) -> float:
    """변동성 계산"""
    import numpy as np
    returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
    return np.std(returns) * np.sqrt(252) * 100  # 연율화

async def analyze_news_sentiment(ticker: str) -> float:
    """뉴스 감성 분석 (한국 주식만)"""
    # TODO: 실제 구현 시 news_analyzer.py 모듈 사용
    # 임시로 랜덤 값 반환
    import random
    return random.uniform(-1, 1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
