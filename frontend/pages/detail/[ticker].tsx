import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';
import axios from 'axios';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { format } from 'date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface DetailedStock {
  ticker: string;
  name: string;
  sector: string;
  current_price: number;
  probability: number;
  expected_return: number;
  fundamental_breakdown: {
    [key: string]: {
      raw_value: number;
      normalized: number;
      weight: number;
      contribution: number;
    };
  };
  price_history: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  news_sentiment?: number;
  technical_indicators: {
    ma20: number;
    ma60: number;
    rsi: number;
    volatility: number;
  };
  last_updated: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function StockDetail() {
  const router = useRouter();
  const { ticker } = router.query;
  const [stock, setStock] = useState<DetailedStock | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (ticker) {
      fetchStockDetail();
    }
  }, [ticker]);

  const fetchStockDetail = async () => {
    try {
      const response = await axios.get(`${API_URL}/detail/${ticker}`);
      setStock(response.data);
    } catch (error) {
      console.error('상세 정보 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!stock) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-gray-600">종목을 찾을 수 없습니다</p>
          <Link href="/" className="text-blue-500 hover:underline mt-4 block">
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  // 차트 데이터 준비
  const chartData = {
    labels: stock.price_history.map(p => format(new Date(p.date), 'MM/dd')),
    datasets: [
      {
        label: '종가',
        data: stock.price_history.map(p => p.close),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.1)',
        tension: 0.1,
        fill: true
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '주가 추이 (120일)'
      }
    },
    scales: {
      y: {
        beginAtZero: false
      }
    }
  };

  const getWeatherIcon = (probability: number) => {
    if (probability >= 0.7) return "☀️";
    if (probability >= 0.6) return "🌤️";
    if (probability >= 0.4) return "⛅";
    if (probability >= 0.3) return "🌥️";
    return "🌧️";
  };

  const getWeatherDescription = (probability: number) => {
    if (probability >= 0.7) return "맑고 화창한 상승세";
    if (probability >= 0.6) return "대체로 맑은 날씨";
    if (probability >= 0.4) return "변동성 있는 구름";
    if (probability >= 0.3) return "흐린 조정 가능성";
    return "비 오는 하락세";
  };

  return (
    <>
      <Head>
        <title>{stock.name} ({stock.ticker}) - 주식 날씨 예보</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* 헤더 */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <Link href="/" className="flex items-center text-gray-600 hover:text-gray-900">
                <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                돌아가기
              </Link>
              <h1 className="text-xl font-semibold">{stock.name}</h1>
            </div>
          </div>
        </header>

        {/* 메인 컨텐츠 */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 종목 개요 */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-3xl font-bold">{stock.name}</h2>
                <p className="text-gray-600">{stock.ticker} · {stock.sector}</p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold">₩{stock.current_price.toLocaleString()}</p>
                <p className="text-sm text-gray-600">현재가</p>
              </div>
            </div>

            {/* 날씨 예보 */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 mt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-lg font-semibold mb-2">오늘의 날씨 예보</p>
                  <p className="text-3xl mb-2">{getWeatherIcon(stock.probability)}</p>
                  <p className="text-gray-700">{getWeatherDescription(stock.probability)}</p>
                </div>
                <div className="text-right">
                  <p className="text-4xl font-bold text-blue-600">
                    {(stock.probability * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm text-gray-600">상승 확률</p>
                  <p className="text-2xl font-semibold mt-2 text-green-600">
                    {stock.expected_return > 0 ? '+' : ''}{stock.expected_return.toFixed(2)}%
                  </p>
                  <p className="text-sm text-gray-600">예상 수익률</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 주가 차트 */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-semibold mb-4">주가 차트</h3>
              <Line data={chartData} options={chartOptions} />
            </div>

            {/* 펀더멘털 분석 */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-semibold mb-4">펀더멘털 분석</h3>
              <div className="space-y-4">
                {Object.entries(stock.fundamental_breakdown).map(([key, value]) => (
                  <div key={key}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-gray-700">{key}</span>
                      <span className="font-semibold">{value.raw_value.toFixed(2)}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${value.normalized * 100}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      기여도: {(value.contribution * 100).toFixed(1)}%
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 기술적 지표 */}
          <div className="bg-white rounded-xl shadow-lg p-6 mt-6">
            <h3 className="text-xl font-semibold mb-4">기술적 지표</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">
                  ₩{stock.technical_indicators.ma20.toLocaleString()}
                </p>
                <p className="text-sm text-gray-600">20일 이동평균</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">
                  ₩{stock.technical_indicators.ma60.toLocaleString()}
                </p>
                <p className="text-sm text-gray-600">60일 이동평균</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-600">
                  {stock.technical_indicators.rsi.toFixed(1)}
                </p>
                <p className="text-sm text-gray-600">RSI</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-600">
                  {stock.technical_indicators.volatility.toFixed(1)}%
                </p>
                <p className="text-sm text-gray-600">변동성</p>
              </div>
            </div>
          </div>

          {/* 뉴스 감성 (한국 주식만) */}
          {stock.news_sentiment !== undefined && (
            <div className="bg-white rounded-xl shadow-lg p-6 mt-6">
              <h3 className="text-xl font-semibold mb-4">뉴스 감성 분석</h3>
              <div className="flex items-center">
                <div className="flex-1">
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full ${
                        stock.news_sentiment > 0 ? 'bg-green-500' : 'bg-red-500'
                      }`}
                      style={{
                        width: `${Math.abs(stock.news_sentiment) * 50 + 50}%`,
                        marginLeft: stock.news_sentiment < 0 ? `${50 - Math.abs(stock.news_sentiment) * 50}%` : '0'
                      }}
                    ></div>
                  </div>
                </div>
                <span className="ml-4 font-semibold">
                  {stock.news_sentiment > 0 ? '긍정적' : '부정적'} 
                  ({(Math.abs(stock.news_sentiment) * 100).toFixed(0)}%)
                </span>
              </div>
            </div>
          )}
        </main>
      </div>
    </>
  );
}
