"""
커스텀 예외 클래스
"""

class StockWeatherException(Exception):
    """기본 예외 클래스"""
    pass

class APIError(StockWeatherException):
    """API 관련 에러"""
    pass

class DataValidationError(StockWeatherException):
    """데이터 검증 에러"""
    pass

class BatchProcessingError(StockWeatherException):
    """배치 처리 에러"""
    pass

class CacheError(StockWeatherException):
    """캐시 관련 에러"""
    pass

class ModelError(StockWeatherException):
    """ML 모델 관련 에러"""
    pass
