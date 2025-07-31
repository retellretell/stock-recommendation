import React from 'react';

interface WeatherGaugeProps {
  rankings: {
    top_gainers: any[];
    top_losers: any[];
  } | null;
}

export default function WeatherGauge({ rankings }: WeatherGaugeProps) {
  if (!rankings) return null;

  // 전체 시장 온도 계산
  const totalStocks = rankings.top_gainers.length + rankings.top_losers.length;
  const avgProbability = (
    rankings.top_gainers.reduce((sum, s) => sum + s.probability, 0) +
    rankings.top_losers.reduce((sum, s) => sum + s.probability, 0)
  ) / totalStocks;

  const temperature = Math.round(avgProbability * 100);
  const rotation = (temperature - 50) * 1.8; // -90 ~ +90도

  const getTemperatureColor = (temp: number) => {
    if (temp >= 70) return 'text-red-600';
    if (temp >= 60) return 'text-orange-500';
    if (temp >= 40) return 'text-yellow-500';
    if (temp >= 30) return 'text-blue-500';
    return 'text-blue-700';
  };

  const getMarketStatus = (temp: number) => {
    if (temp >= 70) return '과열 주의';
    if (temp >= 60) return '강세 시장';
    if (temp >= 40) return '중립 시장';
    if (temp >= 30) return '약세 시장';
    return '극도의 약세';
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-48 h-48">
        {/* 게이지 배경 */}
        <svg className="w-full h-full" viewBox="0 0 200 200">
          <path
            d="M 50 150 A 80 80 0 0 1 150 150"
            fill="none"
            stroke="#e5e7
          stroke="#e5e7eb"
            strokeWidth="20"
          />
          {/* 색상 구간 */}
          <path
            d="M 50 150 A 80 80 0 0 1 70 90"
            fill="none"
            stroke="#3b82f6"
            strokeWidth="20"
          />
          <path
            d="M 70 90 A 80 80 0 0 1 100 70"
            fill="none"
            stroke="#eab308"
            strokeWidth="20"
          />
          <path
            d="M 100 70 A 80 80 0 0 1 130 90"
            fill="none"
            stroke="#f97316"
            strokeWidth="20"
          />
          <path
            d="M 130 90 A 80 80 0 0 1 150 150"
            fill="none"
            stroke="#ef4444"
            strokeWidth="20"
          />
        </svg>

        {/* 바늘 */}
        <div
          className="absolute top-1/2 left-1/2 w-1 h-20 bg-gray-800 origin-bottom"
          style={{
            transform: `translate(-50%, -100%) rotate(${rotation}deg)`,
            transition: 'transform 1s ease-out'
          }}
        >
          <div className="w-3 h-3 bg-gray-800 rounded-full absolute -top-1 -left-1"></div>
        </div>

        {/* 중심점 */}
        <div className="absolute top-1/2 left-1/2 w-4 h-4 bg-gray-800 rounded-full transform -translate-x-1/2 -translate-y-1/2"></div>
      </div>

      {/* 온도 표시 */}
      <div className="text-center mt-4">
        <p className={`text-5xl font-bold ${getTemperatureColor(temperature)}`}>
          {temperature}°
        </p>
        <p className="text-lg font-semibold text-gray-700 mt-2">
          {getMarketStatus(temperature)}
        </p>
      </div>

      {/* 범례 */}
      <div className="flex justify-around w-full mt-6 text-sm">
        <div className="text-center">
          <div className="w-4 h-4 bg-blue-500 rounded-full mx-auto mb-1"></div>
          <span className="text-gray-600">약세</span>
        </div>
        <div className="text-center">
          <div className="w-4 h-4 bg-yellow-500 rounded-full mx-auto mb-1"></div>
          <span className="text-gray-600">중립</span>
        </div>
        <div className="text-center">
          <div className="w-4 h-4 bg-orange-500 rounded-full mx-auto mb-1"></div>
          <span className="text-gray-600">강세</span>
        </div>
        <div className="text-center">
          <div className="w-4 h-4 bg-red-500 rounded-full mx-auto mb-1"></div>
          <span className="text-gray-600">과열</span>
        </div>
      </div>
    </div>
  );
}
