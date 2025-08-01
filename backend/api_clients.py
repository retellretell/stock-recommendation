"""
외부 API 클라이언트 (개선된 버전)
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime, timedelta
import structlog
from bs4 import BeautifulSoup

from config import settings
from exceptions import APIError

logger = structlog.get_logger()

class BaseAPIClient:
    """API 클라이언트 기본 클래스"""
    
    def __init__(self):
        self.session = None
        self.retry_count = settings.max_retries
        self.retry_delay = 1.0
    
    async def _ensure_session(self):
        """세션 확인 및 생성"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict:
        """재시도 로직이 포함된 HTTP 요청"""
        await self._ensure_session()
        
        for attempt in range(self.retry_count):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning("rate_limit_hit", url=url, retry_after=retry_after)
                        await asyncio.sleep(retry_after)
                    else:
                        logger.error("api_request_failed", url=url, status=response.status)
                        
            except asyncio.TimeoutError:
                logger.error("api_request_timeout", url=url, attempt=attempt)
            except aiohttp.ClientError as e:
                logger.error("api_client_error", url=url, error=str(e))
            
            # 재시도 대기
            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        raise APIError(f"API 요청 실패: {url}")
    
    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()

class KRXClient(BaseAPIClient):
    """한국거래소 API 클라이언트"""
    
    def __init__(self):
        super().__init__()
        self.api_key = settings.krx_api_key
        self.base_url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        
        if not self.api_key and settings.env == "production":
            raise ValueError("KRX API 키가 설정되지 않았습니다")
    
    def _validate_api_key(self, key: str) -> bool:
        """API 키 형식 검증"""
        # KRX API 키 형식에 맞게 수정
        return len(key) >= 10 and key.replace('-', '').isalnum()
    
    async def get_all_tickers(self) -> List[str]:
        """전체 종목 코드 조회"""
        await self._ensure_session()
        
        try:
            all_tickers = []
            
            # KOSPI
            kospi_tickers = await self._get_market_tickers('STK')
            all_tickers.extend(kospi_tickers)
            logger.info("krx_kospi_loaded", count=len(kospi_tickers))
            
            # KOSDAQ
            kosdaq_tickers = await self._get_market_tickers('KSQ')
            all_tickers.extend(kosdaq_tickers)
            logger.info("krx_kosdaq_loaded", count=len(kosdaq_tickers))
            
            return all_tickers
            
        except Exception as e:
            logger.error("krx_tickers_load_error", error=str(e))
            # 대표 종목만 반환 (fallback)
            return ['005930', '000660', '035420', '051910', '006400']
    
    async def _get_market_tickers(self, market: str) -> List[str]:
        """시장별 종목 코드 조회"""
        data = {
            'bld': 'dbms/MDC/STAT/standard/MDCSTAT01501',
            'locale': 'ko_KR',
            'mktId': market,
            'trdDd': datetime.now().strftime('%Y%m%d')
        }
        
        if self.api_key:
            data['key'] = self.api_key
        
        try:
            result = await self._make_request('POST', self.base_url, data=data)
            return [item['ISU_SRT_CD'] for item in result.get('output', [])]
        except Exception as e:
            logger.error("krx_market_tickers_error", market=market, error=str(e))
            return []
    
    async def get_price_data(self, ticker: str) -> Dict:
        """종목 가격 데이터 조회"""
        await self._ensure_session()
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)  # 6개월
            
            data = {
                'bld': 'dbms/MDC/STAT/standard/MDCSTAT01701',
                'locale': 'ko_KR',
                'isuCd': ticker,
                'strtDd': start_date.strftime('%Y%m%d'),
                'endDd': end_date.strftime('%Y%m%d')
            }
            
            if self.api_key:
                data['key'] = self.api_key
            
            result = await self._make_request('POST', self.base_url, data=data)
            return self._parse_price_data(result.get('output', []))
            
        except Exception as e:
            logger.error("krx_price_data_error", ticker=ticker, error=str(e))
            return {}
    
    def _parse_price_data(self, data: List[Dict]) -> Dict:
        """가격 데이터 파싱"""
        if not data:
            return {}
        
        history = []
        for item in data:
            try:
                history.append({
                    'date': item.get('TRD_DD'),
                    'open': float(item.get('TDD_OPNPRC', 0)),
                    'high': float(item.get('TDD_HGPRC', 0)),
                    'low': float(item.get('TDD_LWPRC', 0)),
                    'close': float(item.get('TDD_CLSPRC', 0)),
                    'volume': int(item.get('ACC_TRDVOL', 0))
                })
            except (ValueError, TypeError) as e:
                logger.warning("krx_price_parse_warning", error=str(e))
                continue
        
        if history:
            return {
                'close': history[-1]['close'],
                'history': history
            }
        return {}

class DARTClient(BaseAPIClient):
    """DART (전자공시) API 클라이언트"""
    
    def __init__(self):
        super().__init__()
        self.api_key = settings.dart_api_key
        self.base_url = "https://opendart.fss.or.kr/api"
        
        if not self.api_key and settings.env == "production":
            raise ValueError("DART API 키가 설정되지 않았습니다")
        
        # 기업 코드 매핑 (더 많은 종목 추가)
        self.corp_mapping = {
            '005930': '00126380',  # 삼성전자
            '000660': '00164779',  # SK하이닉스
            '035420': '00226455',  # NAVER
            '051910': '00356361',  # LG화학
            '006400': '00126186',  # 삼성SDI
            '005380': '00164742',  # 현대차
            '035720': '01040273',  # 카카오
            '207940': '00976610',  # 삼성바이오로직스
            '005490': '00190321',  # POSCO홀딩스
            '000270': '00146030',  # 기아
        }
    
    async def get_financial_data(self, ticker: str) -> Dict:
        """재무 데이터 조회"""
        await self._ensure_session()
        
        try:
            # 기업 코드 조회
            corp_code = await self._get_corp_code(ticker)
            if not corp_code:
                logger.warning("dart_corp_code_not_found", ticker=ticker)
                return {}
            
            # 재무 정보 조회
            financial_info = await self._fetch_financial_info(corp_code)
            
            # 기업 개요 정보 추가
            company_info = await self._fetch_company_info(corp_code)
            financial_info.update(company_info)
            
            return financial_info
            
        except Exception as e:
            logger.error("dart_financial_data_error", ticker=ticker, error=str(e))
            return {}
    
    async def _get_corp_code(self, ticker: str) -> Optional[str]:
        """종목 코드로 기업 코드 조회"""
        # 매핑 테이블에서 찾기
        if ticker in self.corp_mapping:
            return self.corp_mapping[ticker]
        
        # TODO: DART API를 통한 동적 조회 구현
        # 현재는 매핑이 없으면 None 반환
        return None
    
    async def _fetch_financial_info(self, corp_code: str) -> Dict:
        """재무제표 정보 조회"""
        url = f"{self.base_url}/fnlttSinglAcntAll.json"
        
        current_year = datetime.now().year
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': str(current_year - 1),  # 작년 데이터
            'reprt_code': '11011',  # 사업보고서
            'fs_div': 'CFS'  # 연결재무제표
        }
        
        try:
            result = await self._make_request('GET', url, params=params)
            return self._parse_financial_data(result.get('list', []))
        except Exception as e:
            logger.error("dart_financial_fetch_error", corp_code=corp_code, error=str(e))
            return {}
    
    async def _fetch_company_info(self, corp_code: str) -> Dict:
        """기업 개요 정보 조회"""
        url = f"{self.base_url}/company.json"
        
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code
        }
        
        try:
            result = await self._make_request('GET', url, params=params)
            
            if result.get('status') == '000':
                return {
                    'name': result.get('corp_name', ''),
                    'sector': result.get('induty_code', ''),
                    'market_cap': None  # DART에서는 제공하지 않음
                }
            return {}
            
        except Exception as e:
            logger.error("dart_company_info_error", corp_code=corp_code, error=str(e))
            return {}
    
    def _parse_financial_data(self, data: List[Dict]) -> Dict:
        """재무 데이터 파싱"""
        result = {}
        
        for item in data:
            account_nm = item.get('account_nm', '')
            
            try:
                # ROE
                if '자기자본이익률' in account_nm or 'ROE' in account_nm:
                    result['roe'] = float(item.get('thstrm_amount', 0))
                
                # EPS
                elif '주당순이익' in account_nm or 'EPS' in account_nm:
                    result['eps'] = float(item.get('thstrm_amount', 0))
                    result['prev_year_eps'] = float(item.get('frmtrm_amount', 0))
                
                # 매출액
                elif '매출액' in account_nm or '영업수익' in account_nm:
                    result['revenue'] = float(item.get('thstrm_amount', 0))
                    result['prev_year_revenue'] = float(item.get('frmtrm_amount', 0))
                
                # 영업이익
                elif '영업이익' in account_nm:
                    result['operating_profit'] = float(item.get('thstrm_amount', 0))
                
                # 당기순이익
                elif '당기순이익' in account_nm and '주당' not in account_nm:
                    result['net_income'] = float(item.get('thstrm_amount', 0))
                    
            except (ValueError, TypeError) as e:
                logger.warning("dart_parse_warning", account=account_nm, error=str(e))
                continue
        
        # YoY 계산
        if 'eps' in result and 'prev_year_eps' in result:
            if result['prev_year_eps'] != 0:
                result['eps_yoy'] = ((result['eps'] - result['prev_year_eps']) / 
                                    abs(result['prev_year_eps'])) * 100
        
        if 'revenue' in result and 'prev_year_revenue' in result:
            if result['prev_year_revenue'] != 0:
                result['revenue_yoy'] = ((result['revenue'] - result['prev_year_revenue']) / 
                                        result['prev_year_revenue']) * 100
        
        return result
