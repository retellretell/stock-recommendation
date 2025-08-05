import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import axios from 'axios';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PerformanceData {
  prediction_performance: {
    summary: {
      total_predictions: number;
      accuracy_rate: number;
      avg_confidence: number;
    };
    confidence_analysis: Array<{
      confidence_level: string;
      predictions: number;
      accuracy: number;
    }>;
  };
  trading_performance: {
    portfolio_performance: {
      period_return: number;
      annualized_return: number;
    };
    win_statistics: {
      win_rate: number;
      profit_factor: number;
    };
    daily_returns: Array<{
      date: string;
      total_value: number;
      daily_return: number;
    }>;
  };
  risk_metrics: {
    volatility: number;
    max_drawdown: number;
    sharpe_ratio: number;
    sortino_ratio: number;
  };
  insights: Array<{
    type: string;
    category: string;
    message: string;
  }>;
}

export default function PerformanceDashboard() {
  const [performanceData, setPerformanceData] = useState<PerformanceData | null>(null);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('7');

  useEffect(() => {
    fetchData();
  }, [selectedPeriod]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // 성과 리포트
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - parseInt(selectedPeriod));

      const [reportRes, portfolioRes] = await Promise.all([
        axios.get(`${API_URL}/api/backtest/performance/report`, {
          params: {
            start_date: startDate.toISOString(),
            end_date: endDate.toISOString()
          }
        }),
        axios.get(`${API_URL}/api/backtest/portfolio`)
      ]);

      setPerformanceData(reportRes.data);
      setPortfolio(portfolioRes.data);
    } catch (error) {
      console.error('데이터 로드 실패:', error);
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

  // 차트 데이터 준비
  const dailyReturnsChart = {
    labels: performanceData?.trading_performance.daily_returns.map(d => 
      format(new Date(d.date), 'MM/dd')
    ) || [],
    datasets: [{
      label: '포트폴리오 가치',
      data: performanceData?.trading_performance.daily_returns.map(d => d.total_value) || [],
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.1)',
      tension: 0.1,
      fill: true
    }]
  };

  const confidenceChart = {
    labels: performanceData?.prediction_performance.confidence_analysis.map(c => 
      c.confidence_level
    ) || [],
    datasets: [{
      label: '예측 정확도',
      data: performanceData?.prediction_performance.confidence_analysis.map(c => 
        c.accuracy * 100
      ) || [],
      backgroundColor: 'rgba(53, 162, 235, 0.8)'
    }]
  };

  return (
    <>
      <Head>
        <title>백테스팅 성과 - 주식 날씨 예보판</title>
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* 헤더 */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <Link href="/" className="flex items-center text-gray-600 hover:text-gray-900">
                  <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  메인으로
                </Link>
                <h1 className="ml-4 text-xl font-semibold">백테스팅 성과 대시보드</h1>
              </div>
              
              {/* 기간 선택 */}
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                className="px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="7">최근 7일</option>
                <option value="30">최근 30일</option>
                <option value="90">최근 90일</option>
              </select>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 핵심 지표 카드 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600">예측 정확도</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">
                {(performanceData?.prediction_performance.summary.accuracy_rate * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {performanceData?.prediction_performance.summary.total_predictions}개 예측
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600">수익률</p>
              <p className={`text-3xl font-bold mt-2 ${
                performanceData?.trading_performance.portfolio_performance.period_return >= 0 
                  ? 'text-green-600' : 'text-red-600'
              }`}>
                {performanceData?.trading_performance.portfolio_performance.period_return >= 0 ? '+' : ''}
                {performanceData?.trading_performance.portfolio_performance.period_return.toFixed(2)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                연율화: {performanceData?.trading_performance.portfolio_performance.annualized_return.toFixed(1)}%
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600">승률</p>
              <p className="text-3xl font-bold text-purple-600 mt-2">
                {(performanceData?.trading_performance.win_statistics.win_rate * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                PF: {performanceData?.trading_performance.win_statistics.profit_factor.toFixed(2)}
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-600">샤프 비율</p>
              <p className="text-3xl font-bold text-indigo-600 mt-2">
                {performanceData?.risk_metrics.sharpe_ratio.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                MDD: {performanceData?.risk_metrics.max_drawdown.toFixed(1)}%
              </p>
            </div>
          </div>

          {/* 차트 섹션 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">포트폴리오 가치 추이</h3>
              <Line data={dailyReturnsChart} options={{
                responsive: true,
                plugins: {
                  legend: { display: false }
                }
              }} />
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">신뢰도별 정확도</h3>
              <Bar data={confidenceChart} options={{
                responsive: true,
                plugins: {
                  legend: { display: false }
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    max: 100
                  }
                }
              }} />
            </div>
          </div>

          {/* 현재 포트폴리오 */}
          {portfolio && (
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-lg font-semibold mb-4">현재 포트폴리오</h3>
              <div className="mb-4">
                <p className="text-sm text-gray-600">
                  현금: ₩{portfolio.cash.toLocaleString()} | 
                  총 가치: ₩{portfolio.total_value.toLocaleString()}
                </p>
              </div>
              
              {portfolio.positions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">종목</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">수량</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">평균가</th>
                        <th className="px
