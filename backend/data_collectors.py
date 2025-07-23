"""
무료로 사용 가능한 데이터 수집 방법들
"""

import requests
import yfinance as yf
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import aiohttp
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class FreeDataCollector:
    """무료 데이터 소스 통합 수집기"""
    
    def __init__(self):
        self.yahoo_suffix_map = {
            'KOSPI': '.KS',
            'KOSDAQ': '.KQ'
        }
    
    async def get_all_korean_stocks(self) -> Dict[str, Dict]:
        """한국 전체 종목 리스트 수집"""
        stocks = {}
        
        # 방법 1: Yahoo Finance에서 주요 종목
        stocks.update(await self.get_yahoo_korean_stocks())
        
        # 방법 2: 공개 API 활용
        stocks.update(await self.get_public_api_stocks())
        
        # 방법 3: 웹 스크래핑
        stocks.update(await self.scrape_stock_lists())
        
        return stocks
    
    async def get_yahoo_korean_stocks(self) -> Dict[str, Dict]:
        """Yahoo Finance에서 한국 주식 정보"""
        major_stocks = {
            # KOSPI 주요 종목
            "005930.KS": {"name": "삼성전자", "sector": "전자"},
            "000660.KS": {"name": "SK하이닉스", "sector": "전자"},
            "005490.KS": {"name": "POSCO홀딩스", "sector": "철강"},
            "005380.KS": {"name": "현대차", "sector": "자동차"},
            "035420.KS": {"name": "NAVER", "sector": "인터넷"},
            "051910.KS": {"name": "LG화학", "sector": "화학"},
            "006400.KS": {"name": "삼성SDI", "sector": "전자부품"},
            "035720.KS": {"name": "카카오", "sector": "인터넷"},
            "003550.KS": {"name": "LG", "sector": "지주회사"},
            "105560.KS": {"name": "KB금융", "sector": "금융"},
            "055550.KS": {"name": "신한지주", "sector": "금융"},
            "207940.KS": {"name": "삼성바이오로직스", "sector": "바이오"},
            "068270.KS": {"name": "셀트리온", "sector": "바이오"},
            
            # KOSDAQ 주요 종목
            "247540.KQ": {"name": "에코프로비엠", "sector": "배터리"},
            "086520.KQ": {"name": "에코프로", "sector": "화학"},
            "035900.KQ": {"name": "JYP Ent.", "sector": "엔터"},
            "293490.KQ": {"name": "카카오게임즈", "sector": "게임"},
            "112040.KQ": {"name": "위메이드", "sector": "게임"},
        }
        
        result = {}
        for ticker, info in major_stocks.items():
            code = ticker.split('.')[0]
            result[code] = {
                'code': code,
                'name': info['name'],
                'sector': info['sector'],
                'market': 'KOSPI' if ticker.endswith('.KS') else 'KOSDAQ',
                'yahoo_ticker': ticker
            }
        
        return result
    
    async def get_public_api_stocks(self) -> Dict[str, Dict]:
        """공개 API에서 종목 정보 수집"""
        stocks = {}
        
        # KRX 정보데이터시스템 (KIND) - 공개 데이터
        # 한국거래소 상장법인목록 다운로드 URL
        try:
            # KOSPI
            kospi_url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13&marketType=stockMkt"
            kospi_df = pd.read_html(kospi_url, encoding='cp949')[0]
            
            for _, row in kospi_df.iterrows():
                code = str(row['종목코드']).zfill(6)
                stocks[code] = {
                    'code': code,
                    'name': row['회사명'],
                    'sector': row.get('업종', '기타'),
                    'market': 'KOSPI'
                }
            
            # KOSDAQ
            kosdaq_url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13&marketType=kosdaqMkt"
            kosdaq_df = pd.read_html(kosdaq_url, encoding='cp949')[0]
            
            for _, row in kosdaq_df.iterrows():
                code = str(row['종목코드']).zfill(6)
                stocks[code] = {
                    'code': code,
                    'name': row['회사명'],
                    'sector': row.get('업종', '기타'),
                    'market': 'KOSDAQ'
                }
                
        except Exception as e:
            logger.error(f"공개 API 데이터 수집 실패: {e}")
        
        return stocks
    
    async def scrape_stock_lists(self) -> Dict[str, Dict]:
        """웹사이트에서 종목 리스트 스크래핑"""
        stocks = {}
        
        # 네이버 금융에서 시가총액 상위 종목
        try:
            async with aiohttp.ClientSession() as session:
                # KOSPI
                for page in range(1, 5):  # 상위 200개 종목
                    url = f"https://finance.naver.com/sise/sise_market_sum.nhn?sosok=0&page={page}"
                    async with session.get(url) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        for row in soup.find_all('tr', {'onmouseover': 'mouseOver(this)'}):
                            link = row.find('a', {'class': 'tltle'})
                            if link:
                                name = link.text
                                code = link['href'].split('=')[-1]
                                stocks[code] = {
                                    'code': code,
                                    'name': name,
                                    'market': 'KOSPI',
                                    'sector': '미분류'
                                }
                
                # KOSDAQ
                for page in range(1, 3):  # 상위 100개 종목
                    url = f"https://finance.naver.com/sise/sise_market_sum.nhn?sosok=1&page={page}"
                    async with session.get(url) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        for row in soup.find_all('tr', {'onmouseover': 'mouseOver(this)'}):
                            link = row.find('a', {'class': 'tltle'})
                            if link:
                                name = link.text
                                code = link['href'].split('=')[-1]
                                stocks[code] = {
                                    'code': code,
                                    'name': name,
                                    'market': 'KOSDAQ',
                                    'sector': '미분류'
                                }
                                
        except Exception as e:
            logger.error(f"웹 스크래핑 실패: {e}")
        
        return stocks
    
    def get_stock_price_yahoo(self, stock_code: str, market: str = 'KOSPI') -> Optional[Dict]:
        """Yahoo Finance에서 개별 종목 가격 정보"""
        try:
            ticker = f"{stock_code}{self.yahoo_suffix_map.get(market, '.KS')}"
            stock = yf.Ticker(ticker)
            
            # 현재가 정보
            info = stock.info
            history = stock.history(period="1d")
            
            if not history.empty:
                current_price = history['Close'].iloc[-1]
                return {
                    'code': stock_code,
                    'current_price': current_price,
                    'change': history['Close'].iloc[-1] - history['Open'].iloc[-1],
                    'change_percent': ((history['Close'].iloc[-1] / history['Open'].iloc[-1]) - 1) * 100,
                    'volume': history['Volume'].iloc[-1],
                    'high': history['High'].iloc[-1],
                    'low': history['Low'].iloc[-1]
                }
        except Exception as e:
            logger.error(f"Yahoo Finance 가격 조회 실패 {stock_code}: {e}")
        
        return None
    
    async def get_market_news_free(self) -> List[Dict]:
        """무료 뉴스 소스에서 시장 뉴스 수집"""
        news_list = []
        
        # RSS 피드 활용
        rss_feeds = [
            "https://www.hankyung.com/feed/finance",
            "https://rss.mk.co.kr/rss/30100041",  # 매일경제 증권
            "https://www.sedaily.com/RSS/Stock",  # 서울경제 증권
        ]
        
        for feed_url in rss_feeds:
            try:
                import feedparser
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:10]:  # 최근 10개
                    news_list.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.get('published', ''),
                        'source': feed.feed.title
                    })
            except Exception as e:
                logger.error(f"RSS 피드 수집 실패 {feed_url}: {e}")
        
        return news_list
    
    def analyze_sector_trends(self, stocks: Dict[str, Dict]) -> Dict[str, Dict]:
        """섹터별 트렌드 분석"""
        sector_data = {}
        
        # 섹터별로 그룹화
        for stock in stocks.values():
            sector = stock.get('sector', '기타')
            if sector not in sector_data:
                sector_data[sector] = {
                    'stocks': [],
                    'total_count': 0,
                    'avg_performance': 0
                }
            
            sector_data[sector]['stocks'].append(stock)
            sector_data[sector]['total_count'] += 1
        
        # 섹터별 통계
        for sector, data in sector_data.items():
            # 여기서는 더미 데이터 사용 (실제로는 가격 변화율 계산)
            data['avg_performance'] = np.random.uniform(-5, 5)
            data['trend'] = 'bullish' if data['avg_performance'] > 1 else 'bearish' if data['avg_performance'] < -1 else 'neutral'
        
        return sector_data


# 실시간 가격 모니터링 (무료)
class FreeRealtimeMonitor:
    """무료 실시간 모니터링"""
    
    def __init__(self):
        self.watched_stocks = {}
        self.update_interval = 60  # 1분마다 업데이트
    
    async def monitor_stocks(self, stock_codes: List[str], callback=None):
        """주기적으로 가격 업데이트"""
        collector = FreeDataCollector()
        
        while True:
            updates = []
            
            for code in stock_codes:
                price_data = collector.get_stock_price_yahoo(code)
                if price_data:
                    # 이전 가격과 비교
                    prev_price = self.watched_stocks.get(code, {}).get('current_price', 0)
                    if prev_price and prev_price != price_data['current_price']:
                        price_data['prev_price'] = prev_price
                        updates.append(price_data)
                    
                    self.watched_stocks[code] = price_data
            
            # 콜백 실행
            if callback and updates:
                await callback(updates)
            
            # 대기
            await asyncio.sleep(self.update_interval)


# 투자 시뮬레이터 (포트폴리오 테스트용)
class PortfolioSimulator:
    """포트폴리오 시뮬레이션"""
    
    def __init__(self, initial_capital: float = 10000000):  # 1천만원
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.portfolio = {}
        self.transaction_history = []
    
    def buy_stock(self, code: str, price: float, quantity: int):
        """주식 매수"""
        total_cost = price * quantity
        
        if total_cost > self.current_capital:
            return False, "자금 부족"
        
        self.current_capital -= total_cost
        
        if code not in self.portfolio:
            self.portfolio[code] = {'quantity': 0, 'avg_price': 0}
        
        # 평균 매입가 계산
        total_quantity = self.portfolio[code]['quantity'] + quantity
        total_value = (self.portfolio[code]['quantity'] * self.portfolio[code]['avg_price']) + total_cost
        
        self.portfolio[code]['quantity'] = total_quantity
        self.portfolio[code]['avg_price'] = total_value / total_quantity
        
        self.transaction_history.append({
            'type': 'BUY',
            'code': code,
            'price': price,
            'quantity': quantity,
            'timestamp': datetime.now()
        })
        
        return True, "매수 완료"
    
    def sell_stock(self, code: str, price: float, quantity: int):
        """주식 매도"""
        if code not in self.portfolio or self.portfolio[code]['quantity'] < quantity:
            return False, "보유 수량 부족"
        
        revenue = price * quantity
        self.current_capital += revenue
        
        self.portfolio[code]['quantity'] -= quantity
        if self.portfolio[code]['quantity'] == 0:
            del self.portfolio[code]
        
        self.transaction_history.append({
            'type': 'SELL',
            'code': code,
            'price': price,
            'quantity': quantity,
            'timestamp': datetime.now()
        })
        
        return True, "매도 완료"
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """포트폴리오 총 가치"""
        stock_value = 0
        
        for code, holding in self.portfolio.items():
            if code in current_prices:
                stock_value += holding['quantity'] * current_prices[code]
        
        return self.current_capital + stock_value
    
    def get_performance(self, current_prices: Dict[str, float]) -> Dict:
        """수익률 계산"""
        total_value = self.get_portfolio_value(current_prices)
        
        return {
            'initial_capital': self.initial_capital,
            'current_value': total_value,
            'profit_loss': total_value - self.initial_capital,
            'return_rate': ((total_value / self.initial_capital) - 1) * 100,
            'cash_balance': self.current_capital,
            'stock_holdings': self.portfolio
        }
