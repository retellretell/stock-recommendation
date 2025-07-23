from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from datetime import datetime
import random

app = FastAPI(title="Stock Recommendation API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 더미 주식 데이터
DUMMY_STOCKS = {
    "005930": {"name": "삼성전자", "sector": "전자"},
    "000660": {"name": "SK하이닉스", "sector": "전자"},
    "035720": {"name": "카카오", "sector": "IT"},
    "005380": {"name": "현대차", "sector": "자동차"},
    "035420": {"name": "네이버", "sector": "IT"},
    "051910": {"name": "LG화학", "sector": "화학"},
    "006400": {"name": "삼성SDI", "sector": "전자"},
    "068270": {"name": "셀트리온", "sector": "바이오"},
    "105560": {"name": "KB금융", "sector": "금융"},
    "055550": {"name": "신한지주", "sector": "금융"}
}

@app.get("/")
def read_root():
    return {
        "message": "Stock Recommendation API",
        "version": "1.0.0",
        "status": "running"
    }

@app.post("/api/analyze")
def analyze_stocks():
    """주식 분석 API"""
    recommendations = []
    
    # 랜덤하게 5개 종목 추천
    selected_stocks = random.sample(list(DUMMY_STOCKS.items()), 5)
    
    for code, info in selected_stocks:
        score = random.uniform(0.3, 0.9)
        recommendations.append({
            "code": code,
            "name": info["name"],
            "sector": info["sector"],
            "score": score,
            "confidence": score,
            "reasons": [
                "긍정적인 뉴스 다수",
                "재무 건전성 양호",
                "섹터 전망 긍정적"
            ][:random.randint(1, 3)]
        })
    
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "recommendations": recommendations[:3],
        "stop_loss": recommendations[-2:],
        "market_summary": {
            "overall_sentiment": "neutral",
            "fear_greed_index": random.uniform(40, 60)
        }
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
