"""
策略評估引擎
核心交易決策邏輯，負責評估信號並生成交易指令
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime
from models.trading import TradingParameters, Position, TradeRecord, SystemLog, SignalHistory
from models.user import db
from services.broker_adapter import BrokerAdapter
from services.risk_manager import RiskManager
from services.signal_processor import SignalProcessor

logger = logging.getLogger(__name__)

class StrategyEngine:
    """策略評估引擎"""
    
    def __init__(self, broker_adapter: BrokerAdapter, risk_manager: RiskManager, 
                 signal_processor: SignalProcessor):
        self.broker = broker_adapter
        self.risk_manager = risk_manager
        self.signal_processor = signal_processor
        self.is_running = False
    
    def load_trading_parameters(self) -> Optional[TradingParameters]:
        """載入交易參數"""
        try:
            params = TradingParameters.query.first()
            if not params:
                # 創建默認參數
                params = TradingParameters()
                db.session.add(params)
                db.session.commit()
                logger.info("Created default trading parameters")
            return params
        except Exception as e:
            logger.error(f"Failed to load trading parameters: {e}")
            return None
    
    def evaluate_buy_signals(self) -> List[Dict[str, Any]]:
        """評估買入信號"""
        if not self.is_running:
            return []
        
        try:
            # 載入交易參數
            params = self.load_trading_parameters()
            if not params or not params.is_active:
                logger.info("Trading is disabled or parameters not found")
                return []
            
            # 獲取信號
            signals = self.signal_processor.fetch_yellow_candle_signals()
            if not signals:
                logger.info("No signals received from screener")
                return []
            
            # 處理信號
            processed_signals = self.signal_processor.process_signals(signals)
            
            # 獲取當前帳戶狀態
            balance_info = self.broker.get_balance()
            current_positions = self.broker.get_positions()
            
            total_asset_value = Decimal(str(balance_info.get('total_asset_value', 0)))
            current_position_value = Decimal(str(balance_info.get('total_position_value', 0)))
            
            buy_decisions = []
            
            for signal in processed_signals:
                decision = self._evaluate_single_buy_signal(
                    signal, params, current_positions, 
                    current_position_value, total_asset_value
                )
                if decision:
                    buy_decisions.append(decision)
            
            logger.info(f"Generated {len(buy_decisions)} buy decisions from {len(processed_signals)} signals")
            return buy_decisions
            
        except Exception as e:
            logger.error(f"Error evaluating buy signals: {e}")
            return []
    
    def _evaluate_single_buy_signal(self, signal: Dict[str, Any], params: TradingParameters,
                                   current_positions: List[Dict], current_position_value: Decimal,
                                   total_asset_value: Decimal) -> Optional[Dict[str, Any]]:
        """評估單個買入信號"""
        stock_code = signal['stock_code']
        
        try:
            # 檢查是否已持有該股票
            for position in current_positions:
                if position['stock_code'] == stock_code:
                    logger.info(f"Already holding {stock_code}, skipping")
                    return None
            
            # 檢查信號是否滿足用戶設定的條件
            if not self._check_signal_criteria(signal, params):
                return None
            
            # 獲取股票當前價格
            price_info = self.broker.get_stock_price(stock_code)
            if 'error' in price_info:
                logger.warning(f"Failed to get price for {stock_code}: {price_info['error']}")
                return None
            
            current_price = Decimal(str(price_info['current_price']))
            order_value = params.per_order_value
            
            # 風險檢查
            risk_check_passed, risk_message = self.risk_manager.pre_trade_risk_check(
                stock_code, order_value, current_position_value, total_asset_value
            )
            
            if not risk_check_passed:
                logger.info(f"Risk check failed for {stock_code}: {risk_message}")
                return None
            
            # 計算下單股數
            quantity = self.risk_manager.calculate_order_quantity(
                stock_code, order_value, current_price
            )
            
            if quantity <= 0:
                logger.warning(f"Invalid quantity calculated for {stock_code}: {quantity}")
                return None
            
            return {
                'stock_code': stock_code,
                'stock_name': signal.get('stock_name', ''),
                'action': 'BUY',
                'quantity': quantity,
                'order_type': 'MARKET',
                'current_price': float(current_price),
                'order_value': float(order_value),
                'signal_data': signal,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating signal for {stock_code}: {e}")
            return None
    
    def _check_signal_criteria(self, signal: Dict[str, Any], params: TradingParameters) -> bool:
        """檢查信號是否滿足用戶設定的條件"""
        try:
            # 檢查成交張數
            volume_shares = signal.get('volume_shares', 0)
            if volume_shares < params.min_volume_shares:
                logger.info(f"Volume too low: {volume_shares} < {params.min_volume_shares}")
                return False
            
            # 檢查量比
            volume_ratio = signal.get('volume_ratio', Decimal('0'))
            if volume_ratio < params.min_volume_ratio:
                logger.info(f"Volume ratio too low: {volume_ratio} < {params.min_volume_ratio}")
                return False
            
            # 檢查資金流向
            money_flow = signal.get('money_flow', Decimal('0'))
            if money_flow < params.min_money_flow:
                logger.info(f"Money flow too low: {money_flow} < {params.min_money_flow}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal criteria: {e}")
            return False
    
    def execute_buy_decision(self, decision: Dict[str, Any]) -> bool:
        """執行買入決策"""
        try:
            stock_code = decision['stock_code']
            quantity = decision['quantity']
            order_type = decision['order_type']
            
            logger.info(f"Executing buy order: {stock_code} x {quantity}")
            
            # 執行下單
            order_result = self.broker.place_order(
                stock_code=stock_code,
                order_type=order_type,
                quantity=quantity
            )
            
            if order_result.get('success'):
                # 記錄交易
                self._record_trade(decision, order_result, 'BUY')
                
                # 更新持倉
                self._update_position_after_buy(decision, order_result)
                
                logger.info(f"Buy order executed successfully: {order_result['order_id']}")
                return True
            else:
                logger.error(f"Buy order failed: {order_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing buy decision: {e}")
            return False
    
    def monitor_positions_for_sell(self) -> List[Dict[str, Any]]:
        """監控持倉並生成賣出決策"""
        if not self.is_running:
            return []
        
        try:
            params = self.load_trading_parameters()
            if not params:
                return []
            
            # 獲取當前持倉
            positions = Position.query.filter_by(is_active=True).all()
            sell_decisions = []
            
            for position in positions:
                # 獲取當前價格
                price_info = self.broker.get_stock_price(position.stock_code)
                if 'error' in price_info:
                    continue
                
                current_price = Decimal(str(price_info['current_price']))
                
                # 檢查停利停損條件
                should_sell, sell_reason, message = self.risk_manager.check_stop_loss_take_profit(
                    position, current_price, params.take_profit_pct, params.stop_loss_pct
                )
                
                if should_sell:
                    decision = {
                        'stock_code': position.stock_code,
                        'stock_name': position.stock_name,
                        'action': 'SELL',
                        'quantity': position.quantity,
                        'order_type': 'MARKET',
                        'current_price': float(current_price),
                        'avg_cost': float(position.avg_cost),
                        'sell_reason': sell_reason,
                        'message': message,
                        'position_id': position.id,
                        'timestamp': datetime.now()
                    }
                    sell_decisions.append(decision)
            
            logger.info(f"Generated {len(sell_decisions)} sell decisions")
            return sell_decisions
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            return []
    
    def execute_sell_decision(self, decision: Dict[str, Any]) -> bool:
        """執行賣出決策"""
        try:
            stock_code = decision['stock_code']
            quantity = decision['quantity']
            
            logger.info(f"Executing sell order: {stock_code} x {quantity} ({decision['sell_reason']})")
            
            # 執行下單
            order_result = self.broker.place_order(
                stock_code=stock_code,
                order_type='MARKET_SELL',
                quantity=quantity
            )
            
            if order_result.get('success'):
                # 記錄交易
                self._record_trade(decision, order_result, 'SELL')
                
                # 更新持倉
                self._update_position_after_sell(decision, order_result)
                
                logger.info(f"Sell order executed successfully: {order_result['order_id']}")
                return True
            else:
                logger.error(f"Sell order failed: {order_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing sell decision: {e}")
            return False
    
    def _record_trade(self, decision: Dict[str, Any], order_result: Dict[str, Any], trade_type: str):
        """記錄交易到數據庫"""
        try:
            execution_price = Decimal(str(order_result.get('execution_price', 0)))
            quantity = decision['quantity']
            total_amount = execution_price * quantity
            
            # 計算手續費（簡化計算，實際應根據券商規則）
            fee = total_amount * Decimal('0.001425')  # 0.1425%
            tax = Decimal('0')
            if trade_type == 'SELL':
                tax = total_amount * Decimal('0.003')  # 0.3% 證交稅
            
            net_amount = total_amount - fee - tax
            if trade_type == 'SELL':
                net_amount = total_amount - fee - tax
            else:
                net_amount = -(total_amount + fee)  # 買入為負值
            
            trade_record = TradeRecord(
                stock_code=decision['stock_code'],
                stock_name=decision.get('stock_name', ''),
                trade_type=trade_type,
                quantity=quantity,
                price=execution_price,
                total_amount=total_amount,
                fee=fee,
                tax=tax,
                net_amount=net_amount,
                trigger_reason=decision.get('sell_reason', 'YELLOW_CANDLE_BUY'),
                order_id=order_result.get('order_id'),
                status='COMPLETED'
            )
            
            db.session.add(trade_record)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            db.session.rollback()
    
    def _update_position_after_buy(self, decision: Dict[str, Any], order_result: Dict[str, Any]):
        """買入後更新持倉"""
        try:
            stock_code = decision['stock_code']
            quantity = decision['quantity']
            price = Decimal(str(order_result.get('execution_price', 0)))
            
            # 檢查是否已有持倉
            position = Position.query.filter_by(stock_code=stock_code, is_active=True).first()
            
            if position:
                # 更新現有持倉
                old_quantity = position.quantity
                old_cost = position.avg_cost
                new_quantity = old_quantity + quantity
                new_avg_cost = ((old_cost * old_quantity) + (price * quantity)) / new_quantity
                
                position.quantity = new_quantity
                position.avg_cost = new_avg_cost
            else:
                # 創建新持倉
                position = Position(
                    stock_code=stock_code,
                    stock_name=decision.get('stock_name', ''),
                    quantity=quantity,
                    avg_cost=price,
                    is_active=True
                )
                db.session.add(position)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating position after buy: {e}")
            db.session.rollback()
    
    def _update_position_after_sell(self, decision: Dict[str, Any], order_result: Dict[str, Any]):
        """賣出後更新持倉"""
        try:
            position_id = decision.get('position_id')
            if position_id:
                position = Position.query.get(position_id)
                if position:
                    position.is_active = False
                    db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating position after sell: {e}")
            db.session.rollback()
    
    def start(self):
        """啟動策略引擎"""
        self.is_running = True
        logger.info("Strategy engine started")
        
        # 記錄啟動日誌
        log = SystemLog(
            level='INFO',
            message='策略引擎已啟動',
            module='strategy_engine'
        )
        db.session.add(log)
        db.session.commit()
    
    def stop(self):
        """停止策略引擎"""
        self.is_running = False
        logger.info("Strategy engine stopped")
        
        # 記錄停止日誌
        log = SystemLog(
            level='INFO',
            message='策略引擎已停止',
            module='strategy_engine'
        )
        db.session.add(log)
        db.session.commit()
    
    def run_single_cycle(self) -> Dict[str, Any]:
        """執行單次評估週期"""
        results = {
            'buy_decisions': 0,
            'buy_executed': 0,
            'sell_decisions': 0,
            'sell_executed': 0,
            'errors': []
        }
        
        try:
            # 評估買入信號
            buy_decisions = self.evaluate_buy_signals()
            results['buy_decisions'] = len(buy_decisions)
            
            # 執行買入決策
            for decision in buy_decisions:
                if self.execute_buy_decision(decision):
                    results['buy_executed'] += 1
            
            # 監控持倉並執行賣出
            sell_decisions = self.monitor_positions_for_sell()
            results['sell_decisions'] = len(sell_decisions)
            
            for decision in sell_decisions:
                if self.execute_sell_decision(decision):
                    results['sell_executed'] += 1
            
        except Exception as e:
            error_msg = f"Error in strategy cycle: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results

