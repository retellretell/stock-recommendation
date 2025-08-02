import React, { useState } from 'react';
import { useRouter } from 'next/router';
import clsx from 'clsx';
import { StockData, TabType } from '../types/stock';
import { formatUtils } from '../utils/api';
import { AccessibleColors } from '../utils/accessibility';

interface StockWeatherCardProps {
  stock: StockData;
  rank: number;
  type: TabType;
  colorScheme?: 'default' | 'colorblind' | 'high_contrast';
  reduceMotion?: boolean;
}

export default function AccessibleStockCard({ 
  stock, 
  rank, 
  type,
  colorScheme = 'default',
  reduceMotion = false 
}: StockWeatherCardProps) {
  const router = useRouter();
  const [isFocused, setIsFocused] = useState(false);
  const isGainer = type === 'gainers';
  
  // 신뢰도를 별 개수로 변환
  const starCount = Math.round(stock.confidence * 5);
  
  // 색상 스키마 선택
  const colors = colorScheme === 'colorblind' ? AccessibleColors : {
    positive: { primary: '#3B82F6', secondary: '#10B981', text: '#1E40AF' },
    negative: { primary: '#EF4444', secondary: '#F97316', text: '#991B1B' },
    neutral: { primary: '#6B7280', secondary: '#9CA3AF', text: '#374151' }
  };
  
  // 카드 스타일 (색맹 모드 대응)
  const cardStyles = clsx(
    'bg-white rounded-xl shadow-lg p-6 cursor-pointer',
    reduceMotion ? '' : 'transition-all duration-300',
    !reduceMotion && 'hover:shadow-xl hover:-translate-y-1',
    isFocused && 'ring-4 ring-blue-500 ring-opacity-50',
    isGainer ? 'border-t-4' : 'border-t-4'
  );
  
  const borderColor = isGainer ? colors.positive.primary : colors.negative.primary;
  
  // 패턴 오버레이 (색상 외 구분)
  const patternOverlay = colorScheme === 'colorblind' ? (
    <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ opacity: 0.1 }}>
      <defs>
        <pattern id={`pattern-${stock.ticker}`} x="0" y="0" width="10" height="10" patternUnits="userSpaceOnUse">
          {isGainer ? (
            <path d="M 0,10 L 10,0" stroke={borderColor} strokeWidth="0.5"/>
          ) : (
            <path d="M 0,0 L 10,10" stroke={borderColor} strokeWidth="0.5"/>
          )}
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#pattern-${stock.ticker})`} />
    </svg>
  ) : null;
  
  return (
    <article
      role="article"
      aria-label={`${rank}위 ${stock.name}, 상승 확률 ${(stock.probability * 100).toFixed(0)}퍼센트`}
      className={cardStyles}
      style={{ borderTopColor: borderColor }}
      onClick={() => router.push(`/detail/${stock.ticker}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          router.push(`/detail/${stock.ticker}`);
        }
      }}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      tabIndex={0}
    >
      {/* 패턴 오버레이 */}
      {patternOverlay}
      
      {/* 숨겨진 상태 정보 (스크린 리더용) */}
      <span className="sr-only">
        {stock.accessibility_label || `${stock.name} 종목, 현재 ${rank}위. 
        상승 확률 ${(stock.probability * 100).toFixed(1)}퍼센트. 
        예상 수익률 ${stock.expected_return > 0 ? '플러스' : '마이너스'} 
        ${Math.abs(stock.expected_return).toFixed(2)}퍼센트. 
        신뢰도 5점 만점에 ${(stock.confidence * 5).toFixed(1)}점.`}
      </span>
      
      {/* 순위 배지 */}
      <div className="flex justify-between items-start mb-4">
        <span 
          className={clsx(
            'inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold',
            rank <= 3 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
          )}
          aria-label={`순위: ${rank}위`}
        >
          {rank}
        </span>
        <div className="flex items-center space-x-2">
          <span 
            className={clsx('text-3xl', !reduceMotion && 'animate-pulse-slow')}
            role="img" 
            aria-label={isGainer ? '맑음 날씨' : '비 날씨'}
          >
            {stock.weather_icon}
          </span>
          {/* 텍스트 레이블 추가 (접근성) */}
          {colorScheme === 'high_contrast' && (
            <span className="text-sm font-medium">
              {isGainer ? '상승' : '하락'}
            </span>
          )}
        </div>
      </div>

      {/* 종목 정보 */}
      <h3 className="font-bold text-lg mb-1 line-clamp-1" title={stock.name}>
        {stock.name}
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        <span className="font-medium">{stock.ticker}</span>
        <span className="mx-2">·</span>
        <span>{stock.sector}</span>
      </p>

      {/* 확률 표시 */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-gray-600">상승 확률</span>
          <span 
            className={clsx(
              'font-bold',
              stock.probability >= 0.6 ? 'text-blue-600' : 'text-gray-600'
            )}
            style={{ color: stock.probability >= 0.6 ? colors.positive.text : colors.neutral.text }}
          >
            {formatUtils.formatNumber(stock.probability * 100, 1)}%
          </span>
        </div>
        <div className="relative w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className={clsx(
              'h-2 rounded-full',
              !reduceMotion && 'transition-all duration-500'
            )}
            style={{ 
              width: `${stock.probability * 100}%`,
              backgroundColor: stock.probability >= 0.5 ? colors.positive.primary : colors.negative.primary
            }}
            role="progressbar"
            aria-valuenow={stock.probability * 100}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`상승 확률 ${(stock.probability * 100).toFixed(0)}%`}
          />
          {/* 시각적 구분을 위한 텍스트 오버레이 */}
          {colorScheme === 'high_contrast' && (
            <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">
              {(stock.probability * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      {/* 예상 수익률 */}
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-gray-600">예상 수익률</span>
        <span 
          className={clsx(
            'font-bold',
            stock.expected_return > 0 ? 'text-green-600' : 'text-red-600'
          )}
          style={{ 
            color: stock.expected_return > 0 ? colors.positive.secondary : colors.negative.primary 
          }}
          aria-label={`예상 수익률 ${stock.expected_return > 0 ? '플러스' : '마이너스'} ${Math.abs(stock.expected_return).toFixed(2)}퍼센트`}
        >
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
              role="progressbar"
              aria-valuenow={stock.fundamental_score * 100}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`펀더멘털 점수 ${(stock.fundamental_score * 100).toFixed(0)}점`}
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
            {/* 별점 */}
            <div role="img" aria-label={`신뢰도 5점 만점에 ${starCount}점`}>
              {[1, 2, 3, 4, 5].map((star) => (
                <svg
                  key={star}
                  className={clsx(
                    'inline-block w-3 h-3',
                    !reduceMotion && 'transition-colors',
                    star <= starCount ? 'text-yellow-400' : 'text-gray-300'
                  )}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-hidden="true"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </div>
            <span className="ml-1 text-xs text-gray-500">
              ({formatUtils.formatNumber(stock.confidence * 100, 0)}%)
            </span>
          </div>
        </div>
      </div>
      
      {/* 소셜 감성 (있는 경우) */}
      {stock.social_sentiment !== undefined && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">소셜 감성</span>
            <div className="flex items-center">
              <div className="w-12 bg-gray-200 rounded-full h-1 mr-2">
                <div
                  className="bg-purple-500 h-1 rounded-full"
                  style={{ width: `${stock.social_sentiment * 100}%` }}
                  role="progressbar"
                  aria-valuenow={stock.social_sentiment * 100}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`소셜 감성 ${(stock.social_sentiment * 100).toFixed(0)}% 긍정적`}
                />
              </div>
              <span className="text-xs text-gray-500">
                {formatUtils.formatNumber(stock.social_sentiment * 100, 0)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
