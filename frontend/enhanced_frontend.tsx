import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, AlertTriangle, BarChart2, RefreshCw, Filter } from 'lucide-react';

interface Stock {
  code: string;
  name: string;
  market: string;
  sector: string;
  score?: number;
}

interface SectorAnalysis {
  score: number;
  trend: string;
  total_mentions: number;
}

interface MarketSummary {
  market_sentiment_index: number;
  total_stocks: number;
  positive_stocks: number;
  negative_stocks: number;
  strongest_sectors: string[];
  weakest_sectors: string[];
}

function App() {
  const [loading, setLoading] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<string>('idle');
  const [marketData, setMarketData] = useState<any>(null);
  const [allStocks, setAllStocks] = useState<Stock[]>([]);
  const [sectors, setSectors] = useState<any[]>([]);
  const [selectedSector, setSelectedSector] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<Stock[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'sectors' | 'stocks'>('overview');
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // 초기 데이터 로드
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // 섹터 리스트 로드
      const sectorsRes = await fetch(`${API_URL}/api/sectors/list`);
      const sectorsData = await sectorsRes.json();
      setSectors(sectorsData.sectors);
      
      // 시장 요약 로드
      const summaryRes = await fetch(`${API_URL}/api/market/summary`);
      const summaryData = await summaryRes.json();
      setMarketData(summaryData);
    } catch (error) {
      console.error('초기 데이터 로드 실패:', error);
    }
  };

  const startFullAnalysis = async () => {
    setLoading(true);
    setAnalysisStatus('starting');
    
    try {
      const response = await fetch(`${API_URL}/api/analyze/full`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.status === 'analysis_started' || data.status === 'analysis_in_progress') {
        setAnalysisStatus('in_progress');
        // 주기적으로 상태 확인
        checkAnalysisStatus();
      } else if (data.cache_info?.cached) {
        setMarketData(data);
        setAnalysisStatus('completed');
        setLoading(false);
      }
    } catch (error) {
      console.error('분석 시작 실패:', error);
      setLoading(false);
    }
  };

  const checkAnalysisStatus = async () => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/market/status`);
        const status = await response.json();
        
        if (status.status === 'completed') {
          clearInterval(interval);
          // 결과 가져오기
          const resultRes = await fetch(`${API_URL}/api/market/summary`);
          const result = await resultRes.json();
          setMarketData(result);
          setAnalysisStatus('completed');
          setLoading(false);
        }
      } catch (error) {
        console.error('상태 확인 실패:', error);
      }
    }, 5000); // 5초마다 확인
  };

  const searchStocks = async () => {
    if (!searchTerm) return;
    
    try {
      const response = await fetch(`${API_URL}/api/stocks/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: searchTerm, limit: 20 })
      });
      const data = await response.json();
      setSearchResults(data.results);
    } catch (error) {
      console.error('종목 검색 실패:', error);
    }
  };

  const loadSectorStocks = async (sector: string) => {
    try {
      const response = await fetch(`${API_URL}/api/stocks/list?sector=${sector}`);
      const data = await response.json();
      setAllStocks(data.stocks);
    } catch (error) {
      console.error('섹터 종목 로드 실패:', error);
    }
  };

  const getSentimentColor = (value: number) => {
    if (value > 60) return 'text-green-600';
    if (value < 40) return 'text-red-600';
    return 'text-gray-600';
  };

  const getSentimentText = (value: number) => {
    if (value > 70) return '매우 긍정적';
    if (value > 60) return '긍정적';
    if (value > 40) return '중립';
    if (value > 30) return '부정적';
    return '매우 부정적';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-2">
              <BarChart2 className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">AI 주식 시장 전체 분석</h1>
            </div>
            <button
              onClick={startFullAnalysis}
              disabled={loading}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? (
                <>
                  <RefreshCw className="animate-spin h-5 w-5 mr-2" />
                  분석 중...
                </>
              ) : (
                <>
                  <TrendingUp className="h-5 w-5 mr-2" />
                  전체 시장 분석
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* 탭 네비게이션 */}
      <div className="border-b bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              시장 개요
            </button>
            <button
              onClick={() => setActiveTab('sectors')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'sectors'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              섹터별 분석
            </button>
            <button
              onClick={() => setActiveTab('stocks')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'stocks'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              종목 검색
            </button>
          </nav>
        </div>
      </div>

      {/* 메인 컨텐츠 */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* 분석 상태 표시 */}
        {analysisStatus === 'in_progress' && (
          <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
            <div className="flex">
              <RefreshCw className="animate-spin h-5 w-5 text-blue-400 mr-3" />
              <p className="text-sm text-blue-700">
                전체 시장을 분석 중입니다. 2-3분 정도 소요됩니다...
              </p>
            </div>
          </div>
        )}

        {/* 시장 개요 탭 */}
        {activeTab === 'overview' && marketData && (
          <div className="space-y-6">
            {/* 주요 지표 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">시장 심리 지수</h3>
                <p className={`text-3xl font-bold mt-2 ${getSentimentColor(marketData.market_summary?.market_sentiment_index || 50)}`}>
                  {marketData.market_summary?.market_sentiment_index?.toFixed(1) || '50.0'}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  {getSentimentText(marketData.market_summary?.market_sentiment_index || 50)}
                </p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">분석된 종목</h3>
                <p className="text-3xl font-bold mt-2">{marketData.total_stocks_analyzed || marketData.total_stocks || 0}</p>
                <p className="text-sm text-gray-600 mt-1">KOSPI + KOSDAQ</p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">상승 종목</h3>
                <p className="text-3xl font-bold mt-2 text-green-600">
                  {marketData.market_summary?.positive_stocks || 0}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  {((marketData.market_summary?.positive_stocks / marketData.market_summary?.total_stocks) * 100 || 0).toFixed(1)}%
                </p>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">하락 종목</h3>
                <p className="text-3xl font-bold mt-2 text-red-600">
                  {marketData.market_summary?.negative_stocks || 0}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  {((marketData.market_summary?.negative_stocks / marketData.market_summary?.total_stocks) * 100 || 0).toFixed(1)}%
                </p>
              </div>
            </div>

            {/* 추천/회피 종목 */}
            {marketData.top_recommendations && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 추천 종목 */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-lg font-semibold mb-4 flex items-center">
                    <TrendingUp className="h-5 w-5 text-green-500 mr-2" />
                    추천 종목 TOP 10
                  </h2>
                  <div className="space-y-3">
                    {marketData.top_recommendations?.slice(0, 10).map((stock: any, idx: number) => (
                      <div key={stock.code} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                        <div>
                          <span className="font-medium">{idx + 1}. {stock.name}</span>
                          <span className="text-sm text-gray-500 ml-2">({stock.code})</span>
                          <div className="text-xs text-gray-600 mt-1">{stock.sector} · {stock.market}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-green-600 font-semibold">
                            {(stock.score * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-500">
                            신뢰도 {(stock.confidence * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 회피 종목 */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-lg font-semibold mb-4 flex items-center">
                    <TrendingDown className="h-5 w-5 text-red-500 mr-2" />
                    주의 종목
                  </h2>
                  <div className="space-y-3">
                    {marketData.stocks_to_avoid?.slice(0, 10).map((stock: any, idx: number) => (
                      <div key={stock.code} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                        <div>
                          <span className="font-medium">{idx + 1}. {stock.name}</span>
                          <span className="text-sm text-gray-500 ml-2">({stock.code})</span>
                          <div className="text-xs text-gray-600 mt-1">{stock.sector} · {stock.market}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-red-600 font-semibold">
                            {(stock.score * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-500">
                            신뢰도 {(stock.confidence * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 강세/약세 섹터 */}
            {marketData.market_summary && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4">강세 섹터</h3>
                  <div className="space-y-2">
                    {marketData.market_summary.strongest_sectors?.map((sector: string) => (
                      <div key={sector} className="flex items-center p-2 bg-green-50 rounded">
                        <TrendingUp className="h-4 w-4 text-green-600 mr-2" />
                        <span className="font-medium">{sector}</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4">약세 섹터</h3>
                  <div className="space-y-2">
                    {marketData.market_summary.weakest_sectors?.map((sector: string) => (
                      <div key={sector} className="flex items-center p-2 bg-red-50 rounded">
                        <TrendingDown className="h-4 w-4 text-red-600 mr-2" />
                        <span className="font-medium">{sector}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 섹터별 분석 탭 */}
        {activeTab === 'sectors' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">섹터별 현황</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sectors.map((sector) => (
                  <div
                    key={sector.name}
                    className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => {
                      setSelectedSector(sector.name);
                      loadSectorStocks(sector.name);
                    }}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium text-gray-900">{sector.name}</h3>
                        <p className="text-sm text-gray-500 mt-1">
                          총 {sector.stock_count}개 종목
                        </p>
                        <div className="text-xs text-gray-400 mt-2">
                          KOSPI: {sector.markets.KOSPI} | KOSDAQ: {sector.markets.KOSDAQ}
                        </div>
                      </div>
                      <Filter className="h-4 w-4 text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 선택된 섹터의 종목 리스트 */}
            {selectedSector && allStocks.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">{selectedSector} 섹터 종목</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {allStocks.map((stock) => (
                    <div key={stock.code} className="p-3 border rounded hover:bg-gray-50">
                      <div className="font-medium">{stock.name}</div>
                      <div className="text-sm text-gray-500">{stock.code} · {stock.market}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 종목 검색 탭 */}
        {activeTab === 'stocks' && (
          <div className="space-y-6">
            {/* 검색 바 */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex space-x-4">
                <div className="flex-1">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && searchStocks()}
                    placeholder="종목명 또는 종목코드로 검색..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <button
                  onClick={searchStocks}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center"
                >
                  <Search className="h-4 w-4 mr-2" />
                  검색
                </button>
              </div>
            </div>

            {/* 검색 결과 */}
            {searchResults.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">검색 결과 ({searchResults.length}개)</h3>
                <div className="space-y-3">
                  {searchResults.map((stock) => (
                    <div key={stock.code} className="flex justify-between items-center p-4 border rounded-lg hover:bg-gray-50">
                      <div>
                        <div className="font-medium text-lg">{stock.name}</div>
                        <div className="text-sm text-gray-500">{stock.code} · {stock.market} · {stock.sector}</div>
                      </div>
                      <button className="px-4 py-2 text-sm bg-gray-100 rounded hover:bg-gray-200">
                        상세보기
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 검색 안내 */}
            {searchResults.length === 0 && !searchTerm && (
              <div className="text-center py-12">
                <Search className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">종목 검색</h3>
                <p className="mt-1 text-sm text-gray-500">
                  종목명이나 종목코드를 입력하여 검색하세요
                </p>
              </div>
            )}
          </div>
        )}

        {/* 초기 상태 */}
        {!marketData && !loading && activeTab === 'overview' && (
          <div className="text-center py-12">
            <BarChart2 className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">전체 시장 분석 준비</h3>
            <p className="mt-1 text-sm text-gray-500">
              상단의 '전체 시장 분석' 버튼을 클릭하여 KOSPI/KOSDAQ 전 종목을 분석하세요
            </p>
            <div className="mt-4 text-xs text-gray-400">
              * 분석에는 2-3분이 소요됩니다
            </div>
          </div>
        )}
      </main>

      {/* 푸터 */}
      <footer className="bg-gray-100 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>KOSPI/KOSDAQ 전 종목 실시간 분석 시스템</p>
            <p className="mt-1">데이터는 뉴스 및 공개 정보를 기반으로 AI가 분석한 결과입니다</p>
          </div>
        </div>
      </footer>
    </div>
  );
}