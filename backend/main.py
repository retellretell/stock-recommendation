"""
주식 날씨 예보판 - FastAPI 메인 서버 (개선된 버전)
접근성, 개인화, 설명가능한 AI 기능 추가
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

# 새로 추가된 모듈들
from explainable_ai import ExplainablePredictor
from personalization import UserPersonalization
from alternative_data import AlternativeDataAnalyzer
from enhanced_backtesting import EnhancedBacktester

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
explainable_predictor = None
cache = None
personalization = None
alternative_data = None
backtester = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global data_pipeline, scorer, predictor, explainable_predictor, cache, personalization, alternative_data, backtester
    
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
        
        # 새로운 컴포넌트 초기화
        explainable_predictor = ExplainablePredictor(predictor)
        personalization = UserPersonalization()
        alternative_data = AlternativeDataAnalyzer()
        backtester = EnhancedBacktester()
        
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
    description="AI 기반 주식 예측 서비스 - 설명가능한 AI와 접근성 강화",
    version="3.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
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
        "version": "3.0.0",
        "environment": settings.env,
        "endpoints": {
            "/rankings": "상승/하락 확률 랭킹",
            "/rankings/explained": "설명 포함 랭킹 (신규)",
            "/detail/{ticker}": "종목 상세 정보",
            "/detail/{ticker}/explained": "설명 가능한 AI 분석 (신규)",
            "/sectors": "섹터별 날씨 지도",
            "/personalized/{user_id}": "개인화 대시보드 (신규)",
            "/backtest": "백테스팅 결과 (신규)",
            "/health": "서버 상태"
        }
    }

@app.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    market: Market = Market.ALL,
    limit: int = 20,
    user_id: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """상승/하락 확률 랭킹 조회 (개선된 버전)"""
    logger.info("rankings_requested", market=market, limit=limit, user_id=user_id)
    
    try:
        # 개인화 설정 확인
        if user_id:
            user_prefs = await personalization.get_user_preferences(user_id)
            if user_prefs:
                # 선호 섹터 필터링
                preferred_sectors = user_prefs.get('preferred_sectors', [])
                risk_tolerance = user_prefs.get('risk_tolerance', 'moderate')
        
        # 캐시 키 생성
        cache_key = cache.generate_cache_key(f"rankings_{market}_{limit}", "rankings")
        cached = await cache.get(cache_key)
        
        if cached and not await should_refresh_cache(cached):
            logger.info("rankings_from_cache", cache_key=cache_key)
            return RankingsResponse(**cached)
        
        # 새로운 데이터 수집 및 예측
        stocks = await get_stock_predictions(market)
        
        # 대체 데이터 포함
        for stock in stocks:
            alt_data = await alternative_data.analyze_social_sentiment(stock['ticker'])
            stock['social_sentiment'] = alt_data['composite_score']
            
            # 종합 점수 재계산 (소셜 감성 포함)
            stock['composite_score'] = (
                stock['probability'] * 0.6 +
                stock['fundamental_score'] * 0.3 +
                stock['social_sentiment'] * 0.1
            )
        
        # 개인화 필터링
        if user_id and preferred_sectors:
            stocks = [s for s in stocks if s['sector'] in preferred_sectors]
        
        # 리스크 수준별 필터링
        if user_id and risk_tolerance:
            stocks = filter_by_risk_tolerance(stocks, risk_tolerance)
        
        # 상승/하락 확률로 정렬
        top_gainers = sorted(stocks, key=lambda x: x['composite_score'], reverse=True)[:limit]
        top_losers = sorted(stocks, key=lambda x: x['composite_score'])[:limit]
        
        # 날씨 아이콘 및 접근성 정보 추가
        for stock in top_gainers + top_losers:
            stock['weather_icon'] = get_weather_icon(stock['probability'])
            stock['accessibility_label'] = get_accessibility_label(stock)
        
        rankings_data = {
            "top_gainers": [StockRanking(**s) for s in top_gainers],
            "top_losers": [StockRanking(**s) for s in top_losers],
            "updated_at": datetime.now(),
            "user_personalized": user_id is not None
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

@app.get("/rankings/explained")
async def get_explained_rankings(
    market: Market = Market.ALL,
    limit: int = 10
):
    """설명 가능한 AI 랭킹"""
    logger.info("explained_rankings_requested", market=market, limit=limit)
    
    try:
        # 기본 예측 가져오기
        stocks = await get_stock_predictions(market)
        
        # 각 종목에 대해 설명 추가
        explained_stocks = []
        for stock in stocks[:limit]:  # 성능을 위해 상위 종목만
            stock_data = await data_pipeline.get_stock_data(stock['ticker'])
            
            # 설명 가능한 예측
            explained_prediction = await explainable_predictor.predict_with_explanation(stock_data)
            
            stock['explanation'] = explained_prediction['explanation']
            stock['transparency_score'] = explained_prediction['transparency_score']
            
            explained_stocks.append(stock)
        
        return {
            "stocks": explained_stocks,
            "explanation_methodology": "SHAP (SHapley Additive exPlanations)",
            "updated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error("explained_rankings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detail/{ticker}", response_model=DetailedStock)
async def get_stock_detail(ticker: str):
    """종목 상세 정보 조회 (개선된 버전)"""
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
        
        # 대체 데이터 분석
        alt_data = await alternative_data.analyze_social_sentiment(ticker)
        
        # 기술적 지표 계산
        technical = calculate_technical_indicators(stock_data.get('price_history', []))
        
        # 뉴스 감성 분석
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
            social_sentiment=alt_data['composite_score'],
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

@app.get("/detail/{ticker}/explained")
async def get_explained_detail(ticker: str):
    """설명 가능한 AI 상세 분석"""
    try:
        # 기본 데이터 수집
        stock_data = await data_pipeline.get_stock_data(ticker)
        
        if not stock_data:
            raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
        
        # 설명 가능한 예측
        explained = await explainable_predictor.predict_with_explanation(stock_data)
        
        return {
            "ticker": ticker,
            "name": stock_data.get('name', ticker),
            "prediction": {
                "probability": explained['probability'],
                "expected_return": explained['expected_return'],
                "confidence": explained['confidence']
            },
            "explanation": explained['explanation'],
            "transparency_score": explained['transparency_score'],
            "feature_contributions": {
                "technical": sum([f['impact'] for f in explained['explanation']['top_positive_factors'] 
                                if f['name'] in ['5일 수익률', '20일 수익률', 'RSI', 'MACD']]),
                "fundamental": sum([f['impact'] for f in explained['explanation']['top_positive_factors'] 
                                  if f['name'] in ['ROE', 'EPS 성장률', '매출 성장률']]),
                "volatility": next((f['impact'] for f in explained['explanation']['top_negative_factors'] 
                                  if f['name'] == '변동성'), 0)
            }
        }
        
    except Exception as e:
        logger.error("explained_detail_error", ticker=ticker, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/personalized/{user_id}")
async def create_user_profile(user_id: str, preferences: UserPreferences):
    """사용자 프로필 생성"""
    try:
        await personalization.create_user_profile(user_id, preferences.dict())
        
        return {
            "user_id": user_id,
            "status": "profile_created",
            "preferences": preferences.dict()
        }
        
    except Exception as e:
        logger.error("create_profile_error", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/personalized/{user_id}/dashboard")
async def get_personalized_dashboard(user_id: str):
    """개인화된 대시보드"""
    try:
        dashboard_config = await personalization.get_personalized_dashboard(user_id)
        
        # 개인화된 데이터 수집
        personalized_data = {}
        
        if 'top_5_stocks' in dashboard_config['widgets']:
            rankings = await get_rankings(user_id=user_id, limit=5)
            personalized_data['top_stocks'] = rankings.top_gainers
        
        if 'sector_rotation' in dashboard_config['widgets']:
            personalized_data['sectors'] = await get_sector_weather()
        
        if 'learning_tips' in dashboard_config['widgets']:
            personalized_data['tips'] = get_learning_tips(dashboard_config.get('experience_level', 'beginner'))
        
        return {
            "user_id": user_id,
            "layout": dashboard_config['layout'],
            "data": personalized_data,
            "updated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error("personalized_dashboard_error", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backtest/results")
async def get_backtest_results(
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01"
):
    """향상된 백테스팅 결과"""
    try:
        results = await backtester.run_comprehensive_backtest(start_date, end_date)
        
        return {
            "period": results['period'],
            "overall_accuracy": results['accuracy_metrics'].get('overall', 0),
            "market_conditions": results['market_condition_analysis'],
            "risk_metrics": results['risk_metrics'],
            "drawdown": results['drawdown_analysis'],
            "key_insights": [
                f"최대 손실률: {results['drawdown_analysis']['max_drawdown']:.2%}",
                f"샤프 비율: {results['risk_metrics']['sharpe_ratio']:.2f}",
                f"95% VaR: {results['risk_metrics']['var_95']:.2%}"
            ]
        }
        
    except Exception as e:
        logger.error("backtest_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sectors")
async def get_sector_weather():
    """섹터별 날씨 지도 (개선된 버전)"""
    logger.info("sector_weather_requested")
    
    try:
        # 섹터별 평균 확률 계산
        sector_data = await data_pipeline.get_sector_aggregates()
        
        sector_weather = []
        for sector, data in sector_data.items():
            # 대체 데이터로 보강
            sector_sentiment = await alternative_data.get_sector_sentiment(sector)
            
            avg_probability = data.get('avg_probability', 0.5)
            combined_score = avg_probability * 0.8 + sector_sentiment * 0.2
            
            weather = SectorWeather(
                sector=sector,
                probability=combined_score,
                weather_icon=get_weather_icon(combined_score),
                weather_desc=get_weather_description(combined_score),
                stock_count=data.get('count', 0),
                top_stock=data.get('top_stock', ''),
                trend_strength=calculate_trend_strength(data)
            )
            sector_weather.append(weather)
        
        result = {
            "sectors": sorted(sector_weather, key=lambda x: x.probability, reverse=True),
            "market_overview": calculate_market_overview(sector_weather),
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info("sector_weather_generated", sector_count=len(sector_weather))
        return result
        
    except Exception as e:
        logger.error("sector_weather_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """서버 상태 확인 (확장된 버전)"""
    try:
        # 각 컴포넌트 상태 확인
        checks = {
            "cache": await cache.health_check() if cache else False,
            "models": predictor.is_loaded if predictor else False,
            "data_pipeline": data_pipeline is not None,
            "explainable_ai": explainable_predictor is not None,
            "personalization": personalization is not None,
            "alternative_data": alternative_data is not None
        }
        
        # 성능 메트릭
        cache_stats = await cache.get_stats() if cache else {}
        
        all_healthy = all(checks.values())
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "metrics": {
                "cache_hit_rate": cache_stats.get('hit_rate', 0),
                "total_predictions": cache_stats.get('total_entries', 0),
                "uptime": get_uptime()
            },
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
    
    return False

async def get_stock_predictions(market: Market) -> List[Dict]:
    """주식 예측 데이터 생성 (개선된 버전)"""
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

def get_accessibility_label(stock: Dict) -> str:
    """접근성을 위한 텍스트 레이블 생성"""
    return (
        f"{stock['name']} 종목, "
        f"상승 확률 {int(stock['probability'] * 100)}퍼센트, "
        f"예상 수익률 {'플러스' if stock['expected_return'] > 0 else '마이너스'} "
        f"{abs(stock['expected_return']):.1f}퍼센트, "
        f"신뢰도 {int(stock['confidence'] * 100)}퍼센트"
    )

def filter_by_risk_tolerance(stocks: List[Dict], risk_tolerance: str) -> List[Dict]:
    """리스크 수준별 필터링"""
    if risk_tolerance == 'conservative':
        # 보수적: 변동성 낮은 종목
        return [s for s in stocks if s.get('volatility', 0) < 0.15 and s['confidence'] > 0.7]
    elif risk_tolerance == 'aggressive':
        # 공격적: 높은 수익률 기대
        return [s for s in stocks if abs(s['expected_return']) > 5]
    else:  # moderate
        return stocks

def calculate_technical_indicators(price_history: List[Dict]) -> Dict[str, float]:
    """기술적 지표 계산 (개선된 버전)"""
    if len(price_history) < 20:
        return {
            "ma20": 0,
            "ma60": 0,
            "rsi": 50,
            "volatility": 0,
            "bollinger_upper": 0,
            "bollinger_lower": 0,
            "macd": 0,
            "signal": 0
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
        
        # 볼린저 밴드
        std20 = np.std(closes[-20:])
        bollinger_upper = ma20 + (2 * std20)
        bollinger_lower = ma20 - (2 * std20)
        
        # MACD
        macd, signal = calculate_macd(closes)
        
        return {
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "rsi": round(rsi, 2),
            "volatility": round(volatility, 2),
            "bollinger_upper": round(bollinger_upper, 2),
            "bollinger_lower": round(bollinger_lower, 2),
            "macd": round(macd, 2),
            "signal": round(signal, 2)
        }
    except Exception as e:
        logger.error("technical_indicators_error", error=str(e))
        return {
            "ma20": 0,
            "ma60": 0,
            "rsi": 50,
            "volatility": 0,
            "bollinger_upper": 0,
            "bollinger_lower": 0,
            "macd": 0,
            "signal": 0
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

def calculate_macd(prices: List[float]) -> Tuple[float, float]:
    """MACD 계산"""
    if len(prices) < 26:
        return 0.0, 0.0
    
    # EMA 계산
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    
    macd = ema12 - ema26
    signal = calculate_ema([macd], 9)  # 신호선
    
    return macd, signal

def calculate_ema(prices: List[float], period: int) -> float:
    """지수이동평균 계산"""
    if len(prices) < period:
        return prices[-1] if prices else 0
    
    multiplier = 2 / (period + 1)
    ema = prices[-period]
    
    for price in prices[-period+1:]:
        ema = (price - ema) * multiplier + ema
    
    return ema

async def analyze_news_sentiment(ticker: str) -> float:
    """뉴스 감성 분석 (한국 주식만)"""
    # 실제 구현 시 news_analyzer.py 모듈 사용
    # 여기서는 무료 소스 활용
    try:
        # Google News RSS 활용
        import feedparser
        feed_url = f"https://news.google.com/rss/search?q={ticker}+주가&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(feed_url)
        
        if feed.entries:
            # 간단한 감성 분석
            positive_keywords = ['상승', '호재', '신고가', '매수', '긍정적']
            negative_keywords = ['하락', '악재', '신저가', '매도', '부정적']
            
            sentiment_scores = []
            for entry in feed.entries[:10]:
                title = entry.title
                positive_count = sum(1 for word in positive_keywords if word in title)
                negative_count = sum(1 for word in negative_keywords if word in title)
                
                if positive_count > negative_count:
                    sentiment_scores.append(1)
                elif negative_count > positive_count:
                    sentiment_scores.append(-1)
                else:
                    sentiment_scores.append(0)
            
            return sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    except:
        return 0

def calculate_trend_strength(sector_data: Dict) -> float:
    """섹터 트렌드 강도 계산"""
    probabilities = sector_data.get('probabilities', [])
    if not probabilities:
        return 0.5
    
    # 확률의 표준편차가 낮으면 강한 트렌드
    import numpy as np
    std_dev = np.std(probabilities)
    avg_prob = np.mean(probabilities)
    
    # 트렌드 강도: 평균이 극단값에 가깝고 편차가 낮을수록 강함
    trend_strength = abs(avg_prob - 0.5) * 2 * (1 - std_dev)
    return min(1.0, max(0.0, trend_strength))

def calculate_market_overview(sectors: List[SectorWeather]) -> Dict:
    """전체 시장 개요 계산"""
    if not sectors:
        return {"status": "unknown", "temperature": 50}
    
    avg_probability = sum(s.probability for s in sectors) / len(sectors)
    
    # 시장 온도 (0-100)
    temperature = int(avg_probability * 100)
    
    # 시장 상태
    if temperature >= 70:
        status = "overheated"
        description = "과열 주의 - 조정 가능성"
    elif temperature >= 60:
        status = "bullish"
        description = "강세 시장 - 상승 우세"
    elif temperature >= 40:
        status = "neutral"
        description = "중립 시장 - 관망세"
    elif temperature >= 30:
        status = "bearish"
        description = "약세 시장 - 하락 우세"
    else:
        status = "oversold"
        description = "과매도 - 반등 가능성"
    
    return {
        "status": status,
        "temperature": temperature,
        "description": description,
        "strongest_sectors": [s.sector for s in sorted(sectors, key=lambda x: x.probability, reverse=True)[:3]],
        "weakest_sectors": [s.sector for s in sorted(sectors, key=lambda x: x.probability)[:3]]
    }

def get_learning_tips(experience_level: str) -> List[Dict]:
    """경험 수준별 학습 팁"""
    tips = {
        'beginner': [
            {
                "title": "날씨 아이콘의 의미",
                "content": "☀️는 상승 가능성이 높음을, 🌧️는 하락 가능성을 의미합니다.",
                "icon": "💡"
            },
            {
                "title": "펀더멘털 점수란?",
                "content": "기업의 재무 건전성을 나타내는 지표입니다. 높을수록 좋습니다.",
                "icon": "📊"
            },
            {
                "title": "분산 투자의 중요성",
                "content": "한 종목에 모든 자금을 투자하지 마세요. 여러 종목에 나누어 투자하세요.",
                "icon": "🎯"
            }
        ],
        'intermediate': [
            {
                "title": "RSI 지표 활용",
                "content": "RSI가 30 이하면 과매도, 70 이상이면 과매수 상태입니다.",
                "icon": "📈"
            },
            {
                "title": "섹터 로테이션",
                "content": "경기 사이클에 따라 유망 섹터가 바뀝니다. 섹터별 날씨를 확인하세요.",
                "icon": "🔄"
            }
        ],
        'advanced': [
            {
                "title": "AI 예측의 한계",
                "content": "AI 예측은 과거 데이터 기반입니다. 예상치 못한 이벤트는 반영되지 않습니다.",
                "icon": "🤖"
            },
            {
                "title": "리스크 조정 수익률",
                "content": "단순 수익률보다 샤프 비율 등 리스크 조정 지표를 확인하세요.",
                "icon": "⚖️"
            }
        ]
    }
    
    return tips.get(experience_level, tips['beginner'])

def get_uptime() -> str:
    """서버 가동 시간"""
    # 실제 구현 시 서버 시작 시간 추적
    return "24h 35m 12s"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
