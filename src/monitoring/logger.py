"""
日志与监控模块
"""
import json
import os
from typing import Dict, List
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from src.utils.logger import log


class TradingLogger:
    """交易日志记录器"""
    
    def __init__(self, db_path: str = "logs/trading.db"):
        # 优先读取环境变量中的 DATABASE_URL (Railway 会自动提供)
        # 如果没有，则回退到本地 SQLite
        self.db_url = os.getenv("DATABASE_URL")
        
        if self.db_url:
            # 针对 Railway/Postgres 的 URL 修正 (SQLAlchemy 需要 postgresql:// 开头)
            if self.db_url.startswith("postgres://"):
                self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)
            log.info(f"使用 PostgreSQL 数据库: {self.db_url.split('@')[1] if '@' in self.db_url else 'Railway'}")
        else:
            # 本地开发使用 SQLite
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_url = f"sqlite:///{db_path}"
            log.info(f"使用 SQLite 数据库: {db_path}")
        
        self.engine = create_engine(self.db_url)
        self._init_database()
        log.info("交易日志系统初始化完成")
    
    def _init_database(self):
        """初始化数据库"""
        with self.engine.begin() as conn:
            # 决策记录表
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS decisions (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence INTEGER,
                    leverage INTEGER,
                    position_size_pct REAL,
                    stop_loss_pct REAL,
                    take_profit_pct REAL,
                    reasoning TEXT,
                    market_context TEXT,
                    llm_raw_output TEXT,
                    risk_validated BOOLEAN,
                    risk_message TEXT
                )
            '''))
            
            # 执行记录表
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS executions (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success BOOLEAN,
                    entry_price REAL,
                    quantity REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    orders_data TEXT,
                    message TEXT
                )
            '''))
            
            # 交易记录表
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    open_time TEXT NOT NULL,
                    close_time TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    quantity REAL,
                    leverage INTEGER,
                    pnl REAL,
                    pnl_pct REAL,
                    status TEXT
                )
            '''))
            
            # 性能指标表
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS performance (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    total_pnl REAL,
                    sharpe_ratio REAL,
                    max_drawdown_pct REAL,
                    account_balance REAL
                )
            '''))
    
    def log_decision(self, decision: Dict, market_context: Dict, risk_result: tuple):
        """记录决策"""
        is_valid, modified_decision, risk_message = risk_result
        
        query = text('''
            INSERT INTO decisions (
                timestamp, symbol, action, confidence, leverage,
                position_size_pct, stop_loss_pct, take_profit_pct,
                reasoning, market_context, llm_raw_output,
                risk_validated, risk_message
            ) VALUES (:timestamp, :symbol, :action, :confidence, :leverage,
                :position_size_pct, :stop_loss_pct, :take_profit_pct,
                :reasoning, :market_context, :llm_raw_output,
                :risk_validated, :risk_message)
        ''')
        
        with self.engine.begin() as conn:
            conn.execute(query, {
                'timestamp': decision.get('timestamp'),
                'symbol': decision.get('symbol'),
                'action': decision.get('action'),
                'confidence': decision.get('confidence'),
                'leverage': decision.get('leverage'),
                'position_size_pct': decision.get('position_size_pct'),
                'stop_loss_pct': decision.get('stop_loss_pct'),
                'take_profit_pct': decision.get('take_profit_pct'),
                'reasoning': decision.get('reasoning'),
                'market_context': json.dumps(market_context),
                'llm_raw_output': decision.get('raw_response', ''),
                'risk_validated': is_valid,
                'risk_message': risk_message
            })
        
        log.info(f"决策已记录: {decision.get('action')}")
    
    def log_execution(self, execution_result: Dict):
        """记录执行结果"""
        query = text('''
            INSERT INTO executions (
                timestamp, symbol, action, success,
                entry_price, quantity, stop_loss, take_profit,
                orders_data, message
            ) VALUES (:timestamp, :symbol, :action, :success,
                :entry_price, :quantity, :stop_loss, :take_profit,
                :orders_data, :message)
        ''')
        
        with self.engine.begin() as conn:
            conn.execute(query, {
                'timestamp': execution_result.get('timestamp'),
                'symbol': execution_result.get('symbol', ''),
                'action': execution_result.get('action'),
                'success': execution_result.get('success'),
                'entry_price': execution_result.get('entry_price'),
                'quantity': execution_result.get('quantity'),
                'stop_loss': execution_result.get('stop_loss'),
                'take_profit': execution_result.get('take_profit'),
                'orders_data': json.dumps(execution_result.get('orders', [])),
                'message': execution_result.get('message')
            })
        
        log.info(f"执行结果已记录: {execution_result.get('action')}")
    
    def open_trade(self, trade_info: Dict):
        """开启新交易"""
        query = text('''
            INSERT INTO trades (
                open_time, symbol, side, entry_price, quantity, leverage, status
            ) VALUES (:open_time, :symbol, :side, :entry_price, :quantity, :leverage, :status)
        ''')
        
        with self.engine.begin() as conn:
            conn.execute(query, {
                'open_time': trade_info.get('timestamp'),
                'symbol': trade_info.get('symbol'),
                'side': trade_info.get('side'),
                'entry_price': trade_info.get('entry_price'),
                'quantity': trade_info.get('quantity'),
                'leverage': trade_info.get('leverage', 1),
                'status': 'OPEN'
            })
    
    def close_trade(self, symbol: str, exit_price: float, pnl: float):
        """关闭交易"""
        with self.engine.begin() as conn:
            # 查找最近的未关闭交易
            result = conn.execute(text('''
                SELECT id, entry_price, quantity FROM trades
                WHERE symbol = :symbol AND status = 'OPEN'
                ORDER BY id DESC LIMIT 1
            '''), {'symbol': symbol})
            
            row = result.fetchone()
            if row:
                trade_id, entry_price, quantity = row
                
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                
                conn.execute(text('''
                    UPDATE trades
                    SET close_time = :close_time, exit_price = :exit_price, 
                        pnl = :pnl, pnl_pct = :pnl_pct, status = 'CLOSED'
                    WHERE id = :trade_id
                '''), {
                    'close_time': datetime.now().isoformat(),
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'trade_id': trade_id
                })
    
    def log_performance(self, performance: Dict):
        """记录性能指标"""
        query = text('''
            INSERT INTO performance (
                timestamp, total_trades, winning_trades, losing_trades,
                win_rate, total_pnl, sharpe_ratio, max_drawdown_pct, account_balance
            ) VALUES (:timestamp, :total_trades, :winning_trades, :losing_trades,
                :win_rate, :total_pnl, :sharpe_ratio, :max_drawdown_pct, :account_balance)
        ''')
        
        with self.engine.begin() as conn:
            conn.execute(query, {
                'timestamp': datetime.now().isoformat(),
                'total_trades': performance.get('total_trades', 0),
                'winning_trades': performance.get('winning_trades', 0),
                'losing_trades': performance.get('losing_trades', 0),
                'win_rate': performance.get('win_rate', 0),
                'total_pnl': performance.get('total_pnl', 0),
                'sharpe_ratio': performance.get('sharpe_ratio', 0),
                'max_drawdown_pct': performance.get('max_drawdown_pct', 0),
                'account_balance': performance.get('account_balance', 0)
            })
    
    def get_recent_decisions(self, limit: int = 10) -> List[Dict]:
        """获取最近的决策"""
        with self.engine.connect() as conn:
            result = conn.execute(text('''
                SELECT * FROM decisions
                ORDER BY id DESC LIMIT :limit
            '''), {'limit': limit})
            
            rows = result.fetchall()
            # Convert rows to dictionaries
            return [dict(row._mapping) for row in rows]
    
    def get_trade_statistics(self) -> Dict:
        """获取交易统计"""
        with self.engine.connect() as conn:
            # 总交易数
            result = conn.execute(text('SELECT COUNT(*) FROM trades WHERE status = \'CLOSED\''))
            total_trades = result.scalar() or 0
            
            # 盈利交易
            result = conn.execute(text('SELECT COUNT(*) FROM trades WHERE status = \'CLOSED\' AND pnl > 0'))
            winning_trades = result.scalar() or 0
            
            # 亏损交易
            result = conn.execute(text('SELECT COUNT(*) FROM trades WHERE status = \'CLOSED\' AND pnl < 0'))
            losing_trades = result.scalar() or 0
            
            # 总盈亏
            result = conn.execute(text('SELECT SUM(pnl) FROM trades WHERE status = \'CLOSED\''))
            total_pnl = result.scalar() or 0
            
            # 胜率
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl
            }
