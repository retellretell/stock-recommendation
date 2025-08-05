# 📈 주식 날씨 예보판 (Stock Weather Dashboard)

> AI가 예측하는 주식 시장의 날씨, 상승/하락 확률을 직관적으로 확인하세요!

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)
![Next.js](https://img.shields.io/badge/Next.js-14.0.4-black.svg)

## 🌟 주요 특징

### 날씨로 보는 주식 추천
- **직관적인 날씨 아이콘**: ☀️ 맑음(상승), 🌧️ 비(하락) 등으로 한눈에 파악
- **스마트 규칙 기반 AI**: 실제 투자 전략을 코드화한 예측 시스템
  - RSI, MACD, 이동평균선 등 기술적 지표 분석
  - 골든크로스/데드크로스 패턴 인식
  - 볼린저 밴드, 거래량 분석
  - 펀더멘털 점수 통합
- **설명 가능한 AI**: 예측 근거를 명확히 제공

### 실시간 데이터 수집
- **Alpha Vantage API**: 실시간 미국 주식 데이터
- **Yahoo Finance**: 백업 데이터 소스
- **뉴스 감성 분석**: 최신 뉴스의 긍정/부정 분석
- **소셜 미디어 감성**: Reddit, 뉴스 등 종합 분석

### 접근성 및 포용성
- **색맹 친화적**: 색상 외에도 패턴과 텍스트로 정보 전달
- **스크린 리더 지원**: 시각 장애인을 위한 완전한 접근성
- **키보드 네비게이션**: 마우스 없이도 모든 기능 사용 가능

### 개인화된 경험
- **경험 수준별 UI**: 초보자/중급자/고급자 맞춤 인터페이스
- **리스크 성향 반영**: 보수적/중립적/공격적 투자 성향별 필터링
- **선호 섹터 설정**: 관심 있는 업종 위주로 정보 제공

## 🚀 빠른 시작

### 1. 자동 설치 및 실행

```bash
# 프로젝트 클론
git clone https://github.com/retellretell/stock-recommendation.git
cd stock-recommendation

# 실행 권한 부여
chmod +x run.sh

# 자동 설치 및 실행
./run.sh
```

**중요**: 실행 전에 Alpha Vantage API 키가 필요합니다!
1. [Alpha Vantage](https://www.alphavantage.co/support/#api-key)에서 무료 API 키 발급
2. `backend/.env` 파일에서 `ALPHA_VANTAGE_API_KEY` 설정

웹 브라우저에서 `http://localhost:3000` 접속

### 2. 수동 설치 (개발자용)

#### Alpha Vantage API 키 발급
1. [Alpha Vantage](https://www.alphavantage.co/support/#api-key) 에서 무료 API 키 발급
2. 무료 티어: 분당 5회, 일일 500회 요청 제한
3. `.env` 파일에 API 키 추가

#### 백엔드 설정

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파
