import React, { useState } from 'react';
import './App.css';

interface Stock {
  code: string;
  name: string;
  sector: string;
  score: number;
  reasons: string[];
}

function App() {
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<Stock[]>([]);
  const [stopLoss, setStopLoss] = useState<Stock[]>([]);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  
  const analyzeStocks = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      setRecommendations(data.recommendations || []);
      setStopLoss(data.stop_loss || []);
    } catch (error) {
      console.error('Error:', error);
      alert('분석 중 오류가 발생했습니다.');
    }
    setLoading(false);
  };
  
  return (
    <div className="App">
      <header className="App-header">
        <h1>🤖 AI 주식 추천 시스템</h1>
        <p>실시간 뉴스와 재무 분석 기반 추천</p>
        
        <button 
          onClick={analyzeStocks} 
          disabled={loading}
          className="analyze-button"
        >
          {loading ? '분석 중...' : '실시간 분석 시작'}
        </button>
        
        <div className="results-container">
          {recommendations.length > 0 && (
            <div className="recommendations">
              <h2>💰 매수 추천 종목</h2>
              {recommendations.map((stock) => (
                <div key={stock.code} className="stock-card buy">
                  <h3>{stock.name} ({stock.code})</h3>
                  <p>섹터: {stock.sector}</p>
                  <p>신뢰도: {(stock.score * 100).toFixed(1)}%</p>
                  <ul>
                    {stock.reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
          
          {stopLoss.length > 0 && (
            <div className="stop-loss">
              <h2>⚠️ 주의 종목</h2>
              {stopLoss.map((stock) => (
                <div key={stock.code} className="stock-card sell">
                  <h3>{stock.name} ({stock.code})</h3>
                  <p>섹터: {stock.sector}</p>
                  <p>위험도: {(stock.score * 100).toFixed(1)}%</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </header>
    </div>
  );
}

export default App;
