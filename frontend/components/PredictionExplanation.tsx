import React from 'react';
import clsx from 'clsx';

interface PredictionExplanationProps {
  stock: any;
  className?: string;
}

export default function PredictionExplanation({ stock, className = '' }: PredictionExplanationProps) {
  const getRiskBadgeColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getSignalIcon = (direction: string) => {
    switch (direction) {
      case 'BUY': return '📈';
      case 'SELL': return '📉';
      default: return '➡️';
    }
  };

  return (
    <div className={`bg-blue-50 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-blue-900">AI 분석 (베타)</h4>
        <span className={clsx(
          'px-2 py-1 rounded-full text-xs font-medium',
          getRiskBadgeColor(stock.risk_level || 'medium')
        )}>
          리스크: {stock.risk_level || '보통'}
        </span>
      </div>

      {/* 신호 방향 */}
      {stock.signal_direction && (
        <div className="mb-3">
          <span className="text-2xl mr-2">{getSignalIcon(stock.signal_direction)}</span>
          <span className="font-medium">
            {stock.signal_direction === 'BUY' ? '매수 신호' : 
             stock.signal_direction === 'SELL' ? '매도 신호' : '관망'}
          </span>
        </div>
      )}

      {/* 주요 근거 */}
      {stock.top_reasons && stock.top_reasons.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-700">주요 근거:</p>
          <ul className="text-xs text-gray-600 space-y-1">
            {stock.top_reasons.map((reason: string, index: number) => (
              <li key={index} className="flex items-start">
                <span className="text-blue-500 mr-1">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 기술적 지표 요약 */}
      {stock.technical_summary && (
        <div className="mt-3 pt-3 border-t border-blue-100">
          <div className="grid grid-cols-2 gap-2 text-xs">
            {stock.technical_summary.rsi && (
              <div>
                <span className="text-gray-500">RSI:</span>
                <span className={clsx(
                  'ml-1 font-medium',
                  stock.technical_summary.rsi < 30 ? 'text-green-600' :
                  stock.technical_summary.rsi > 70 ? 'text-red-600' : 'text-gray-700'
                )}>
                  {stock.technical_summary.rsi.toFixed(0)}
                </span>
              </div>
            )}
            <div>
              <span className="text-gray-500">추세:</span>
              <span className={clsx(
                'ml-1 font-medium',
                stock.technical_summary.trend === 'bullish' ? 'text-green-600' :
                stock.technical_summary.trend === 'bearish' ? 'text-red-600' : 'text-gray-700'
              )}>
                {stock.technical_summary.trend === 'bullish' ? '상승' :
                 stock.technical_summary.trend === 'bearish' ? '하락' : '횡보'}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="mt-3 text-xs text-blue-700 bg-blue-100 rounded px-2 py-1">
        ℹ️ 규칙 기반 분석입니다. 실제 투자는 신중히 결정하세요.
      </div>
    </div>
  );
}
