"""
風險管理模組
實現多層次的風險控制機制，確保交易在安全範圍內進行
"""

from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from models.trading import TradingParameters, Position, TradeRecord, SystemLog
from models.user import db

logger = logging.getLogger(__name__)

class RiskManager:
    """風險管理器"""
    
    def __init__(self):
        self.daily_trade_count = {}  # 記錄每日交易次數
        self.recent_signals = {}     # 記錄最近的交易信號
        self.emergency_stop = False  # 緊急停止標誌
    
    def load_parameters(self) -> Optional[TradingParameters]:
        """載入交易參數"""
        try:
            return TradingParameters.query.first()
        except Exception as e:
            logger.error(f"Failed to load trading parameters: {e}")
            return None
    
    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """驗證交易參數的合理性"""
        errors = []
        
        # 停利百分比驗證
        if 'take_profit_pct' in params:
            take_profit = params['take_profit_pct']
            if not isinstance(take_profit, (int, float, Decimal)) or take_profit <= 0 or take_profit > 100:
                errors.append('停利百分比必須在0-100之間')
        
        # 停損百分比驗證
        if 'stop_loss_pct' in params:
            stop_loss = params['stop_loss_pct']
            if not isinstance(stop_loss, (int, float, Decimal)) or stop_loss >= 0 or stop_loss < -50:
                errors.append('停損百分比必須在-50-0之間')
        
        # 最低成交張數驗證
        if 'min_volume_shares' in params:
            volume_shares = params['min_volume_shares']
            if not isinstance(volume_shares, int) or volume_shares <= 0:
                errors.append('最低成交張數必須為正整數')
        
        # 最低量比驗證
        if 'min_volume_ratio' in params:
            volume_ratio = params['min_volume_ratio']
            if not isinstance(volume_ratio, (int, float, Decimal)) or volume_ratio <= 0:
                errors.append('最低量比必須大於0')
        
        # 單筆下單金額驗證
        if 'per_order_value' in params:
            order_value = params['per_order_value']
            if not isinstance(order_value, (int, float, Decimal)) or order_value <= 0:
                errors.append('單筆下單金額必須大於0')
            elif order_value > 10000000:  # 1000萬上限
                errors.append('單筆下單金額不得超過1000萬')
        
        # 最大總倉位驗證
        if 'max_total_position' in params:
            max_position = params['max_total_position']
            if not isinstance(max_position, (int, float, Decimal)) or max_position <= 0:
                errors.append('最大總倉位必須大於0')
        
        # 單日最大交易次數驗證
        if 'max_daily_trades' in params:
            max_trades = params['max_daily_trades']
            if not isinstance(max_trades, int) or max_trades <= 0 or max_trades > 1000:
                errors.append('單日最大交易次數必須在1-1000之間')
        
        return len(errors) == 0, errors
    
    def check_emergency_stop(self) -> bool:
        """檢查是否觸發緊急停止"""
        if self.emergency_stop:
            return True
        
        # 檢查交易參數是否被停用
        params = self.load_parameters()
        if not params or not params.is_active:
            return True
        
        return False
    
    def check_daily_trade_limit(self, max_daily_trades: int) -> bool:
        """檢查單日交易次數限制"""
        today = datetime.now().date()
        today_str = today.isoformat()
        
        # 從數據庫獲取今日交易次數
        today_count = TradeRecord.query.filter(
            TradeRecord.trade_date >= datetime.combine(today, datetime.min.time())
        ).count()
        
        if today_count >= max_daily_trades:
            logger.warning(f"Daily trade limit reached: {today_count}/{max_daily_trades}")
            self._log_risk_event(
                'WARNING',
                f'已達到單日交易次數限制: {today_count}/{max_daily_trades}',
                'daily_trade_limit'
            )
            return False
        
        return True
    
    def check_position_limit(self, current_total_value: Decimal, 
                           new_order_value: Decimal, max_total_position: Decimal) -> bool:
        """檢查總倉位限制"""
        projected_total = current_total_value + new_order_value
        
        if projected_total > max_total_position:
            logger.warning(f"Position limit exceeded: {projected_total} > {max_total_position}")
            self._log_risk_event(
                'WARNING',
                f'總倉位限制超限: {projected_total} > {max_total_position}',
                'position_limit'
            )
            return False
        
        return True
    
    def check_single_stock_exposure(self, stock_code: str, new_order_value: Decimal,
                                  total_asset_value: Decimal, max_exposure_pct: float = 20.0) -> bool:
        """檢查單一股票持倉比例限制"""
        # 獲取該股票當前持倉
        current_position = Position.query.filter_by(
            stock_code=stock_code, is_active=True
        ).first()
        
        current_value = Decimal('0')
        if current_position and current_position.market_value:
            current_value = Decimal(str(current_position.market_value))
        
        projected_value = current_value + new_order_value
        exposure_pct = (projected_value / total_asset_value * 100) if total_asset_value > 0 else 0
        
        if exposure_pct > max_exposure_pct:
            logger.warning(f"Single stock exposure limit exceeded: {stock_code} {exposure_pct:.2f}% > {max_exposure_pct}%")
            self._log_risk_event(
                'WARNING',
                f'單一股票持倉比例超限: {stock_code} {exposure_pct:.2f}% > {max_exposure_pct}%',
                'single_stock_exposure'
            )
            return False
        
        return True
    
    def check_duplicate_signal(self, stock_code: str, cooldown_minutes: int = 60) -> bool:
        """檢查重複信號過濾"""
        now = datetime.now()
        cooldown_key = f"{stock_code}_{now.date()}"
        
        if cooldown_key in self.recent_signals:
            last_signal_time = self.recent_signals[cooldown_key]
            if (now - last_signal_time).total_seconds() < cooldown_minutes * 60:
                logger.info(f"Duplicate signal filtered: {stock_code} (cooldown: {cooldown_minutes}min)")
                return False
        
        # 記錄新信號
        self.recent_signals[cooldown_key] = now
        return True
    
    def check_market_hours(self) -> bool:
        """檢查是否在交易時間內"""
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        # 台股交易時間：週一到週五 9:00-13:30
        if weekday >= 5:  # 週末
            return False
        
        # 上午盤：9:00-12:00
        # 下午盤：13:30-13:30 (實際到13:30)
        morning_start = datetime.strptime('09:00', '%H:%M').time()
        morning_end = datetime.strptime('12:00', '%H:%M').time()
        afternoon_start = datetime.strptime('13:30', '%H:%M').time()
        afternoon_end = datetime.strptime('13:30', '%H:%M').time()
        
        is_morning = morning_start <= current_time <= morning_end
        is_afternoon = current_time == afternoon_start  # 只有13:30這一刻
        
        return is_morning or is_afternoon
    
    def pre_trade_risk_check(self, stock_code: str, order_value: Decimal,
                           current_positions_value: Decimal, total_asset_value: Decimal) -> Tuple[bool, str]:
        """交易前風險檢查"""
        
        # 檢查緊急停止
        if self.check_emergency_stop():
            return False, "系統處於緊急停止狀態"
        
        # 載入交易參數
        params = self.load_parameters()
        if not params:
            return False, "無法載入交易參數"
        
        # 檢查交易時間（開發階段暫時跳過）
        # if not self.check_market_hours():
        #     return False, "非交易時間"
        
        # 檢查單日交易次數限制
        if not self.check_daily_trade_limit(params.max_daily_trades):
            return False, "已達到單日交易次數限制"
        
        # 檢查總倉位限制
        if not self.check_position_limit(
            current_positions_value, 
            order_value, 
            params.max_total_position
        ):
            return False, "總倉位限制超限"
        
        # 檢查單一股票持倉比例
        if not self.check_single_stock_exposure(stock_code, order_value, total_asset_value):
            return False, "單一股票持倉比例超限"
        
        # 檢查重複信號
        if not self.check_duplicate_signal(stock_code):
            return False, "重複信號，已過濾"
        
        return True, "風險檢查通過"
    
    def check_stop_loss_take_profit(self, position: Position, current_price: Decimal,
                                  take_profit_pct: Decimal, stop_loss_pct: Decimal) -> Tuple[bool, str, str]:
        """檢查停利停損條件"""
        if not position.avg_cost:
            return False, "", ""
        
        avg_cost = Decimal(str(position.avg_cost))
        price_change_pct = ((current_price - avg_cost) / avg_cost * 100)
        
        # 檢查停利條件
        if price_change_pct >= take_profit_pct:
            return True, "TAKE_PROFIT", f"觸發停利: {price_change_pct:.2f}% >= {take_profit_pct}%"
        
        # 檢查停損條件
        if price_change_pct <= stop_loss_pct:
            return True, "STOP_LOSS", f"觸發停損: {price_change_pct:.2f}% <= {stop_loss_pct}%"
        
        return False, "", ""
    
    def calculate_order_quantity(self, stock_code: str, order_value: Decimal, 
                               stock_price: Decimal) -> int:
        """計算下單股數（以張為單位）"""
        if stock_price <= 0:
            return 0
        
        # 計算可購買的張數（1張 = 1000股）
        lots = int(order_value / (stock_price * 1000))
        
        # 返回股數
        return lots * 1000
    
    def set_emergency_stop(self, reason: str = "手動觸發"):
        """設置緊急停止"""
        self.emergency_stop = True
        logger.critical(f"Emergency stop activated: {reason}")
        self._log_risk_event('ERROR', f'緊急停止已啟動: {reason}', 'emergency_stop')
    
    def reset_emergency_stop(self):
        """重置緊急停止"""
        self.emergency_stop = False
        logger.info("Emergency stop reset")
        self._log_risk_event('INFO', '緊急停止已重置', 'emergency_stop')
    
    def _log_risk_event(self, level: str, message: str, module: str):
        """記錄風險事件到系統日誌"""
        try:
            log = SystemLog(
                level=level,
                message=message,
                module=module
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """獲取風險統計信息"""
        today = datetime.now().date()
        
        # 今日交易次數
        today_trades = TradeRecord.query.filter(
            TradeRecord.trade_date >= datetime.combine(today, datetime.min.time())
        ).count()
        
        # 當前持倉數量
        active_positions = Position.query.filter_by(is_active=True).count()
        
        # 總持倉市值
        positions = Position.query.filter_by(is_active=True).all()
        total_position_value = sum(
            float(pos.market_value or 0) for pos in positions
        )
        
        # 最近24小時的風險事件
        yesterday = datetime.now() - timedelta(days=1)
        risk_events = SystemLog.query.filter(
            SystemLog.timestamp >= yesterday,
            SystemLog.level.in_(['WARNING', 'ERROR'])
        ).count()
        
        return {
            'today_trades': today_trades,
            'active_positions': active_positions,
            'total_position_value': total_position_value,
            'recent_risk_events': risk_events,
            'emergency_stop_active': self.emergency_stop
        }

