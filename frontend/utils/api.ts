/**
 * API 유틸리티 함수
 */
import axios, { AxiosError } from 'axios';
import { 
  RankingsData, 
  DetailedStock, 
  SectorWeather, 
  Market,
  APIError 
} from '../types/stock';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
apiClient.interceptors.request.use(
  (config) => {
    // 로딩 상태 시작
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error: AxiosError<APIError>) => {
    if (error.response) {
      console.error(`API Error: ${error.response.status}`, error.response.data);
      
      // 에러 메시지 처리
      const errorMessage = error.response.data?.detail || '알 수 없는 오류가 발생했습니다.';
      
      // 사용자 친화적 에러 메시지로 변환
      if (error.response.status === 404) {
        throw new Error('요청한 데이터를 찾을 수 없습니다.');
      } else if (error.response.status === 500) {
        throw new Error('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      }
      
      throw new Error(errorMessage);
    } else if (error.request) {
      console.error('API No Response:', error.request);
      throw new Error('서버에 연결할 수 없습니다. 네트워크를 확인해주세요.');
    } else {
      console.error('API Setup Error:', error.message);
      throw new Error('요청 설정 중 오류가 발생했습니다.');
    }
  }
);

// API 함수들
export const api = {
  // 랭킹 조회
  async getRankings(market: Market = 'ALL', limit: number = 20): Promise<RankingsData> {
    const response = await apiClient.get('/rankings', {
      params: { market, limit }
    });
    return response.data;
  },

  // 종목 상세 정보
  async getStockDetail(ticker: string): Promise<DetailedStock> {
    const response = await apiClient.get(`/detail/${ticker}`);
    return response.data;
  },

  // 섹터별 날씨
  async getSectorWeather(): Promise<{ sectors: SectorWeather[]; updated_at: string }> {
    const response = await apiClient.get('/sectors');
    return response.data;
  },

  // 서버 상태 확인
  async checkHealth(): Promise<{
    status: string;
    checks: Record<string, boolean>;
    timestamp: string;
  }> {
    const response = await apiClient.get('/health');
    return response.data;
  }
};

// 날씨 관련 유틸리티
export const weatherUtils = {
  getWeatherIcon(probability: number): string {
    if (probability >= 0.7) return "☀️";
    if (probability >= 0.6) return "🌤️";
    if (probability >= 0.4) return "⛅";
    if (probability >= 0.3) return "🌥️";
    return "🌧️";
  },

  getWeatherDescription(probability: number): string {
    if (probability >= 0.7) return "맑고 화창한 상승세";
    if (probability >= 0.6) return "대체로 맑은 날씨";
    if (probability >= 0.4) return "변동성 있는 구름";
    if (probability >= 0.3) return "흐린 조정 가능성";
    return "비 오는 하락세";
  },

  getTemperatureColor(temp: number): string {
    if (temp >= 70) return 'text-red-600';
    if (temp >= 60) return 'text-orange-500';
    if (temp >= 40) return 'text-yellow-500';
    if (temp >= 30) return 'text-blue-500';
    return 'text-blue-700';
  }
};

// 숫자 포맷팅 유틸리티
export const formatUtils = {
  formatNumber(value: number, decimals: number = 0): string {
    return new Intl.NumberFormat('ko-KR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  },

  formatPercent(value: number, decimals: number = 1): string {
    return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
  },

  formatCurrency(value: number, currency: string = 'KRW'): string {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  }
};
