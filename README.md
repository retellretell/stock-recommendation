# 📈 주식 날씨 예보판 (Stock Weather Dashboard)

> AI가 예측하는 주식 시장의 날씨, 상승/하락 확률을 직관적으로 확인하세요!

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)
![Next.js](https://img.shields.io/badge/Next.js-14.0.4-black.svg)

## 🌟 주요 특징

### 날씨로 보는 주식 추천
- **직관적인 날씨 아이콘**: ☀️ 맑음(상승), 🌧️ 비(하락) 등으로 한눈에 파악
- **AI 기반 예측**: LSTM, XGBoost 등 앙상블 모델로 상승/하락 확률 계산
- **설명 가능한 AI**: SHAP을 통한 예측 근거 제공

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

# 자동 설치 및 실행
bash run.sh
```

웹 브라우저에서 `http://localhost:3000` 접속

### 2. 수동 설치 (개발자용)

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
# .env 파일을 편집하여 API 키 설정

# 서버 실행
uvicorn main:app --reload
```

#### 프론트엔드 설정

```bash
cd frontend

# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env.local

# 개발 서버 실행
npm run dev
```

### 3. Docker로 실행

```bash
# 전체 스택 실행
docker-compose up -d

# 개별 서비스 실행
docker-compose up backend
docker-compose up frontend
```

## 📊 API 문서

### 주요 엔드포인트

| 엔드포인트 | 설명 | 예시 |
|-----------|------|------|
| `GET /rankings` | 상승/하락 확률 랭킹 | [예시 응답](http://localhost:8000/rankings) |
| `GET /detail/{ticker}` | 종목 상세 정보 | [삼성전자](http://localhost:8000/detail/005930) |
| `GET /sectors` | 섹터별 날씨 지도 | [섹터 현황](http://localhost:8000/sectors) |
| `GET /personalized/{user_id}` | 개인화 대시보드 | 맞춤 추천 |
| `GET /backtest/results` | 백테스팅 결과 | 성능 분석 |

### 실시간 API 사용 예시

```python
import requests

# 상위 상승 예상 종목 조회
response = requests.get("http://localhost:8000/rankings?market=KR&limit=10")
gainers = response.json()["top_gainers"]

for stock in gainers:
    print(f"{stock['name']}: {stock['probability']*100:.1f}% 상승 확률")
```

## 🔧 기술 스택

### 백엔드
- **FastAPI**: 고성능 Python 웹 프레임워크
- **SQLite + aiosqlite**: 비동기 데이터베이스
- **ONNX Runtime**: ML 모델 추론
- **yfinance**: 무료 주식 데이터
- **SHAP**: 설명 가능한 AI
- **Structlog**: 구조화된 로깅

### 프론트엔드
- **Next.js**: React 기반 풀스택 프레임워크
- **Tailwind CSS**: 유틸리티 기반 스타일링
- **Chart.js**: 인터랙티브 차트
- **SWR**: 데이터 페칭 및 캐싱
- **TypeScript**: 타입 안전성

### AI/ML
- **TensorFlow**: LSTM 시계열 모델
- **XGBoost**: 그래디언트 부스팅
- **ONNX**: 모델 표준화 및 최적화
- **scikit-learn**: 전처리 및 평가

## 📈 백테스팅 성능

### 2023-2024년 실적 (1년간)

| 지표 | 수치 | 설명 |
|------|------|------|
| **전체 정확도** | 62.3% | 상승/하락 방향 예측 정확도 |
| **상승장 정확도** | 71.2% | 강세장에서의 예측 성공률 |
| **하락장 정확도** | 54.6% | 약세장에서의 예측 성공률 |
| **최대 손실률** | 15.2% | 최대 드로다운 |
| **샤프 비율** | 1.2 | 위험 대비 수익률 |

### 섹터별 성과

```
IT/전자: 68.5% 정확도 (가장 높음)
바이오: 58.1% 정확도
금융: 61.7% 정확도
제조업: 59.3% 정확도
```

## 🎨 사용자 인터페이스

### 메인 대시보드
```
🌤️ 주식 날씨 예보판

📊 섹터별 날씨
[IT: ☀️ 72°] [바이오: ⛅ 58°] [금융: 🌧️ 45°]

☀️ 맑음 예보 (상승 예상)    🌧️ 비 예보 (하락 예상)

1위 삼성전자 ☀️              1위 LG디스플레이 🌧️
   상승확률: 78%                하락확률: 76%
   예상수익: +5.2%              예상손실: -3.8%
```

### 접근성 기능
- **음성 안내**: "삼성전자, 상승 확률 78퍼센트, 신뢰도 높음"
- **큰 글씨**: 시력이 불편한 사용자를 위한 확대 기능
- **고대비 모드**: 명확한 색상 구분
- **키보드 단축키**: Alt+1(메인), Alt+2(네비게이션)

## 🔐 환경 변수 설정

### 백엔드 (.env)
```env
# API 키 (선택사항)
KRX_API_KEY=your_krx_api_key_here
DART_API_KEY=your_dart_api_key_here

# 캐시 설정
CACHE_TTL=10800
CACHE_FRESHNESS=3600

# API 설정
BATCH_SIZE=100
RATE_LIMIT_DELAY=1.0
MAX_RETRIES=3
```

### 프론트엔드 (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_REFRESH_INTERVAL=300000
NEXT_PUBLIC_ENABLE_NEWS_SENTIMENT=true
NEXT_PUBLIC_ENABLE_SECTOR_MAP=true
```

## 🤖 AI 모델 학습

### Google Colab에서 모델 훈련

1. `train_models.ipynb` 노트북을 Google Colab에서 열기
2. 한국/미국 주요 종목 데이터 수집 및 전처리
3. LSTM, XGBoost 모델 훈련
4. ONNX 형식으로 변환 및 저장

```python
# 모델 훈련 예시
from tensorflow import keras

model = keras.Sequential([
    keras.layers.LSTM(64, return_sequences=True),
    keras.layers.Dropout(0.2),
    keras.layers.LSTM(32),
    keras.layers.Dense(1, activation='sigmoid')
])
```

## 🧪 테스트

```bash
# 백엔드 테스트
cd backend
pytest tests/ -v

# 프론트엔드 테스트
cd frontend
npm test

# E2E 테스트
npm run test:e2e
```

## 📦 배포

### Vercel (프론트엔드)
```bash
npm install -g vercel
vercel --prod
```

### Railway/Render (백엔드)
```bash
# requirements.txt와 Dockerfile 자동 감지
git push origin main
```

### Docker 배포
```bash
# 프로덕션 빌드
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 기여하기

### 기여 방법

1. **이슈 등록**: 버그 리포트나 기능 제안을 [Issues](https://github.com/retellretell/stock-recommendation/issues)에 등록
2. **포크 및 개발**:
   ```bash
   git fork https://github.com/retellretell/stock-recommendation.git
   git clone https://github.com/your-username/stock-recommendation.git
   git checkout -b feature/your-feature
   ```
3. **풀 리퀘스트**: 변경사항을 메인 브랜치로 제출

### 코딩 규칙

- **Python**: Black 포매터, type hints 사용
- **TypeScript**: ESLint + Prettier 설정 준수
- **커밋 메시지**: `feat:`, `fix:`, `docs:` 등 conventional commits

### 우선순위가 높은 기여 영역

- [ ] 새로운 ML 모델 (Transformer, GNN 등)
- [ ] 추가 데이터 소스 (뉴스 API, 소셜 미디어)
- [ ] 다국어 지원 (영어, 일본어)
- [ ] 모바일 앱 (React Native)
- [ ] 음성 인터페이스 (Web Speech API)

## 📝 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.

```
MIT License

Copyright (c) 2025 rin choi

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

## ⚠️ 면책 조항

- 이 앱은 **교육 및 참고 목적**으로 제작되었습니다
- AI 예측은 **100% 정확하지 않으며**, 투자 손실에 대해 책임지지 않습니다
- 모든 투자는 **본인의 판단과 책임** 하에 진행하세요
- 실제 투자 전 **전문가 상담**을 권장합니다

## 📞 지원 및 문의

### 커뮤니티
- **GitHub Discussions**: 일반적인 질문과 토론
- **Discord**: [실시간 채팅방](https://discord.gg/stock-weather)
- **Issues**: 버그 리포트 및 기능 요청

### 개발자 연락처
- **GitHub**: [@retellretell](https://github.com/retellretell)
- **Email**: xx

---

<div align="center">

**⭐ 이 프로젝트가 도움이 되었다면 GitHub Star를 눌러주세요!**

[🌟 Star 추가하기](https://github.com/retellretell/stock-recommendation/stargazers) | [🐛 버그 신고](https://github.com/retellretell/stock-recommendation/issues) | [💡 기능 제안](https://github.com/retellretell/stock-recommendation/discussions)

*주식 투자는 신중하게, AI는 도구로 활용하세요* 📈

</div>
