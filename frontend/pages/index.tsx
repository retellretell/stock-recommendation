import React, { useState, useEffect } from 'react';
import { GetServerSideProps } from 'next';
import Head from 'next/head';
import Link from 'next/link';
import axios from 'axios';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import StockWeatherCard from '../components/StockWeatherCard';
import WeatherGauge from '../components/WeatherGauge';
import SectorWeatherMap from '../components/SectorWeatherMap';

interface StockRanking {
  ticker: string;
  name: string;
  sector: string;
  probability: number;
  expected_return: number;
  fundamental_score: number;
  weather_icon: string;
  confidence: number;
}

interface RankingsData {
  top_gainers: StockRanking[];
  top_losers: StockRanking[];
  updated_at: string;
}

interface HomeProps {
  initialData: RankingsData | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home({ initialData }: HomeProps) {
  const [rankings, setRankings] = useState<RankingsData | null>(initialData);
  const [loading, setLoading] = useState(false);
  const [market, setMarket] = useState('ALL');
  const [activeTab, setActiveTab] = useState<'gainers' | 'losers'>('gainers');

  const fetchRankings = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/rankings`, {
        params: { market, limit: 20 }
      });
      setRankings(response.data);
    } catch (error) {
      console.error('랭킹 데이터 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (market !== 'ALL' || !initialData) {
      fetchRankings();
    }
  }, [market]);

  // 5분마다 자동 갱신
  useEffect(() => {
    const interval = setInterval(fetchRankings, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [market]);

  const displayStocks = rankings ? 
    (activeTab === 'gainers' ? rankings.top_gainers : rankings.top_losers) : [];

  return (
    <>
      <Head>
        <title>주식 날씨 예보판 - AI 기반 주식 예측</title>
        <meta name="description" content="AI가 예측하는 주식 시장의 날씨, 상승/하락 확률 랭킹" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        {/* 헤더 */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <h1 className="text-2xl font-bold text-gray-900 flex items-center">
                  <span className="mr-2">🌤️</span>
                  주식 날씨 예보판
                </h1>
              </div>
              <nav className="flex space-x-4">
                <select
                  value={market}
                  onChange={(e) => setMarket(e.target.value)}
                  className="px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ALL">전체</option>
                  <option value="KR">한국</option>
                  <option value="US">미국</option>
                </select>
              </nav>
            </div>
          </div>
        </header>

        {/* 메인 컨텐츠 */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 업데이트 시간 */}
          {rankings && (
            <div className="text-center mb-6 text-gray-600">
              마지막 업데이트: {format(new Date(rankings.updated_at), 'PPpp', { locale: ko })}
            </div>
          )}

          {/* 섹터별 날씨 지도 */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-4">📊 섹터별 날씨</h2>
            <SectorWeatherMap />
          </div>

          {/* 탭 선택 */}
          <div className="flex justify-center mb-8">
            <div className="bg-white rounded-lg shadow-sm p-1 inline-flex">
              <button
                onClick={() => setActiveTab('gainers')}
                className={`px-6 py-2 rounded-md font-medium transition ${
                  activeTab === 'gainers'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                ☀️ 맑음 예보 (상승 예상)
              </button>
              <button
                onClick={() => setActiveTab('losers')}
                className={`px-6 py-2 rounded-md font-medium transition ${
                  activeTab === 'losers'
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                🌧️ 비 예보 (하락 예상)
              </button>
            </div>
          </div>

          {/* 주식 랭킹 그리드 */}
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {displayStocks.map((stock, index) => (
                <Link
                  key={stock.ticker}
                  href={`/detail/${stock.ticker}`}
                  className="transform transition-transform hover:scale-105"
                >
                  <StockWeatherCard
                    stock={stock}
                    rank={index + 1}
                    type={activeTab}
                  />
                </Link>
              ))}
            </div>
          )}

          {/* 전체 시장 게이지 */}
          <div className="mt-12 bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4 text-center">🌡️ 시장 온도계</h2>
            <WeatherGauge rankings={rankings} />
          </div>
        </main>

        {/* 푸터 */}
        <footer className="bg-gray-100 mt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="text-center text-gray-600">
              <p>데이터 출처: KRX, Yahoo Finance | AI 예측은 참고용입니다</p>
              <p className="mt-2">© 2025 Stock Weather Dashboard</p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}

export const getServerSideProps: GetServerSideProps = async () => {
  try {
    const response = await axios.get(`${API_URL}/rankings`, {
      params: { market: 'ALL', limit: 20 }
    });
    
    return {
      props: {
        initialData: response.data
      }
    };
  } catch (error) {
    console.error('Initial data fetch error:', error);
    return {
      props: {
        initialData: null
      }
    };
  }
};
