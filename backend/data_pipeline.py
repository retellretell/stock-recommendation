"""
데이터 수집 파이프라인 (개선된 버전)
"""
import asyncio
import aiohttp
from asyncio import Semaphore
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from bs4 import BeautifulSoup

from config import settings
from cache_manager import CacheManager
from api_clients import KRXClient, DARTClient
from exceptions import BatchProcessingError, APIError
from models import Market, StockData

logger = structlog.get_logger()

class DataPipeline:
    """데이터 수집 및 처리 파이프라인"""
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self.krx_client = KRXClient()
        self.dart_client = DARTClient()
        self.batch_size = settings.batch_size
        self.rate_limit_delay = settings.rate_limit_delay
        self.semaphore = Semaphore(settings.max_concurrent_requests)
        
    async def get_kr_tickers(self) -> List[str]:
        """한국 주식 티커 목록"""
        cache_key = self.cache.generate_cache_key("kr_tickers", "tickers")
        cached = await self.cache.get(cache_key)
        
        if cached:
            logger.info("kr_tickers_from_cache", count=len(cached))
            return cached
        
        try:
            # KRX에서 전체 종목 코드 가져오기
            tickers = await self.krx_client.get_all_tickers()
            
            # 캐시 저장 (24시간)
            await self.cache.set(cache_key, tickers, ttl=86400)
            
            logger.info("kr_tickers_loaded", count=len(tickers))
            return tickers
            
        except Exception as e:
            logger.error("kr_tickers_load_failed", error=str(e))
            # 대표 종목 반환 (fallback)
            return ['005930', '000660', '035420', '051910', '006400']
    
    async def get_us_tickers(self) -> List[str]:
        """미국 주식 티커 목록 (S&P 500)"""
        cache_key = self.cache.generate_cache_key("us_tickers", "tickers")
        cached = await self.cache.get(cache_key)
        
        if cached:
            logger.info("us_tickers_from_cache", count=len(cached))
            return cached
        
        # S&P 500 구성 종목
        sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sp500_url) as response:
                    html = await response.text()
                    
            # pandas로 테이블 파싱
            tables = pd.read_html(html)
            sp500_df = tables[0]
            tickers = sp500_df['Symbol'].tolist()
            
            # 캐시 저장
            await self.cache.set(cache_key, tickers, ttl=86400)
            
            logger.info("us_tickers_loaded", count=len(tickers))
            return tickers
            
        except Exception as e:
            logger.error("us_tickers_load_failed", error=str(e))
            # 대표 종목만 반환
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V']
    
    async def fetch_batch_data(self, tickers: List[str], market: Market = Market.US) -> Dict[str, Dict]:
        """배치 데이터 수집 (개선된 동시성 제어)"""
        logger.info("batch_fetch_started", tickers_count=len(tickers), market=market, batch_size=self.batch_size)
        
        start_time = datetime.now()
        results = {}
        errors = []
        
        async def fetch_with_limit(batch: List[str]) -> Tuple[Dict, List]:
            """세마포어를 사용한 동시성 제한"""
            async with self.semaphore:
                if market == Market.KR:
                    return await self._fetch_kr_batch(batch)
                else:
                    return await self._fetch_us_batch(batch)
        
        # 배치 단위로 비동기 처리
        tasks = []
        for i in range(0, len(tickers), self.batch_size):
            batch = tickers[i:i+self.batch_size]
            tasks.append(fetch_with_limit(batch))
        
        # 모든 배치 처리 대기
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 병합 및 에러 수집
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                errors.append({"error": "batch_failed", "message": str(batch_result)})
            else:
                batch_data, batch_errors = batch_result
                results.update(batch_data)
                errors.extend(batch_errors)
        
        # 성능 메트릭 로깅
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            "batch_fetch_completed",
            duration=duration,
            success_count=len(results),
            failure_count=len(errors),
            error_rate=len(errors) / len(tickers) if tickers else 0
        )
        
        # 오류 임계값 체크
        if len(errors) > len(tickers) * 0.5:  # 50% 이상 실패시
            raise BatchProcessingError(f"배치 처리 실패: {len(errors)}/{len(tickers)} 실패")
        
        return results
    
    async def _fetch_kr_batch(self, tickers: List[str]) -> Tuple[Dict[str, Dict], List[Dict]]:
        """한국 주식 배치 데이터 수집"""
        results = {}
        errors = []
        
        for ticker in tickers:
            try:
                # 캐시 확인
                cache_key = self.cache.generate_cache_key(ticker, f"kr_stock")
                cached = await self.cache.get(cache_key)
                
                if cached and not self._needs_update(cached):
                    results[ticker] = cached
                    continue
                
                # KRX 가격 데이터
                price_data = await self.krx_client.get_price_data(ticker)
                
                # DART 재무 데이터
                financial_data = await self.dart_client.get_financial_data(ticker)
                
                # 데이터 병합 및 검증
                stock_data = self._merge_and_validate_stock_data(ticker, price_data, financial_data)
                
                # 캐시 저장
                await self.cache.set(cache_key, stock_data, ttl=settings.cache_ttl)
                
                results[ticker] = stock_data
                
            except aiohttp.ClientError as e:
                logger.error("network_error", ticker=ticker, error=str(e))
                errors.append({"ticker": ticker, "error": "network", "message": str(e)})
            except ValueError as e:
                logger.error("data_validation_error", ticker=ticker, error=str(e))
                errors.append({"ticker": ticker, "error": "validation", "message": str(e)})
            except Exception as e:
                logger.error("unexpected_error", ticker=ticker, error=str(e))
                errors.append({"ticker": ticker, "error": "unknown", "message": str(e)})
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
        
        return results, errors
    
    async def _fetch_us_batch(self, tickers: List[str]) -> Tuple[Dict[str, Dict], List[Dict]]:
        """미국 주식 배치 데이터 수집 (yfinance)"""
        results = {}
        errors = []
        
        try:
            # yfinance 배치 다운로드
            batch_str = ' '.join(tickers)
            data = yf.download(
                batch_str, 
                period='6mo', 
                interval='1d', 
                group_by='ticker', 
                progress=False,
                threads=False
            )
            
            for ticker in tickers:
                try:
                    # 캐시 확인
                    cache_key = self.cache.generate_cache_key(ticker, "us_stock")
                    cached = await self.cache.get(cache_key)
                    
                    if cached and not self._needs_update(cached):
                        results[ticker] = cached
                        continue
                    
                    # 데이터 추출
                    if len(tickers) > 1:
                        ticker_data = data[ticker] if ticker in data else None
                    else:
                        ticker_data = data
                    
                    if ticker_data is None or ticker_data.empty:
                        errors.append({"ticker": ticker, "error": "no_data", "message": "No data available"})
                        continue
                    
                    # 주식 정보
                    info = yf.Ticker(ticker).info
                    
                    # 데이터 포맷팅 및 검증
                    stock_data = self._format_yfinance_data(ticker, ticker_data, info)
                    
                    # 캐시 저장
                    await self.cache.set(cache_key, stock_data, ttl=settings.cache_ttl)
                    
                    results[ticker] = stock_data
                    
                except Exception as e:
                    logger.error("us_stock_processing_error", ticker=ticker, error=str(e))
                    errors.append({"ticker": ticker, "error": "processing", "message": str(e)})
                    
        except Exception as e:
            logger.error("yfinance_batch_download_failed", error=str(e))
            for ticker in tickers:
                errors.append({"ticker": ticker, "error": "batch_download", "message": str(e)})
        
        return results, errors
    
    async def get_stock_data(self, ticker: str) -> Optional[Dict]:
        """개별 종목 데이터 조회"""
        # 시장 구분
        market = Market.KR if ticker.endswith('.KS') or ticker.endswith('.KQ') else Market.US
        
        # 캐시 확인
        cache_key = self.cache.generate_cache_key(ticker, f"{market.lower()}_stock")
        cached = await self.cache.get(cache_key)
        
        if cached and not self._needs_update(cached):
            return cached
        
        # 새 데이터 수집
        try:
            data = await self.fetch_batch_data([ticker], market)
            return data.get(ticker)
        except Exception as e:
            logger.error("get_stock_data_error", ticker=ticker, error=str(e))
            return None
    
    async def get_sector_aggregates(self) -> Dict[str, Dict]:
        """섹터별 집계 데이터"""
        # 모든 캐시된 주식 데이터 가져오기
        all_stocks = await self.cache.get_pattern("*_stock_*")
        
        sector_data = {}
        
        for key, stock in all_stocks.items():
            if not isinstance(stock, dict):
                continue
                
            sector = stock.get('sector', 'Unknown')
            
            if sector not in sector_data:
                sector_data[sector] = {
                    'stocks': [],
                    'total_probability': 0,
                    'count': 0,
                    'probabilities': []
                }
            
            # 예측 확률이 있다면 추가
            probability = stock.get('probability', 0.5)
            
            sector_data[sector]['stocks'].append(stock.get('ticker', ''))
            sector_data[sector]['total_probability'] += probability
            sector_data[sector]['count'] += 1
            sector_data[sector]['probabilities'].append(probability)
        
        # 평균 계산 및 대표 종목 선정
        for sector, data in sector_data.items():
            if data['count'] > 0:
                data['avg_probability'] = data['total_probability'] / data['count']
                # 확률이 가장 높은 종목을 대표로
                if data['probabilities']:
                    max_prob_idx = data['probabilities'].index(max(data['probabilities']))
                    data['top_stock'] = data['stocks'][max_prob_idx] if max_prob_idx < len(data['stocks']) else data['stocks'][0]
                else:
                    data['top_stock'] = data['stocks'][0] if data['stocks'] else ''
        
        return sector_data
    
    def _needs_update(self, cached_data: Dict) -> bool:
        """캐시 업데이트 필요 여부"""
        if 'last_updated' not in cached_data:
            return True
        
        # 최종 업데이트 시간 확인
        if isinstance(cached_data['last_updated'], str):
            last_updated = datetime.fromisoformat(cached_data['last_updated'])
        else:
            last_updated = cached_data['last_updated']
            
        age = (datetime.now() - last_updated).seconds
        
        # 1시간 이내면 그대로 사용
        if age < settings.cache_freshness:
            return False
        
        # 3시간 초과면 무조건 업데이트
        if age > settings.cache_ttl:
            return True
        
        # TODO: ±5% 변동 체크 로직 구현
        
        return False
    
    def _merge_and_validate_stock_data(self, ticker: str, price_data: Dict, financial_data: Dict) -> Dict:
        """가격 데이터와 재무 데이터 병합 및 검증"""
        # 기본 구조
        stock_data = {
            'ticker': ticker,
            'name': financial_data.get('name', ticker),
            'sector': financial_data.get('sector', 'Unknown'),
            'current_price': price_data.get('close', 0),
            'price_history': price_data.get('history', []),
            'last_updated': datetime.now().isoformat()
        }
        
        # 재무 데이터 검증 및 추가
        financial_fields = ['market_cap', 'pe_ratio', 'eps', 'eps_yoy', 'revenue', 'revenue_yoy', 'roe']
        for field in financial_fields:
            value = financial_data.get(field)
            if value is not None:
                # 이상치 검증
                if field == 'pe_ratio' and not -1000 <= value <= 1000:
                    value = None
                elif field.endswith('_yoy') and not -500 <= value <= 500:
                    value = None
                elif field == 'roe' and not -100 <= value <= 100:
                    value = None
            stock_data[field] = value
        
        # 데이터 검증
        if stock_data['current_price'] <= 0:
            raise ValueError(f"Invalid price for {ticker}: {stock_data['current_price']}")
        
        return stock_data
    
    def _format_yfinance_data(self, ticker: str, ticker_data: pd.DataFrame, info: Dict) -> Dict:
        """yfinance 데이터 포맷팅"""
        # 가격 히스토리 변환
        price_history = []
        for date, row in ticker_data.iterrows():
            price_history.append({
                'date': date.isoformat(),
                'open': float(row['Open']) if pd.notna(row['Open']) else 0,
                'high': float(row['High']) if pd.notna(row['High']) else 0,
                'low': float(row['Low']) if pd.notna(row['Low']) else 0,
                'close': float(row['Close']) if pd.notna(row['Close']) else 0,
                'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0
            })
        
        # 전년 대비 성장률 계산
        current_eps = info.get('trailingEps', 0)
        forward_eps = info.get('forwardEps', current_eps)
        eps_yoy = ((forward_eps - current_eps) / abs(current_eps) * 100) if current_eps != 0 else 0
        
        stock_data = {
            'ticker': ticker,
            'name': info.get('longName', ticker),
            'sector': info.get('sector', 'Unknown'),
            'current_price': float(ticker_data['Close'].iloc[-1]) if not ticker_data.empty else 0,
            'price_history': price_history,
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'eps': current_eps,
            'eps_yoy': eps_yoy,
            'revenue': info.get('totalRevenue'),
            'revenue_yoy': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else None,
            'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else None,
            'last_updated': datetime.now().isoformat()
        }
        
        return stock_data
