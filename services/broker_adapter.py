"""
券商API適配器模組
提供統一的券商API接口，支援多家券商的整合
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import logging
import requests
import time

logger = logging.getLogger(__name__)

class BrokerAdapter(ABC):
    """券商適配器抽象基類"""
    
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = kwargs.get('base_url', '')
        self.session = requests.Session()
        self.last_request_time = 0
        self.rate_limit_delay = 0.1  # 100ms between requests
    
    def _rate_limit(self):
        """API請求頻率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    @abstractmethod
    def authenticate(self) -> bool:
        """驗證API連接"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """獲取帳戶信息"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """獲取持倉信息"""
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """獲取帳戶餘額"""
        pass
    
    @abstractmethod
    def place_order(self, stock_code: str, order_type: str, quantity: int, 
                   price: Optional[Decimal] = None) -> Dict[str, Any]:
        """下單"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """取消訂單"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """查詢訂單狀態"""
        pass
    
    @abstractmethod
    def get_stock_price(self, stock_code: str) -> Dict[str, Any]:
        """獲取股票即時報價"""
        pass

class MockBrokerAdapter(BrokerAdapter):
    """模擬券商適配器，用於測試和開發"""
    
    def __init__(self, api_key: str = "mock_key", api_secret: str = "mock_secret", **kwargs):
        super().__init__(api_key, api_secret, **kwargs)
        self.mock_balance = Decimal('1000000.00')  # 模擬100萬資金
        self.mock_positions = {}
        self.mock_orders = {}
        self.order_counter = 1
        
        # 模擬股票價格
        self.mock_prices = {
            '2330.TW': {'price': Decimal('500.00'), 'name': '台積電'},
            '2454.TW': {'price': Decimal('800.00'), 'name': '聯發科'},
            '2317.TW': {'price': Decimal('100.00'), 'name': '鴻海'},
            '2412.TW': {'price': Decimal('25.00'), 'name': '中華電'},
            '1301.TW': {'price': Decimal('60.00'), 'name': '台塑'},
        }
    
    def authenticate(self) -> bool:
        """模擬驗證，總是成功"""
        logger.info("Mock broker authentication successful")
        return True
    
    def get_account_info(self) -> Dict[str, Any]:
        """獲取模擬帳戶信息"""
        return {
            'account_id': 'MOCK_ACCOUNT_001',
            'account_name': '測試帳戶',
            'broker_name': '模擬券商',
            'status': 'ACTIVE'
        }
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """獲取模擬持倉"""
        positions = []
        for stock_code, position in self.mock_positions.items():
            current_price = self.mock_prices.get(stock_code, {}).get('price', Decimal('0'))
            market_value = current_price * position['quantity']
            cost_value = position['avg_cost'] * position['quantity']
            unrealized_pnl = market_value - cost_value
            unrealized_pnl_pct = (unrealized_pnl / cost_value * 100) if cost_value > 0 else Decimal('0')
            
            positions.append({
                'stock_code': stock_code,
                'stock_name': self.mock_prices.get(stock_code, {}).get('name', ''),
                'quantity': position['quantity'],
                'avg_cost': float(position['avg_cost']),
                'current_price': float(current_price),
                'market_value': float(market_value),
                'unrealized_pnl': float(unrealized_pnl),
                'unrealized_pnl_pct': float(unrealized_pnl_pct)
            })
        
        return positions
    
    def get_balance(self) -> Dict[str, Any]:
        """獲取模擬餘額"""
        total_position_value = sum(
            self.mock_prices.get(code, {}).get('price', Decimal('0')) * pos['quantity']
            for code, pos in self.mock_positions.items()
        )
        
        return {
            'cash_balance': float(self.mock_balance),
            'total_position_value': float(total_position_value),
            'total_asset_value': float(self.mock_balance + total_position_value),
            'available_cash': float(self.mock_balance)
        }
    
    def place_order(self, stock_code: str, order_type: str, quantity: int, 
                   price: Optional[Decimal] = None) -> Dict[str, Any]:
        """模擬下單"""
        self._rate_limit()
        
        order_id = f"MOCK_ORDER_{self.order_counter:06d}"
        self.order_counter += 1
        
        # 獲取當前價格
        current_price = self.mock_prices.get(stock_code, {}).get('price', Decimal('100.00'))
        
        # 對於市價單，使用當前價格
        if order_type.upper() == 'MARKET':
            execution_price = current_price
        else:
            execution_price = price or current_price
        
        total_amount = execution_price * quantity
        
        # 模擬訂單執行
        if order_type.upper() in ['BUY', 'MARKET_BUY']:
            # 檢查資金是否足夠
            if total_amount > self.mock_balance:
                return {
                    'success': False,
                    'error': '資金不足',
                    'order_id': None
                }
            
            # 扣除資金
            self.mock_balance -= total_amount
            
            # 更新持倉
            if stock_code in self.mock_positions:
                old_quantity = self.mock_positions[stock_code]['quantity']
                old_cost = self.mock_positions[stock_code]['avg_cost']
                new_quantity = old_quantity + quantity
                new_avg_cost = ((old_cost * old_quantity) + (execution_price * quantity)) / new_quantity
                self.mock_positions[stock_code] = {
                    'quantity': new_quantity,
                    'avg_cost': new_avg_cost
                }
            else:
                self.mock_positions[stock_code] = {
                    'quantity': quantity,
                    'avg_cost': execution_price
                }
        
        elif order_type.upper() in ['SELL', 'MARKET_SELL']:
            # 檢查持倉是否足夠
            if stock_code not in self.mock_positions or self.mock_positions[stock_code]['quantity'] < quantity:
                return {
                    'success': False,
                    'error': '持倉不足',
                    'order_id': None
                }
            
            # 增加資金
            self.mock_balance += total_amount
            
            # 更新持倉
            self.mock_positions[stock_code]['quantity'] -= quantity
            if self.mock_positions[stock_code]['quantity'] == 0:
                del self.mock_positions[stock_code]
        
        # 記錄訂單
        self.mock_orders[order_id] = {
            'order_id': order_id,
            'stock_code': stock_code,
            'order_type': order_type,
            'quantity': quantity,
            'price': float(execution_price),
            'total_amount': float(total_amount),
            'status': 'FILLED',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Mock order placed: {order_id} - {order_type} {quantity} shares of {stock_code} at {execution_price}")
        
        return {
            'success': True,
            'order_id': order_id,
            'status': 'FILLED',
            'execution_price': float(execution_price),
            'total_amount': float(total_amount)
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """模擬取消訂單"""
        if order_id in self.mock_orders:
            self.mock_orders[order_id]['status'] = 'CANCELLED'
            logger.info(f"Mock order cancelled: {order_id}")
            return True
        return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """查詢模擬訂單狀態"""
        if order_id in self.mock_orders:
            return self.mock_orders[order_id]
        return {'error': 'Order not found'}
    
    def get_stock_price(self, stock_code: str) -> Dict[str, Any]:
        """獲取模擬股票價格"""
        if stock_code in self.mock_prices:
            return {
                'stock_code': stock_code,
                'stock_name': self.mock_prices[stock_code]['name'],
                'current_price': float(self.mock_prices[stock_code]['price']),
                'timestamp': datetime.now().isoformat()
            }
        return {'error': 'Stock not found'}
    
    def update_mock_price(self, stock_code: str, new_price: Decimal):
        """更新模擬股票價格（測試用）"""
        if stock_code in self.mock_prices:
            self.mock_prices[stock_code]['price'] = new_price
            logger.info(f"Mock price updated: {stock_code} = {new_price}")

class FubonBrokerAdapter(BrokerAdapter):
    """富邦證券API適配器（待實現）"""
    
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        super().__init__(api_key, api_secret, **kwargs)
        self.base_url = kwargs.get('base_url', 'https://api.fubon-ebrokerdj.com')
    
    def authenticate(self) -> bool:
        """富邦證券API認證（待實現）"""
        # TODO: 實現富邦證券的實際API認證邏輯
        logger.warning("Fubon broker adapter not implemented yet")
        return False
    
    def get_account_info(self) -> Dict[str, Any]:
        raise NotImplementedError("Fubon broker adapter not implemented yet")
    
    def get_positions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Fubon broker adapter not implemented yet")
    
    def get_balance(self) -> Dict[str, Any]:
        raise NotImplementedError("Fubon broker adapter not implemented yet")
    
    def place_order(self, stock_code: str, order_type: str, quantity: int, 
                   price: Optional[Decimal] = None) -> Dict[str, Any]:
        raise NotImplementedError("Fubon broker adapter not implemented yet")
    
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Fubon broker adapter not implemented yet")
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Fubon broker adapter not implemented yet")
    
    def get_stock_price(self, stock_code: str) -> Dict[str, Any]:
        raise NotImplementedError("Fubon broker adapter not implemented yet")

def create_broker_adapter(broker_type: str, **kwargs) -> BrokerAdapter:
    """券商適配器工廠函數"""
    if broker_type.lower() == 'mock':
        return MockBrokerAdapter(**kwargs)
    elif broker_type.lower() == 'fubon':
        return FubonBrokerAdapter(**kwargs)
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}")

