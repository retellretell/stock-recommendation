import React, { useEffect, useState } from 'react';
import axios from 'axios';
import clsx from 'clsx';

interface SectorWeather {
  sector: string;
  probability: number;
  weather_icon: string;
  weather_desc: string;
  stock_count: number;
  top_stock: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function SectorWeatherMap() {
  const [sectors, setSectors] = useState<SectorWeather[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSectorData();
  }, []);

  const fetchSectorData = async () => {
    try {
      const response = await axios.get(`${API_URL}/sectors`);
      setSectors(response.data.sectors);
    } catch (error) {
      console.error('섹터 데이터 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="animate-pulse">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const getSectorColor = (probability: number) => {
    if (probability >= 0.7) return 'from-yellow-100 to-yellow-200 border-yellow-400';
    if (probability >= 0.6) return 'from-green-100 to-green-200 border-green-400';
    if (probability >= 0.4) return 'from-gray-100 to-gray-200 border-gray-400';
    if (probability >= 0.3) return 'from-blue-100 to-blue-200 border-blue-400';
    return 'from-indigo-100 to-indigo-200 border-indigo-400';
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {sectors.map((sector) => (
          <div
            key={sector.sector}
            className={clsx(
              'relative p-4 rounded-lg border-2 bg-gradient-to-br cursor-pointer transition-all hover:scale-105',
              getSectorColor(sector.probability)
            )}
          >
            <div className="flex justify-between items-start mb-2">
              <h4 className="font-semibold text-sm">{sector.sector}</h4>
              <span className="text-2xl">{sector.weather_icon}</span>
            </div>
            <p className="text-xs text-gray-600 mb-1">{sector.stock_count}개 종목</p>
            <p className="text-lg font-bold">{(sector.probability * 100).toFixed(0)}°</p>
            <p className="text-xs text-gray-700 mt-1 line-clamp-1">
              대표: {sector.top_stock}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
