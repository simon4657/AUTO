from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal
from models.user import db

class TradingParameters(db.Model):
    """交易參數配置表"""
    __tablename__ = 'trading_parameters'
    
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    min_volume_shares = db.Column(db.Integer, default=1000, nullable=False)  # 最低成交張數
    min_volume_ratio = db.Column(db.Numeric(5, 2), default=Decimal('1.5'), nullable=False)  # 最低量比
    min_money_flow = db.Column(db.Numeric(10, 2), default=Decimal('20.0'), nullable=False)  # 最低資金流向
    take_profit_pct = db.Column(db.Numeric(5, 2), default=Decimal('10.0'), nullable=False)  # 停利百分比
    stop_loss_pct = db.Column(db.Numeric(5, 2), default=Decimal('-5.0'), nullable=False)  # 停損百分比
    per_order_value = db.Column(db.Numeric(12, 2), default=Decimal('500000.00'), nullable=False)  # 單筆下單金額
    max_total_position = db.Column(db.Numeric(15, 2), default=Decimal('1000000.00'), nullable=False)  # 最大總倉位
    max_daily_trades = db.Column(db.Integer, default=20, nullable=False)  # 單日最大交易次數
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TradingParameters {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'is_active': self.is_active,
            'min_volume_shares': int(self.min_volume_shares),
            'min_volume_ratio': float(self.min_volume_ratio),
            'min_money_flow': float(self.min_money_flow),
            'take_profit_pct': float(self.take_profit_pct),
            'stop_loss_pct': float(self.stop_loss_pct),
            'per_order_value': float(self.per_order_value),
            'max_total_position': float(self.max_total_position),
            'max_daily_trades': self.max_daily_trades,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class Position(db.Model):
    """持倉記錄表"""
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(10), nullable=False)  # 股票代碼
    stock_name = db.Column(db.String(50), nullable=True)   # 股票名稱
    quantity = db.Column(db.Integer, nullable=False)       # 持有股數
    avg_cost = db.Column(db.Numeric(10, 2), nullable=False)  # 平均成本
    current_price = db.Column(db.Numeric(10, 2), nullable=True)  # 當前價格
    market_value = db.Column(db.Numeric(15, 2), nullable=True)   # 市值
    unrealized_pnl = db.Column(db.Numeric(15, 2), nullable=True)  # 未實現損益
    unrealized_pnl_pct = db.Column(db.Numeric(8, 4), nullable=True)  # 未實現損益百分比
    buy_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # 是否為活躍持倉
    
    def __repr__(self):
        return f'<Position {self.stock_code}: {self.quantity} shares>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'quantity': self.quantity,
            'avg_cost': float(self.avg_cost),
            'current_price': float(self.current_price) if self.current_price else None,
            'market_value': float(self.market_value) if self.market_value else None,
            'unrealized_pnl': float(self.unrealized_pnl) if self.unrealized_pnl else None,
            'unrealized_pnl_pct': float(self.unrealized_pnl_pct) if self.unrealized_pnl_pct else None,
            'buy_date': self.buy_date.isoformat() if self.buy_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active
        }

class TradeRecord(db.Model):
    """交易記錄表"""
    __tablename__ = 'trade_records'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(10), nullable=False)
    stock_name = db.Column(db.String(50), nullable=True)
    trade_type = db.Column(db.String(10), nullable=False)  # 'BUY' or 'SELL'
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)  # 總金額
    fee = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))  # 手續費
    tax = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))  # 稅費
    net_amount = db.Column(db.Numeric(15, 2), nullable=False)    # 淨金額
    trigger_reason = db.Column(db.String(100), nullable=True)    # 觸發原因
    order_id = db.Column(db.String(50), nullable=True)           # 券商訂單ID
    trade_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='COMPLETED')       # 交易狀態
    
    def __repr__(self):
        return f'<TradeRecord {self.trade_type} {self.stock_code}: {self.quantity}@{self.price}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'trade_type': self.trade_type,
            'quantity': self.quantity,
            'price': float(self.price),
            'total_amount': float(self.total_amount),
            'fee': float(self.fee),
            'tax': float(self.tax),
            'net_amount': float(self.net_amount),
            'trigger_reason': self.trigger_reason,
            'order_id': self.order_id,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'status': self.status
        }

class SystemLog(db.Model):
    """系統日誌表"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(10), nullable=False)  # INFO, WARNING, ERROR
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(50), nullable=True)  # 模組名稱
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemLog {self.level}: {self.message[:50]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class SignalHistory(db.Model):
    """信號歷史記錄表"""
    __tablename__ = 'signal_history'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(10), nullable=False)
    stock_name = db.Column(db.String(50), nullable=True)
    signal_type = db.Column(db.String(20), nullable=False)  # 'YELLOW_CANDLE'
    volume_shares = db.Column(db.Integer, nullable=True)
    volume_ratio = db.Column(db.Numeric(5, 2), nullable=True)
    money_flow = db.Column(db.Numeric(10, 2), nullable=True)
    signal_time = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    action_taken = db.Column(db.String(20), nullable=True)  # 'BUY', 'SKIP', 'REJECTED'
    rejection_reason = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f'<SignalHistory {self.signal_type} {self.stock_code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'signal_type': self.signal_type,
            'volume_shares': self.volume_shares,
            'volume_ratio': float(self.volume_ratio) if self.volume_ratio else None,
            'money_flow': float(self.money_flow) if self.money_flow else None,
            'signal_time': self.signal_time.isoformat() if self.signal_time else None,
            'processed': self.processed,
            'action_taken': self.action_taken,
            'rejection_reason': self.rejection_reason
        }

