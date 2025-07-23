from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
import logging

from market_analyzer import MarketWideAnalyzer, KoreaStockUniverse

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="전체 주식 시장 분석 API",
    description="KOSPI/KOSDAQ 전 종목 + 섹터별 분석",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 분석기 인스턴스
market_analyzer = MarketWideAnalyzer()
stock_universe = KoreaStockUniverse()

# 캐시 (간단한 메모리 캐시)
cache = {
    'market_analysis': None,
    'last_update': None,
    'sector_data': {}
}

# 데이터 모델
class MarketAnalysisResponse(BaseModel):
    timestamp: str
    total_stocks_analyzed: int
    market_summary: Dict
    sector_analysis: Dict
    top_recommendations: List[Dict]
    stocks_to_avoid: List[Dict]
    cache_info: Dict

class SectorAnalysisRequest(BaseModel):
    sectors: List[str]
    top_n: int = 10

class StockSearchRequest(BaseModel):
    keyword: str
    limit: int = 20

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 종목 데이터 로드"""
    logger.info("종목 데이터 로드 시작...")
    await stock_universe.load_all_stocks()
    logger.info(f"종목 로드 완료: {len(stock_universe.get_all_stocks())}개")

@app.get("/")
async def root():
    return {
        "message": "전체 주식 시장 분석 API",
        "total_stocks": len(stock_universe.get_all_stocks()),
        "endpoints": {
            "/api/analyze/full": "전체 시장 분석 (시간 소요)",
            "/api/analyze/sectors": "특정 섹터 분석",
            "/api/stocks/search": "종목 검색",
            "/api/stocks/list": "전체 종목 리스트",
            "/api/market/summary": "시장 요약 (캐시)"
        }
    }

@app.post("/api/analyze/full")
async def analyze_full_market(background_tasks: BackgroundTasks):
    """전체 시장 분석 (2-3분 소요)"""
    try:
        # 최근 분석이 있으면 캐시 반환
        if cache['last_update']:
            time_diff = (datetime.now() - cache['last_update']).total_seconds()
            if time_diff < 600:  # 10분 이내
                return {
                    **cache['market_analysis'],
                    'cache_info': {
                        'cached': True,
                        'age_seconds': int(time_diff),
                        'next_update_in': int(600 - time_diff)
                    }
                }
        
        # 백그라운드에서 분석 시작
        if not cache.get('analysis_in_progress'):
            background_tasks.add_task(run_market_analysis)
            cache['analysis_in_progress'] = True
            
            return {
                'status': 'analysis_started',
                'message': '전체 시장 분석이 시작되었습니다. 2-3분 후 다시 요청해주세요.',
                'check_url': '/api/market/status'
            }
        else:
            return {
                'status': 'analysis_in_progress',
                'message': '이미 분석이 진행 중입니다. 잠시 후 다시 시도해주세요.'
            }
            
    except Exception as e:
        logger.error(f"전체 시장 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/status")
async def get_analysis_status():
    """분석 진행 상태 확인"""
    if cache.get('analysis_in_progress'):
        return {
            'status': 'in_progress',
            'message': '분석이 진행 중입니다...'
        }
    elif cache.get('market_analysis'):
        return {
            'status': 'completed',
            'last_update': cache['last_update'].isoformat() if cache['last_update'] else None,
            'result_available': True
        }
    else:
        return {
            'status': 'idle',
            'message': '분석이 시작되지 않았습니다.'
        }

@app.get("/api/market/summary")
async def get_market_summary():
    """캐시된 시장 요약 데이터"""
    if not cache.get('market_analysis'):
        # 간단한 요약만 즉시 생성
        all_stocks = stock_universe.get_all_stocks()
        sectors = stock_universe.get_sector_list()
        
        return {
            'status': 'basic_summary',
            'total_stocks': len(all_stocks),
            'markets': {
                'KOSPI': len([s for s in all_stocks.values() if s['market'] == 'KOSPI']),
                'KOSDAQ': len([s for s in all_stocks.values() if s['market'] == 'KOSDAQ'])
            },
            'sectors': sectors,
            'message': '상세 분석을 위해 /api/analyze/full 엔드포인트를 사용하세요.'
        }
    
    return cache['market_analysis']

@app.post("/api/analyze/sectors")
async def analyze_specific_sectors(request: SectorAnalysisRequest):
    """특정 섹터만 빠르게 분석"""
    try:
        results = {}
        
        for sector in request.sectors:
            # 해당 섹터 종목들
            sector_stocks = stock_universe.get_stocks_by_sector(sector)
            
            if not sector_stocks:
                results[sector] = {
                    'error': '해당 섹터를 찾을 수 없습니다.',
                    'available_sectors': stock_universe.get_sector_list()
                }
                continue
            
            # 간단한 분석 (실제로는 뉴스 수집 등 추가)
            top_stocks = sorted(
                sector_stocks,
                key=lambda x: hash(x['name']) % 100,  # 더미 점수
                reverse=True
            )[:request.top_n]
            
            results[sector] = {
                'total_stocks': len(sector_stocks),
                'top_stocks': [
                    {
                        'code': stock['code'],
                        'name': stock['name'],
                        'market': stock['market'],
                        'score': (hash(stock['name']) % 100) / 100  # 0-1 사이 더미 점수
                    }
                    for stock in top_stocks
                ],
                'sector_trend': 'neutral',  # 실제로는 뉴스 분석 필요
                'recommendation': '섹터 전반적으로 중립적입니다.'
            }
        
        return {
            'sectors_analyzed': request.sectors,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"섹터 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stocks/search")
async def search_stocks(request: StockSearchRequest):
    """종목 검색"""
    try:
        all_stocks = stock_universe.get_all_stocks()
        keyword = request.keyword.lower()
        
        # 이름 또는 코드로 검색
        matched_stocks = []
        for code, stock in all_stocks.items():
            if keyword in stock['name'].lower() or keyword in code:
                matched_stocks.append({
                    'code': code,
                    'name': stock['name'],
                    'market': stock['market'],
                    'sector': stock['sector']
                })
        
        # 정렬 (정확도 순)
        matched_stocks.sort(key=lambda x: (
            x['name'].lower().startswith(keyword),
            keyword in x['name'].lower(),
            keyword in x['code']
        ), reverse=True)
        
        return {
            'keyword': request.keyword,
            'total_found': len(matched_stocks),
            'results': matched_stocks[:request.limit]
        }
        
    except Exception as e:
        logger.error(f"종목 검색 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/list")
async def get_all_stocks(market: Optional[str] = None, sector: Optional[str] = None):
    """전체 종목 리스트"""
    try:
        all_stocks = stock_universe.get_all_stocks()
        
        # 필터링
        filtered_stocks = []
        for code, stock in all_stocks.items():
            if market and stock['market'] != market:
                continue
            if sector and stock['sector'] != sector:
                continue
                
            filtered_stocks.append({
                'code': code,
                'name': stock['name'],
                'market': stock['market'],
                'sector': stock['sector']
            })
        
        # 이름순 정렬
        filtered_stocks.sort(key=lambda x: x['name'])
        
        return {
            'total': len(filtered_stocks),
            'filters': {
                'market': market,
                'sector': sector
            },
            'stocks': filtered_stocks
        }
        
    except Exception as e:
        logger.error(f"종목 리스트 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sectors/list")
async def get_all_sectors():
    """전체 섹터 리스트"""
    sectors = stock_universe.get_sector_list()
    
    sector_details = []
    all_stocks = stock_universe.get_all_stocks()
    
    for sector in sectors:
        stocks_in_sector = [s for s in all_stocks.values() if s['sector'] == sector]
        sector_details.append({
            'name': sector,
            'stock_count': len(stocks_in_sector),
            'markets': {
                'KOSPI': len([s for s in stocks_in_sector if s['market'] == 'KOSPI']),
                'KOSDAQ': len([s for s in stocks_in_sector if s['market'] == 'KOSDAQ'])
            }
        })
    
    # 종목 수 많은 순으로 정렬
    sector_details.sort(key=lambda x: x['stock_count'], reverse=True)
    
    return {
        'total_sectors': len(sectors),
        'sectors': sector_details
    }

@app.get("/api/stocks/{stock_code}")
async def get_stock_detail(stock_code: str):
    """개별 종목 상세 정보"""
    all_stocks = stock_universe.get_all_stocks()
    
    if stock_code not in all_stocks:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    
    stock = all_stocks[stock_code]
    
    # 같은 섹터 다른 종목들
    same_sector_stocks = [
        {'code': code, 'name': s['name']}
        for code, s in all_stocks.items()
        if s['sector'] == stock['sector'] and code != stock_code
    ][:5]
    
    return {
        'code': stock_code,
        'name': stock['name'],
        'market': stock['market'],
        'sector': stock['sector'],
        'same_sector_stocks': same_sector_stocks,
        'analysis': {
            'score': 0.5,  # 더미 데이터
            'recommendation': 'HOLD',
            'last_update': datetime.now().isoformat()
        }
    }

# 백그라운드 작업
async def run_market_analysis():
    """백그라운드에서 전체 시장 분석 실행"""
    try:
        logger.info("전체 시장 분석 시작...")
        
        # 실제 분석 실행
        result = await market_analyzer.analyze_entire_market()
        
        # 캐시 업데이트
        cache['market_analysis'] = result
        cache['last_update'] = datetime.now()
        cache['analysis_in_progress'] = False
        
        logger.info("전체 시장 분석 완료!")
        
    except Exception as e:
        logger.error(f"시장 분석 실패: {e}")
        cache['analysis_in_progress'] = False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)