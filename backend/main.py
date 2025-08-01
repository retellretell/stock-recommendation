"""
주식 날씨 예보판 - FastAPI 메인 서버 (개선된 버전)
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

from config import settings
from models import *
from data_pipeline import DataPipeline
from score_calculator import FundamentalScorer
from ml_predictor import StockPredictor
from cache_manager import CacheManager
from exceptions import *

# 구조화된 로깅 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# 전역 인스턴스
data_pipeline = None
scorer = None
predictor = None
cache = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global data_pipeline, scorer, predictor, cache
    
    logger.info("application_startup", env=settings.env)
    
    try:
        # 설정 검증
        settings.validate_settings()
        
        # 인스턴스 초기화
        cache = CacheManager(settings.cache_db_path)
        await cache.initialize()
        
        data_pipeline = DataPipeline(cache)
        scorer = FundamentalScorer()
        predictor = StockPredictor()
        
        # ML 모델 로드
        await predictor.load_models()
        
        # 초기 데이터 수집 (백그라운드)
        asyncio.create_task(initial_data_collection())
        
        logger.info("application_startup_complete")
        
    except Exception as e:
        logger.error("application_startup_failed", error=str(e))
        raise
    
    yield
    
    # 종료 시 정리
    logger.info("application_shutdown")
    if cache:
        await cache.close()

# FastAPI 앱 초기화
app = FastAPI(
    title="주식 날씨 예보판 API",
    description="AI 기반 주식 상승/하락 확률 예측 서비스",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 에러 핸들러
@app.exception_handler(StockWeatherException)
async def stock_weather_exception_handler(request: Request, exc: StockWeatherException):
    logger.error("custom_exception", exception=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "type": exc.__class__.__name__}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", exception=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "InternalError"}
    )

# 미들웨어: 요청 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        "request_processed",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        process_time=process_time
    )
    
    return response

async def initial_data_collection():
    """초기 데이터 수집"""
    try:
        logger.info("initial_data_collection_started")
        
        # 한국 주식
        kr_tickers = await data_pipeline.get_kr_tickers()
        await data_pipeline.fetch_batch_data(kr_tickers[:100], market=Market.KR)
        
        # 미국 주식
        us_tickers = await data_pipeline.get_us_tickers()
        await data_pipeline.fetch_batch_data(us_tickers[:100], market=Market.US)
        
        logger.info("initial_data_collection_completed")
    except Exception as e:
        logger.error("initial_data_collection_failed", error=str(e))

@app.get("/")
async def root():
    """API 정보"""
    return {
        "service": "Stock Weather Dashboard",
        "version": "2.0.0",
        "environment": settings.env,
        "endpoints": {
            "/rankings": "상승/하락 확률 랭킹",
            "/detail/{ticker}": "종목 상세 정보",
            "/sectors": "섹터별 날씨 지도",
            "/health": "서버 상태"
        }
    }

@app.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    market: Market = Market.ALL,
    limit: int = 20,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """상승/하락 확률 랭킹 조회"""
    logger.info("rankings_requested", market=market, limit=limit)
    
    try:
        # 캐시 키 생성
        cache_key = cache.generate_cache_key(f"rankings_{market}_{limit}", "rankings")
        cached = await cache.get(cache_key)
        
        if cached and not await should_refresh_cache(cached):
            logger.info("rankings_from_cache", cache_key=cache_key)
            return RankingsResponse(**cached)
        
        # 새로운 데이터 수집 및 예측
        stocks = await get_stock_predictions(market)
        
        # 상승/하락 확률로 정렬
        top_gainers = sorted(stocks, key=lambda x: x['probability'], reverse=True)[:limit]
        top_losers = sorted(stocks, key=lambda x: x['probability'])[:limit]
        
        # 날씨 아이콘 추가
        for stock in top_gainers + top_losers:
            stock['weather_icon'] = get_weather_icon(stock['probability'])
        
        rankings_data = {
            "top_gainers": [StockRanking(**s) for s in top_gainers],
            "top_losers": [StockRanking(**s) for s in top_losers],
            "updated_at": datetime.now()
        }
        
        # 캐시 업데이트 (백그라운드)
        background_tasks.add_task(
            cache.set, 
            cache_key, 
            rankings_data, 
            ttl=settings.cache_ttl
        )
        
        logger.info("rankings_generated", gainers_count=len(top_gainers), losers_count=len(top_losers))
        return RankingsResponse(**rankings_data)
        
    except Exception as e:
        logger.error("rankings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detail/{ticker}", response_model=DetailedStock)
async def get_stock_detail(ticker: str):
    """종목 상세 정보 조회"""
    logger.info("stock_detail_requested", ticker=ticker)
    
    try:
        # 캐시 확인
        cache_key = cache.generate_cache_key(ticker, "detail")
        cached = await cache.get(cache_key)
        
        if cached and (datetime.now() - cached['last_updated']).seconds < settings.cache_freshness:
            logger.info("stock_detail_from_cache", ticker=ticker)
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
        technical = calculate_technical_indicators(stock_data.get('price_history', []))
        
        # 뉴스 감성 분석 (옵션)
        news_sentiment = await analyze_news_sentiment(ticker) if ticker.endswith('.KS') else None
        
        # 가격 이력 변환
        price_history = [
            PriceHistory(**p) for p in stock_data.get('price_history', [])[-120:]
        ]
        
        detailed_info = DetailedStock(
            ticker=ticker,
            name=stock_data.get('name', ticker),
            sector=stock_data.get('sector', 'Unknown'),
            current_price=stock_data.get('current_price', 0),
            probability=prediction['probability'],
            expected_return=prediction['expected_return'],
            fundamental_breakdown=breakdown,
            price_history=price_history,
            news_sentiment=news_sentiment,
            technical_indicators=technical,
            last_updated=datetime.now()
        )
        
        # 캐시 저장
        await cache.set(cache_key, detailed_info.dict(), ttl=settings.cache_ttl)
        
        logger.info("stock_detail_generated", ticker=ticker)
        return detailed_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("stock_detail_error", ticker=ticker, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sectors")
async def get_sector_weather():
    """섹터별 날씨 지도"""
    logger.info("sector_weather_requested")
    
    try:
        # 섹터별 평균 확률 계산
        sector_data = await data_pipeline.get_sector_aggregates()
        
        sector_weather = []
        for sector, data in sector_data.items():
            avg_probability = data.get('avg_probability', 0.5)
            weather = SectorWeather(
                sector=sector,
                probability=avg_probability,
                weather_icon=get_weather_icon(avg_probability),
                weather_desc=get_weather_description(avg_probability),
                stock_count=data.get('count', 0),
                top_stock=data.get('top_stock', '')
            )
            sector_weather.append(weather)
        
        result = {
            "sectors": sorted(sector_weather, key=lambda x: x.probability, reverse=True),
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info("sector_weather_generated", sector_count=len(sector_weather))
        return result
        
    except Exception as e:
        logger.error("sector_weather_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    try:
        # 각 컴포넌트 상태 확인
        checks = {
            "cache": await cache.health_check() if cache else False,
            "models": predictor.is_loaded if predictor else False,
            "data_pipeline": data_pipeline is not None
        }
        
        all_healthy = all(checks.values())
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
            "environment": settings.env
        }
    except Exception as e:
        logger.error("health_check_error", error=str(e))
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
    
    # 업데이트 시간 확인
    if 'updated_at' in cached_data:
        if isinstance(cached_data['updated_at'], str):
            updated_at = datetime.fromisoformat(cached_data['updated_at'])
        else:
            updated_at = cached_data['updated_at']
        
        age = (datetime.now() - updated_at).seconds
        
        # 3시간 TTL
        if age > settings.cache_ttl:
            return True
        
        # 최근 1시간 이내 데이터는 유지
        if age < settings.cache_freshness:
            return False
    
    # TODO: ±5% 변동 체크 구현
    
    return False

async def get_stock_predictions(market: Market) -> List[Dict]:
    """주식 예측 데이터 생성"""
    logger.info("generating_predictions", market=market)
    
    # 티커 목록 가져오기
    if market == Market.KR:
        tickers = await data_pipeline.get_kr_tickers()
    elif market == Market.US:
        tickers = await data_pipeline.get_us_tickers()
    else:  # ALL
        kr_tickers = await data_pipeline.get_kr_tickers()
        us_tickers = await data_pipeline.get_us_tickers()
        tickers = kr_tickers[:50] + us_tickers[:50]
    
    predictions = []
    
    # 배치 처리
    for i in range(0, len(tickers), settings.batch_size):
        batch = tickers[i:i+settings.batch_size]
        batch_data = await data_pipeline.fetch_batch_data(batch, market)
        
        for ticker, data in batch_data.items():
            if data:
                try:
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
                except Exception as e:
                    logger.error("prediction_error", ticker=ticker, error=str(e))
    
    logger.info("predictions_generated", count=len(predictions))
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
        return {
            "ma20": 0,
            "ma60": 0,
            "rsi": 50,
            "volatility": 0
        }
    
    try:
        closes = [p['close'] for p in price_history]
        
        # 이동평균
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
        
        # RSI
        rsi = calculate_rsi(closes)
        
        # 변동성
        volatility = calculate_volatility(closes[-20:])
        
        return {
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "rsi": round(rsi, 2),
            "volatility": round(volatility, 2)
        }
    except Exception as e:
        logger.error("technical_indicators_error", error=str(e))
        return {
            "ma20": 0,
            "ma60": 0,
            "rsi": 50,
            "volatility": 0
        }

def calculate_rsi(prices: List[float], period: int = 14) -> float:
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
    
    avg_gain = sum(gains[-period:]) / period if gains else 0
    avg_loss = sum(losses[-period:]) / period if losses else 0
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_volatility(prices: List[float]) -> float:
    """변동성 계산"""
    import numpy as np
    
    if len(prices) < 2:
        return 0.0
    
    returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
    return np.std(returns) * np.sqrt(252) * 100  # 연율화

async def analyze_news_sentiment(ticker: str) -> float:
    """뉴스 감성 분석 (한국 주식만)"""
    # TODO: 실제 구현 시 news_analyzer.py 모듈 사용
    import random
    return random.uniform(-1, 1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
