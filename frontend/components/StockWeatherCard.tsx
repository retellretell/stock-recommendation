import React from 'react';
import clsx from 'clsx';
import { StockData, TabType } from '../types/stock';
import { formatUtils } from '../utils/api';

interface StockWeatherCardProps {
  stock: StockData;
  rank: number;
  type: TabType;
}

export default function StockWeatherCard({ stock, rank, type }: StockWeatherCardProps) {
  const isGainer = type === 'gainers';
  
  // 신뢰도를 별 개수로 변환
  const starCount = Math.round(stock.confidence * 5);
  
  return (
    <div className={clsx(
      'bg-white rounded-xl shadow-lg p-6 cursor-pointer transition-all duration-300',
      'hover:shadow-xl hover:-translate-y-1',
      isGainer ? 'border-t-4 border-blue-500' : 'border-t-4 border-gray-700'
    )}>
      {/* 순위 배지 */}
      <div className="flex justify-between items-start mb-4">
        <span className={clsx(
          'inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold',
          rank <= 3 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
        )}>
          {rank}
        </span>
        <span className="text-3xl animate-pulse-slow">{stock.weather_icon}</span>
      </div>

      {/* 종목 정보 */}
      <h3 className="font-bold text-lg mb-1 line-clamp-1" title={stock.name}>
        {stock.name}
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        {stock.ticker} · {stock.sector}
      </p>

      {/* 확률 표시 */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-gray-600">상승 확률</span>
          <span className={clsx(
            'font-bold',
            stock.probability >= 0.6 ? 'text-blue-600' : 'text-gray-600'
          )}>
            {formatUtils.formatNumber(stock.probability * 100, 1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={clsx(
              'h-2 rounded-full transition-all duration-500',
              stock.probability >= 0.7 ? 'bg-gradient-to-r from-blue-400 to-blue-600' :
              stock.probability >= 0.5 ? 'bg-gradient-to-r from-green-400 to-green-600' :
              stock.probability >= 0.3 ? 'bg-gradient-to-r from-yellow-400 to-yellow-600' : 
              'bg-gradient-to-r from-red-400 to-red-600'
            )}
            style={{ width: `${stock.probability * 100}%` }}
          />
        </div>
      </div>

      {/* 예상 수익률 */}
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-gray-600">예상 수익률</span>
        <span className={clsx(
          'font-bold',
          stock.expected_return > 0 ? 'text-green-600' : 'text-red-600'
        )}>
          {formatUtils.formatPercent(stock.expected_return, 2)}
        </span>
      </div>

      {/* 펀더멘털 스코어 */}
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-gray-600">펀더멘털</span>
        <div className="flex items-center">
          <div className="w-16 bg-gray-200 rounded-full h-1.5 mr-2">
            <div
              className="bg-indigo-500 h-1.5 rounded-full"
              style={{ width: `${stock.fundamental_score * 100}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">
            {formatUtils.formatNumber(stock.fundamental_score * 100, 0)}
          </span>
        </div>
      </div>

      {/* 신뢰도 표시 */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">신뢰도</span>
          <div className="flex items-center space-x-0.5">
            {[1, 2, 3, 4, 5].map((star) => (
              <svg
                key={star}
                className={clsx(
                  'w-3 h-3 transition-colors',
                  star <= starCount ? 'text-yellow-400' : 'text-gray-300'
                )}
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
            <span className="ml-1 text-xs text-gray-500">
              ({formatUtils.formatNumber(stock.confidence * 100, 0)}%)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
