"""
가상 거래 (Paper Trading) 시스템
"""
import aiosqlite
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog
import asyncio

from .models import PaperTrade, Portfolio, TradingAction, BacktestConfig
from .tracker import PredictionTracker

logger = structlog.get_logger()

class PaperTradingEngine:
    """가상 거래 엔진"""
    
    def __init__(self, 
                 db_path: str = "backtesting.db",
                 config: Optional[BacktestConfig] = None):
        self.db_path = db_path
        self.config = config or BacktestConfig()
        self.tracker = PredictionTracker(db_path)
        self._initialized = False
        
        # 현재 포트폴리오 상태
        self.portfolio = Portfolio(
            cash=self.config.initial_capital,
            positions={},
            total_value=self.config.initial_capital,
            initial_capital=self.config.initial_capital,
            total_return=0,
            total_return_pct=0,
            max_drawdown=0,
            sharpe_ratio=0,
            win_rate=0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=0,
            avg_loss=0,
            last_updated=datetime.now()
        )
        
    async def initialize(self):
        """데이터베이스 초기화"""
        async with aiosqlite.connect(self.db_path) as db:
            # 거래 테이블
            await db.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER,
                    ticker TEXT NOT NULL,
                    action TEXT NOT NULL,
                    trade_date TIMESTAMP NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    total_value REAL NOT NULL,
                    
                    position_before INTEGER,
                    position_after INTEGER,
                    cash_before REAL,
                    cash_after REAL,
                    
                    realized_pnl REAL DEFAULT 0,
                    unrealized_pnl REAL DEFAULT 0,
                    commission REAL DEFAULT 0,
                    
                    closed_date TIMESTAMP,
                    closed_price REAL,
                    final_pnl REAL,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
                )
            """)
            
            # 포트폴리오 상태 테이블
            await db.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TIMESTAMP NOT NULL,
                    cash REAL NOT NULL,
                    positions TEXT NOT NULL,
                    total_value REAL NOT NULL,
                    daily_return REAL,
                    cumulative_return REAL,
                    drawdown REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_date 
                ON paper_trades(trade_date)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_ticker 
                ON paper_trades(ticker)
            """)
            
            await db.commit()
            
        # 포트폴리오 복원
        await self._restore_portfolio()
        
        self._initialized = True
        logger.info("paper_trading_initialized", 
                   initial_capital=self.config.initial_capital)
    
    async def process_prediction(self, 
                               ticker: str, 
                               prediction: Dict,
                               current_price: float) -> Optional[PaperTrade]:
        """예측 기반 거래 결정"""
        if not self._initialized:
            await self.initialize()
            
        # 거래 신호 결정
        action = self._determine_action(ticker, prediction)
        
        if action == TradingAction.HOLD:
            return None
            
        # 거래 수량 결정
        quantity = self._calculate_quantity(ticker, current_price, action)
        
        if quantity == 0:
            return None
            
        # 거래 실행
        trade = await self._execute_trade(
            ticker=ticker,
            action=action,
            price=current_price,
            quantity=quantity,
            prediction_id=prediction.get('id')
        )
        
        return trade
    
    def _determine_action(self, ticker: str, prediction: Dict) -> TradingAction:
        """거래 액션 결정"""
        probability = prediction['probability']
        confidence = prediction.get('confidence', 0.5)
        current_position = self.portfolio.positions.get(ticker, {}).get('quantity', 0)
        
        # 신뢰도 임계값 체크
        if confidence < self.config.confidence_threshold:
            return TradingAction.HOLD
            
        # 매수 신호
        if probability > 0.65 and current_position == 0:
            return TradingAction.BUY
            
        # 매도 신호
        if probability < 0.35 and current_position > 0:
            return TradingAction.SELL
            
        # 손절/익절 체크
        if current_position > 0:
            position_info = self.portfolio.positions[ticker]
            avg_price = position_info['avg_price']
            current_price = position_info.get('current_price', avg_price)
            
            pnl_pct = (current_price - avg_price) / avg_price
            
            # 손절
            if pnl_pct < -self.config.stop_loss:
                return TradingAction.SELL
                
            # 익절
            if pnl_pct > self.config.take_profit:
                return TradingAction.SELL
                
        return TradingAction.HOLD
    
    def _calculate_quantity(self, ticker: str, price: float, action: TradingAction) -> int:
        """거래 수량 계산"""
        if action == TradingAction.BUY:
            # 포지션 크기 제한
            max_position_value = self.portfolio.total_value * self.config.max_position_size
            available_cash = self.portfolio.cash * 0.95  # 여유 자금 5%
            
            max_value = min(max_position_value, available_cash)
            
            # 최소 거래 금액 체크
            if max_value < self.config.min_trade_value:
                return 0
                
            quantity = int(max_value / price)
            return quantity
            
        elif action == TradingAction.SELL:
            # 전량 매도
            return self.portfolio.positions.get(ticker, {}).get('quantity', 0)
            
        return 0
    
    async def _execute_trade(self,
                           ticker: str,
                           action: TradingAction,
                           price: float,
                           quantity: int,
                           prediction_id: Optional[int] = None) -> PaperTrade:
        """거래 실행"""
        # 거래 전 상태
        position_before = self.portfolio.positions.get(ticker, {}).get('quantity', 0)
        cash_before = self.portfolio.cash
        
        # 수수료 계산
        trade_value = price * quantity
        commission = trade_value * self.config.commission_rate
        
        # 거래 처리
        if action == TradingAction.BUY:
            total_cost = trade_value + commission
            if total_cost > self.portfolio.cash:
                raise ValueError("Insufficient cash")
                
            self.portfolio.cash -= total_cost
            
            # 포지션 업데이트
            if ticker not in self.portfolio.positions:
                self.portfolio.positions[ticker] = {
                    'quantity': 0,
                    'avg_price': 0,
                    'total_cost': 0
                }
                
            position = self.portfolio.positions[ticker]
            new_quantity = position['quantity'] + quantity
            new_total_cost = position['total_cost'] + trade_value
            
            position['quantity'] = new_quantity
            position['avg_price'] = new_total_cost / new_quantity
            position['total_cost'] = new_total_cost
            position['current_price'] = price
            
        else:  # SELL
            if position_before < quantity:
                raise ValueError("Insufficient shares")
                
            position = self.portfolio.positions[ticker]
            avg_price = position['avg_price']
            
            # 실현 손익 계산
            realized_pnl = (price - avg_price) * quantity - commission
            
            # 세금 (수익에 대해서만)
            if realized_pnl > 0:
                tax = trade_value * self.config.tax_rate
                realized_pnl -= tax
                commission += tax
                
            self.portfolio.cash += trade_value - commission
            
            # 포지션 업데이트
            position['quantity'] -= quantity
            if position['quantity'] == 0:
                del self.portfolio.positions[ticker]
            else:
                position['current_price'] = price
        
        # 거래 기록 생성
        trade = PaperTrade(
            prediction_id=prediction_id,
            ticker=ticker,
            action=action,
            trade_date=datetime.now(),
            price=price,
            quantity=quantity,
            total_value=trade_value,
            position_before=position_before,
            position_after=self.portfolio.positions.get(ticker, {}).get('quantity', 0),
            cash_before=cash_before,
            cash_after=self.portfolio.cash,
            realized_pnl=realized_pnl if action == TradingAction.SELL else 0,
            commission=commission
        )
        
        # DB 저장
        await self._save_trade(trade)
        
        # 포트폴리오 통계 업데이트
        await self._update_portfolio_stats()
        
        logger.info("trade_executed",
                   ticker=ticker,
                   action=action.value,
                   quantity=quantity,
                   price=price)
        
        return trade
    
    async def _save_trade(self, trade: PaperTrade):
        """거래 기록 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO paper_trades (
                    prediction_id, ticker, action, trade_date, price, quantity,
                    total_value, position_before, position_after,
                    cash_before, cash_after, realized_pnl, commission
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.prediction_id,
                trade.ticker,
                trade.action.value,
                trade.trade_date.isoformat(),
                trade.price,
                trade.quantity,
                trade.total_value,
                trade.position_before,
                trade.position_after,
                trade.cash_before,
                trade.cash_after,
                trade.realized_pnl,
                trade.commission
            ))
            
            await db.commit()
    
    async def update_portfolio_values(self, current_prices: Dict[str, float]):
        """포트폴리오 현재가 업데이트"""
        # 포지션 현재가 업데이트
        for ticker, position in self.portfolio.positions.items():
            if ticker in current_prices:
                position['current_price'] = current_prices[ticker]
                position['unrealized_pnl'] = (
                    (current_prices[ticker] - position['avg_price']) * position['quantity']
                )
        
        # 포트폴리오 총 가치 계산
        positions_value = sum(
            pos['quantity'] * pos.get('current_price', pos['avg_price'])
            for pos in self.portfolio.positions.values()
        )
        
        self.portfolio.total_value = self.portfolio.cash + positions_value
        self.portfolio.total_return = self.portfolio.total_value - self.portfolio.initial_capital
        self.portfolio.total_return_pct = (
            self.portfolio.total_return / self.portfolio.initial_capital * 100
        )
        
        # 일일 스냅샷 저장
        await self._save_portfolio_snapshot()
    
    async def _save_portfolio_snapshot(self):
        """포트폴리오 스냅샷 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            # 이전 스냅샷 조회
            cursor = await db.execute("""
                SELECT total_value FROM portfolio_history
                ORDER BY date DESC LIMIT 1
            """)
            row = await cursor.fetchone()
            
            prev_value = row[0] if row else self.portfolio.initial_capital
            daily_return = (self.portfolio.total_value - prev_value) / prev_value * 100
            
            # 최대 낙폭 계산
            cursor = await db.execute("""
                SELECT MAX(total_value) FROM portfolio_history
            """)
            row = await cursor.fetchone()
            peak_value = row[0] if row and row[0] else self.portfolio.total_value
            
            drawdown = (self.portfolio.total_value - peak_value) / peak_value * 100
            self.portfolio.max_drawdown = min(self.portfolio.max_drawdown, drawdown)
            
            # 스냅샷 저장
            await db.execute("""
                INSERT INTO portfolio_history (
                    date, cash, positions, total_value,
                    daily_return, cumulative_return, drawdown
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                self.portfolio.cash,
                json.dumps(self.portfolio.positions),
                self.portfolio.total_value,
                daily_return,
                self.portfolio.total_return_pct,
                drawdown
            ))
            
            await db.commit()
    
    async def _update_portfolio_stats(self):
        """포트폴리오 통계 업데이트"""
        async with aiosqlite.connect(self.db_path) as db:
            # 전체 거래 통계
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE NULL END) as avg_win,
                    AVG(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE NULL END) as avg_loss
                FROM paper_trades
                WHERE action = 'sell'
            """)
            
            stats = await cursor.fetchone()
            
            self.portfolio.total_trades = stats[0] or 0
            self.portfolio.winning_trades = stats[1] or 0
            self.portfolio.losing_trades = stats[2] or 0
            self.portfolio.avg_win = stats[3] or 0
            self.portfolio.avg_loss = stats[4] or 0
            
            if self.portfolio.total_trades > 0:
                self.portfolio.win_rate = self.portfolio.winning_trades / self.portfolio.total_trades
            
            # 샤프 비율 계산 (간단한 버전)
            cursor = await db.execute("""
                SELECT daily_return FROM portfolio_history
                WHERE daily_return IS NOT NULL
                ORDER BY date DESC LIMIT 252
            """)
            
            returns = [row[0] for row in await cursor.fetchall()]
            
            if len(returns) > 30:
                import numpy as np
                returns_array = np.array(returns)
                
                # 연율화된 샤프 비율
                excess_returns = returns_array - (self.config.commission_rate * 100)  # 간단히 처리
                self.portfolio.sharpe_ratio = (
                    np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
                    if np.std(excess_returns) > 0 else 0
                )
            
            self.portfolio.last_updated = datetime.now()
    
    async def _restore_portfolio(self):
        """포트폴리오 상태 복원"""
        async with aiosqlite.connect(self.db_path) as db:
            # 최신 스냅샷에서 복원
            cursor = await db.execute("""
                SELECT cash, positions, total_value
                FROM portfolio_history
                ORDER BY date DESC LIMIT 1
            """)
            
            row = await cursor.fetchone()
            if row:
                self.portfolio.cash = row[0]
                self.portfolio.positions = json.loads(row[1])
                self.portfolio.total_value = row[2]
                
                logger.info("portfolio_restored", 
                          cash=self.portfolio.cash,
                          positions_count=len(self.portfolio.positions))
    
    async def close_position(self, ticker: str, reason: str = "manual"):
        """포지션 청산"""
        if ticker not in self.portfolio.positions:
            return None
            
        position = self.portfolio.positions[ticker]
        current_price = position.get('current_price', position['avg_price'])
        
        trade = await self._execute_trade(
            ticker=ticker,
            action=TradingAction.SELL,
            price=current_price,
            quantity=position['quantity']
        )
        
        logger.info("position_closed", ticker=ticker, reason=reason)
        
        return trade
    
    async def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약"""
        return {
            'cash': self.portfolio.cash,
            'positions': [
                {
                    'ticker': ticker,
                    'quantity': pos['quantity'],
                    'avg_price': pos['avg_price'],
                    'current_price': pos.get('current_price', pos['avg_price']),
                    'unrealized_pnl': pos.get('unrealized_pnl', 0),
                    'pnl_pct': (
                        (pos.get('current_price', pos['avg_price']) - pos['avg_price']) 
                        / pos['avg_price'] * 100
                    )
                }
                for ticker, pos in self.portfolio.positions.items()
            ],
            'total_value': self.portfolio.total_value,
            'total_return': self.portfolio.total_return,
            'total_return_pct': self.portfolio.total_return_pct,
            'win_rate': self.portfolio.win_rate,
            'sharpe_ratio': self.portfolio.sharpe_ratio,
            'max_drawdown': self.portfolio.max_drawdown
        }
