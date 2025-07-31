"""
데이터 수집 파이프라인
"""
import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

from cache_manager import CacheManager
from api_clients import KRXClient, DARTClient

load_dotenv()
logger = logging.getLogger(__name__)

class DataPipeline:
    """데이터 수집 및 처리 파이프라인"""
    
    def __init__(self):
        self.cache = CacheManager()
        self.krx_client = KRXClient()
        self.dart_client = DARTClient()
        self.batch_size = 100
        self.rate_limit_delay = 1.0  # 초
        
    async def get_kr_tickers(self) -> List[str]:
        """한국 주식 티커 목록"""
        # 캐시 확인
        cached = await self.cache.get("kr_tickers")
        if cached:
            return cached
        
        # KRX에서 전체 종목 코드 가져오기
        tickers = await self.krx_client.get_all_tickers()
        
        # 캐시 저장 (24시간)
        await self.cache.set("kr_tickers", tickers, ttl=86400)
        
        return tickers
    
    async def get_us_tickers(self) -> List[str]:
        """미국 주식 티커 목록 (S&P 500)"""
        cached = await self.cache.get("us_tickers")
        if cached:
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
            await self.cache.set("us_tickers", tickers, ttl=86400)
            
            return tickers
            
        except Exception as e:
            logger.error(f"S&P 500 티커 로드 실패: {e}")
            # 대표 종목만 반환
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'JNJ', 'V']
    
    async def fetch_batch_data(self, tickers: List[str], market: str = 'US') -> Dict[str, Dict]:
        """배치 데이터 수집"""
        results = {}
        
        # 배치 단위로 처리
        for i in range(0, len(tickers), self.batch_size):
            batch = tickers[i:i+self.batch_size]
            
            if market == 'KR':
                batch_data = await self._fetch_kr_batch(batch)
            else:
                batch_data = await self._fetch_us_batch(batch)
            
            results.update(batch_data)
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
        
        return results
    
    async def _fetch_kr_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """한국 주식 배치 데이터 수집"""
        results = {}
        
        for ticker in tickers:
            try:
                # 캐시 확인
                cache_key = f"kr_stock_{ticker}"
                cached = await self.cache.get(cache_key)
                
                if cached and not self._needs_update(cached):
                    results[ticker] = cached
                    continue
                
                # KRX 가격 데이터
                price_data = await self.krx_client.get_price_data(ticker)
                
                # DART 재무 데이터
                financial_data = await self.dart_client.get_financial_data(ticker)
                
                # 데이터 병합
                stock_data = self._merge_stock_data(ticker, price_data, financial_data)
                
                # 캐시 저장
                await self.cache.set(cache_key, stock_data, ttl=10800)  # 3시간
                
                results[ticker] = stock_data
                
            except Exception as e:
                logger.error(f"KR 주식 데이터 수집 실패 {ticker}: {e}")
                
        return results
    
    async def _fetch_us_batch(self, tickers: List[str]) -> Dict[str, Dict]:
        """미국 주식 배치 데이터 수집 (yfinance)"""
        results = {}
        
        try:
            # yfinance 배치 다운로드
            batch_str = ' '.join(tickers)
            data = yf.download(batch_str, period='6mo', interval='1d', group_by='ticker', progress=False)
            
            for ticker in tickers:
                try:
                    if ticker in data:
                        ticker_data = data[ticker] if len(tickers) > 1 else data
                        
                        # 주식 정보
                        info = yf.Ticker(ticker).info
                        
                        # 데이터 포맷팅
                        price_history = []
                        for date, row in ticker_data.iterrows():
                            price_history.append({
                                'date': date.isoformat(),
                                'open': float(row['Open']),
                                'high': float(row['High']),
                                'low': float(row['Low']),
                                'close': float(row['Close']),
                                'volume': int(row['Volume'])
                            })
                        
                        stock_data = {
                            'ticker': ticker,
                            'name': info.get('longName', ticker),
                            'sector': info.get('sector', 'Unknown'),
                            'current_price': float(ticker_data['Close'].iloc[-1]),
                            'price_history': price_history,
                            'market_cap': info.get('marketCap', 0),
                            'pe_ratio': info.get('trailingPE', 0),
                            'eps': info.get('trailingEps', 0),
                            'revenue': info.get('totalRevenue', 0),
                            'roe': info.get('returnOnEquity', 0),
                            'last_updated': datetime.now().isoformat()
                        }
                        
                        # 캐시 저장
                        cache_key = f"us_stock_{ticker}"
                        await self.cache.set(cache_key, stock_data, ttl=10800)
                        
                        results[ticker] = stock_data
                        
                except Exception as e:
                    logger.error(f"US 개별 주식 처리 실패 {ticker}: {e}")
                    
        except Exception as e:
            logger.error(f"US 배치 다운로드 실패: {e}")
            
        return results
    
    async def get_stock_data(self, ticker: str) -> Optional[Dict]:
        """개별 종목 데이터 조회"""
        # 시장 구분
        market = 'KR' if ticker.endswith('.KS') or ticker.endswith('.KQ') else 'US'
        
        # 캐시 확인
        cache_key = f"{market.lower()}_stock_{ticker}"
        cached = await self.cache.get(cache_key)
        
        if cached and not self._needs_update(cached):
            return cached
        
        # 새 데이터 수집
        if market == 'KR':
            data = await self._fetch_kr_batch([ticker])
        else:
            data = await self._fetch_us_batch([ticker])
        
        return data.get(ticker)
    
    async def get_sector_aggregates(self) -> Dict[str, Dict]:
        """섹터별 집계 데이터"""
        # 모든 캐시된 주식 데이터 가져오기
        all_stocks = await self.cache.get_pattern("*_stock_*")
        
        sector_data = {}
        
        for stock in all_stocks.values():
            sector = stock.get('sector', 'Unknown')
            
            if sector not in sector_data:
                sector_data[sector] = {
                    'stocks': [],
                    'total_probability': 0,
                    'count': 0
                }
            
            # 예측 확률이 있다면 추가 (실제로는 predictor에서 계산)
            probability = stock.get('probability', 0.5)
            
            sector_data[sector]['stocks'].append(stock['ticker'])
            sector_data[sector]['total_probability'] += probability
            sector_data[sector]['count'] += 1
        
        # 평균 계산
        for sector, data in sector_data.items():
            if data['count'] > 0:
                data['avg_probability'] = data['total_probability'] / data['count']
                data['top_stock'] = data['stocks'][0]  # 실제로는 더 정교한 로직 필요
        
        return sector_data
    
    def _needs_update(self, cached_data: Dict) -> bool:
        """캐시 업데이트 필요 여부"""
        if 'last_updated' not in cached_data:
            return True
        
        # 최종 업데이트 시간 확인
        last_updated = datetime.fromisoformat(cached_data['last_updated'])
        age = (datetime.now() - last_updated).seconds
        
        # 1시간 이내면 그대로 사용
        if age < 3600:
            return False
        
        # 3시간 초과면 무조건 업데이트
        if age > 10800:
            return True
        
        # ±5% 변동 체크 로직 (추가 구현 필요)
        # TODO: 실시간 가격과 비교
        
        return False
    
    def _merge_stock_data(self, ticker: str, price_data: Dict, financial_data: Dict) -> Dict:
        """가격 데이터와 재무 데이터 병합"""
        return {
            'ticker': ticker,
            'name': financial_data.get('name', ticker),
            'sector': financial_data.get('sector', 'Unknown'),
            'current_price': price_data.get('close', 0),
            'price_history': price_data.get('history', []),
            'market_cap': financial_data.get('market_cap', 0),
            'pe_ratio': financial_data.get('pe_ratio', 0),
            'eps': financial_data.get('eps', 0),
            'eps_yoy': financial_data.get('eps_yoy', 0),
            'revenue': financial_data.get('revenue', 0),
            'revenue_yoy': financial_data.get('revenue_yoy', 0),
            'roe': financial_data.get('roe', 0),
            'last_updated': datetime.now().isoformat()
        }
