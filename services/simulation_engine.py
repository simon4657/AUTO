"""
模擬交易引擎
提供完整的模擬交易環境，用於測試自動下單策略
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SimulationEngine:
    """模擬交易引擎"""
    
    def __init__(self):
        self.current_prices = {}  # 當前股價
        self.price_history = {}   # 價格歷史
        self.market_open = True   # 市場是否開放
        self.simulation_speed = 1.0  # 模擬速度倍數
        
        # 模擬一些熱門OTC股票
        self.stock_universe = {
            '3008': {'name': '大立光', 'base_price': 2500.0},
            '6415': {'name': '矽力-KY', 'base_price': 850.0},
            '4919': {'name': '新唐', 'base_price': 120.0},
            '3443': {'name': '創意', 'base_price': 280.0},
            '6239': {'name': '力成', 'base_price': 95.0},
            '3034': {'name': '聯詠', 'base_price': 450.0},
            '4966': {'name': '譜瑞-KY', 'base_price': 1200.0},
            '6531': {'name': '愛普', 'base_price': 180.0},
            '3661': {'name': '世芯-KY', 'base_price': 1800.0},
            '4968': {'name': '立積', 'base_price': 220.0}
        }
        
        # 初始化股價
        self._initialize_prices()
        
    def _initialize_prices(self):
        """初始化股價數據"""
        for code, info in self.stock_universe.items():
            base_price = info['base_price']
            # 添加一些隨機波動
            current_price = base_price * (0.95 + random.random() * 0.1)
            self.current_prices[code] = round(current_price, 2)
            
            # 初始化價格歷史（過去60天）
            self.price_history[code] = []
            price = base_price
            for i in range(60):
                # 模擬價格走勢
                change = random.gauss(0, 0.02)  # 平均0%，標準差2%的變化
                price *= (1 + change)
                price = max(price, base_price * 0.5)  # 最低不低於基準價的50%
                price = min(price, base_price * 2.0)  # 最高不超過基準價的200%
                
                self.price_history[code].append({
                    'date': datetime.now() - timedelta(days=60-i),
                    'price': round(price, 2),
                    'volume': random.randint(1000, 50000)  # 模擬成交量
                })
    
    def get_current_price(self, stock_code: str) -> Optional[float]:
        """獲取當前股價"""
        return self.current_prices.get(stock_code)
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """獲取股票基本信息"""
        if stock_code in self.stock_universe:
            return {
                'code': stock_code,
                'name': self.stock_universe[stock_code]['name'],
                'current_price': self.current_prices.get(stock_code),
                'base_price': self.stock_universe[stock_code]['base_price']
            }
        return None
    
    def get_market_data(self, stock_code: str) -> Optional[Dict]:
        """獲取市場數據（模擬黃柱信號條件）"""
        if stock_code not in self.stock_universe:
            return None
            
        current_price = self.current_prices[stock_code]
        history = self.price_history[stock_code]
        
        # 計算技術指標
        recent_prices = [h['price'] for h in history[-20:]]  # 最近20天
        recent_volumes = [h['volume'] for h in history[-20:]]
        
        avg_price = sum(recent_prices) / len(recent_prices)
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        
        # 模擬當日數據
        today_volume = random.randint(5000, 100000)
        volume_ratio = today_volume / avg_volume
        
        # 模擬資金流向（主力買入比例）
        money_flow = random.uniform(-50, 80)  # -50% 到 80%
        
        # 模擬價格變化
        price_change = (current_price - avg_price) / avg_price * 100
        
        # 判斷是否符合黃柱信號條件
        is_yellow_signal = (
            today_volume >= 10000 and  # 成交量大於1萬股
            volume_ratio >= 1.5 and   # 量比大於1.5
            money_flow >= 20.0 and    # 資金流向大於20%
            price_change >= -5.0      # 價格變化不低於-5%
        )
        
        return {
            'stock_code': stock_code,
            'stock_name': self.stock_universe[stock_code]['name'],
            'current_price': current_price,
            'price_change_pct': round(price_change, 2),
            'volume': today_volume,
            'volume_ratio': round(volume_ratio, 2),
            'money_flow': round(money_flow, 2),
            'avg_volume': int(avg_volume),
            'is_yellow_signal': is_yellow_signal,
            'timestamp': datetime.now()
        }
    
    def simulate_price_movement(self):
        """模擬價格變動"""
        if not self.market_open:
            return
            
        for code in self.current_prices:
            # 模擬價格變動
            change_pct = random.gauss(0, 0.01)  # 平均0%，標準差1%的變化
            new_price = self.current_prices[code] * (1 + change_pct)
            
            # 限制價格範圍
            base_price = self.stock_universe[code]['base_price']
            new_price = max(new_price, base_price * 0.5)
            new_price = min(new_price, base_price * 2.0)
            
            self.current_prices[code] = round(new_price, 2)
            
            # 更新價格歷史
            self.price_history[code].append({
                'date': datetime.now(),
                'price': new_price,
                'volume': random.randint(1000, 50000)
            })
            
            # 保持歷史記錄不超過100條
            if len(self.price_history[code]) > 100:
                self.price_history[code] = self.price_history[code][-100:]
    
    def get_yellow_signals(self, min_volume_shares: int = 10000, 
                          min_volume_ratio: float = 1.5,
                          min_money_flow: float = 20.0) -> List[Dict]:
        """獲取符合條件的黃柱信號股票"""
        signals = []
        
        for code in self.stock_universe:
            market_data = self.get_market_data(code)
            if market_data and (
                market_data['volume'] >= min_volume_shares and
                market_data['volume_ratio'] >= min_volume_ratio and
                market_data['money_flow'] >= min_money_flow
            ):
                signals.append(market_data)
        
        return signals
    
    def execute_simulated_order(self, stock_code: str, action: str, 
                               quantity: int, price: float = None) -> Dict:
        """執行模擬訂單"""
        if stock_code not in self.stock_universe:
            return {
                'success': False,
                'message': f'股票代碼 {stock_code} 不存在'
            }
        
        current_price = self.current_prices[stock_code]
        execution_price = price if price else current_price
        
        # 模擬訂單執行延遲
        time.sleep(0.1 / self.simulation_speed)
        
        # 模擬市場滑價（小幅價格變動）
        slippage = random.uniform(-0.002, 0.002)  # ±0.2%
        final_price = execution_price * (1 + slippage)
        final_price = round(final_price, 2)
        
        total_amount = final_price * quantity
        
        # 模擬交易費用
        fee_rate = 0.001425  # 0.1425%手續費
        fee = total_amount * fee_rate
        
        if action.upper() == 'BUY':
            total_cost = total_amount + fee
        else:  # SELL
            total_cost = total_amount - fee
        
        return {
            'success': True,
            'order_id': f'SIM_{int(time.time())}_{random.randint(1000, 9999)}',
            'stock_code': stock_code,
            'stock_name': self.stock_universe[stock_code]['name'],
            'action': action.upper(),
            'quantity': quantity,
            'execution_price': final_price,
            'total_amount': round(total_amount, 2),
            'fee': round(fee, 2),
            'net_amount': round(total_cost, 2),
            'execution_time': datetime.now(),
            'status': 'COMPLETED'
        }
    
    def set_market_status(self, is_open: bool):
        """設置市場開放狀態"""
        self.market_open = is_open
        logger.info(f"市場狀態設置為: {'開放' if is_open else '關閉'}")
    
    def set_simulation_speed(self, speed: float):
        """設置模擬速度倍數"""
        self.simulation_speed = max(0.1, min(speed, 10.0))
        logger.info(f"模擬速度設置為: {self.simulation_speed}x")
    
    def get_portfolio_value(self, positions: List[Dict]) -> Dict:
        """計算投資組合價值"""
        total_value = 0
        total_cost = 0
        total_pnl = 0
        
        for position in positions:
            stock_code = position['stock_code']
            quantity = position['quantity']
            avg_cost = position['avg_cost']
            
            current_price = self.get_current_price(stock_code)
            if current_price:
                current_value = current_price * quantity
                cost_value = avg_cost * quantity
                pnl = current_value - cost_value
                
                total_value += current_value
                total_cost += cost_value
                total_pnl += pnl
        
        return {
            'total_value': round(total_value, 2),
            'total_cost': round(total_cost, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round((total_pnl / total_cost * 100) if total_cost > 0 else 0, 2)
        }

# 全局模擬引擎實例
simulation_engine = SimulationEngine()

