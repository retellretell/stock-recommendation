"""
외부 API 클라이언트
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class KRXClient:
    """한국거래소 API 클라이언트"""
    
    def __init__(self):
        self.api_key = os.getenv('KRX_API_KEY')
        self.base_url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        self.session = None
    
    async def _ensure_session(self):
        """세션 확인 및 생성"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def get_all_tickers(self) -> List[str]:
        """전체 종목 코드 조회"""
        await self._ensure_session()
        
        try:
            # KOSPI
            kospi_tickers = await self._get_market_tickers('STK')
            
            # KOSDAQ
            kosdaq_tickers = await self._get_market_tickers('KSQ')
            
            return kospi_tickers + kosdaq_tickers
            
        except Exception as e:
            logger.error(f"KRX 종목 조회 오류: {e}")
            # 대표 종목만 반환
            return ['005930', '000660', '035420', '051910', '006400']
    
    async def _get_market_tickers(self, market: str) -> List[str]:
        """시장별 종목 코드 조회"""
        data = {
            'bld': 'dbms/MDC/STAT/standard/MDCSTAT01501',
            'locale': 'ko_KR',
            'mktId': market,
            'trdDd': datetime.now().strftime('%Y%m%d')
        }
        
        async with self.session.post(self.base_url, data=data) as response:
            if response.status == 200:
                result = await response.json()
                return [item['ISU_SRT_CD'] for item in result.get('output', [])]
            else:
                logger.error(f"KRX API 오류: {response.status}")
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
            
            async with self.session.post(self.base_url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return self._parse_price_data(result.get('output', []))
                else:
                    logger.error(f"가격 데이터 조회 오류: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"KRX 가격 조회 오류 {ticker}: {e}")
            return {}
    
    def _parse_price_data(self, data: List[Dict]) -> Dict:
        """가격 데이터 파싱"""
        if not data:
            return {}
        
        history = []
        for item in data:
            history.append({
                'date': item.get('TRD_DD'),
                'open': float(item.get('TDD_OPNPRC', 0)),
                'high': float(item.get('TDD_HGPRC', 0)),
                'low': float(item.get('TDD_LWPRC', 0)),
                'close': float(item.get('TDD_CLSPRC', 0)),
                'volume': int(item.get('ACC_TRDVOL', 0))
            })
        
        return {
            'close': history[-1]['close'] if history else 0,
            'history': history
        }
    
    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()


class DARTClient:
    """DART (전자공시) API 클라이언트"""
    
    def __init__(self):
        self.api_key = os.getenv('DART_API_KEY')
        self.base_url = "https://opendart.fss.or.kr/api"
        self.session = None
    
    async def _ensure_session(self):
        """세션 확인 및 생성"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def get_financial_data(self, ticker: str) -> Dict:
        """재무 데이터 조회"""
        await self._ensure_session()
        
        try:
            # 기업 코드 조회
            corp_code = await self._get_corp_code(ticker)
            if not corp_code:
                return {}
            
            # 재무 정보 조회
            financial_info = await self._fetch_financial_info(corp_code)
            
            return financial_info
            
        except Exception as e:
            logger.error(f"DART 재무 데이터 조회 오류 {ticker}: {e}")
            return {}
    
    async def _get_corp_code(self, ticker: str) -> Optional[str]:
        """종목 코드로 기업 코드 조회"""
        # 실제로는 DART 기업 코드 매핑 테이블 필요
        # 임시로 하드코딩
        corp_mapping = {
            '005930': '00126380',  # 삼성전자
            '000660': '00164779',  # SK하이닉스
            '035420': '00226455',  # NAVER
            # ... 더 많은 매핑
        }
        return corp_mapping.get(ticker)
    
    async def _fetch_financial_info(self, corp_code: str) -> Dict:
        """재무제표 정보 조회"""
        url = f"{self.base_url}/fnlttSinglAcntAll.json"
        
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': str(datetime.now().year - 1),  # 작년
            'reprt_code': '11011',  # 사업보고서
            'fs_div': 'CFS'  # 연결재무제표
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return self._parse_financial_data(data.get('list', []))
            else:
                logger.error(f"DART API 오류: {response.status}")
                return {}
    
    def _parse_financial_data(self, data: List[Dict]) -> Dict:
        """재무 데이터 파싱"""
        result = {}
        
        for item in data:
            account_nm = item.get('account_nm', '')
            
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
    
    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()
