"""
新策略引擎 - 整合Yahoo Finance實際數據
"""

import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional
from .yahoo_finance_robust import YahooFinanceService

logger = logging.getLogger(__name__)

class StrategyEngine:
    """策略引擎類 - 支援多種交易策略"""
    
    def __init__(self):
        self.is_running = False
        self.strategy_type = "type1"  # 預設為TYPE1黃柱策略
        self.start_time = None
        self.yahoo_service = YahooFinanceService()
        self.current_signals = []
        self.trade_records = []
        self._stop_event = threading.Event()
        self._strategy_thread = None
        
        # 策略參數
        self.parameters = {
            'min_volume_shares': 1000,
            'min_volume_ratio': 1.5,
            'min_money_flow': 20,
            'take_profit_pct': 10,
            'stop_loss_pct': 5
        }
    
    def set_strategy_type(self, strategy_type: str):
        """設定策略類型"""
        valid_types = ["type1", "type2", "type3", "type4"]
        if strategy_type in valid_types:
            self.strategy_type = strategy_type
            logger.info(f"策略類型已設定為: {strategy_type}")
        else:
            logger.warning(f"無效的策略類型: {strategy_type}")
    
    def update_parameters(self, params: Dict):
        """更新策略參數"""
        self.parameters.update(params)
        logger.info(f"策略參數已更新: {self.parameters}")
    
    def start(self):
        """啟動策略引擎"""
        if self.is_running:
            logger.warning("策略引擎已在運行中")
            return False
        
        self.is_running = True
        self.start_time = datetime.now()
        self._stop_event.clear()
        
        # 啟動策略執行線程
        self._strategy_thread = threading.Thread(target=self._run_strategy, daemon=True)
        self._strategy_thread.start()
        
        logger.info(f"策略引擎已啟動 - 策略類型: {self.strategy_type}")
        self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] 啟動{self.strategy_type}策略")
        return True
    
    def stop(self):
        """停止策略引擎"""
        if not self.is_running:
            logger.warning("策略引擎未在運行")
            return False
        
        self.is_running = False
        self._stop_event.set()
        
        if self._strategy_thread and self._strategy_thread.is_alive():
            self._strategy_thread.join(timeout=5)
        
        logger.info("策略引擎已停止")
        self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] 策略引擎已停止")
        return True
    
    def _run_strategy(self):
        """策略執行主循環"""
        logger.info(f"開始執行 {self.strategy_type.upper()} 策略")
        
        while not self._stop_event.is_set():
            try:
                if self.strategy_type == "type1":
                    self._execute_type1_strategy()
                elif self.strategy_type == "type2":
                    self._execute_type2_strategy()
                elif self.strategy_type == "type3":
                    self._execute_type3_strategy()
                elif self.strategy_type == "type4":
                    self._execute_type4_strategy()
                
                # 每30秒執行一次策略掃描
                self._stop_event.wait(30)
                
            except Exception as e:
                logger.error(f"策略執行錯誤: {str(e)}")
                self._stop_event.wait(10)  # 錯誤後等待10秒再重試
    
    def _execute_type1_strategy(self):
        """執行TYPE1黃柱策略"""
        logger.info("執行TYPE1黃柱策略掃描...")
        
        try:
            # 使用Yahoo Finance服務掃描黃柱股票
            yellow_stocks = self.yahoo_service.scan_yellow_column_stocks(max_stocks=20)
            
            if yellow_stocks:
                logger.info(f"TYPE1策略發現 {len(yellow_stocks)} 支黃柱股票")
                
                for stock in yellow_stocks:
                    # 檢查是否符合用戶設定的參數
                    if self._check_user_parameters(stock):
                        signal = {
                            'strategy': 'TYPE1',
                            'symbol': stock['symbol'],
                            'name': stock['name'],
                            'action': 'BUY',
                            'price': stock['close_price'],
                            'volume': stock['volume'],
                            'volume_ratio': stock['volume_ratio'],
                            'money_flow': stock['money_flow'],
                            'reason': '黃柱信號',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        self.current_signals.append(signal)
                        self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] 買入 {signal['symbol']} {signal['name']} @{signal['price']:.2f}")
                        
                        logger.info(f"生成買入信號: {stock['symbol']} - 價格: {stock['close_price']}")
            else:
                logger.info("TYPE1策略未發現符合條件的黃柱股票")
                self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] 掃描完成，未發現黃柱股票")
                
        except Exception as e:
            logger.error(f"TYPE1策略執行錯誤: {str(e)}")
            self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] 策略執行錯誤: {str(e)}")
    
    def _execute_type2_strategy(self):
        """執行TYPE2量價策略"""
        logger.info("執行TYPE2量價策略...")
        
        # 模擬量價策略邏輯
        try:
            # 獲取部分股票數據進行量價分析
            symbols = self.yahoo_service.taiwan_stocks[:10]
            found_signals = 0
            
            for symbol in symbols:
                data = self.yahoo_service.get_stock_data(symbol, period="1mo")
                if data is None or len(data) < 5:
                    continue
                
                volume_ratio = self.yahoo_service.calculate_volume_ratio(data)
                money_flow = self.yahoo_service.calculate_money_flow(data)
                
                # 量價策略條件：量比 > 2.0 且資金流向 > 10
                if volume_ratio > 2.0 and money_flow > 10:
                    latest = data.iloc[-1]
                    found_signals += 1
                    
                    signal = {
                        'strategy': 'TYPE2',
                        'symbol': symbol,
                        'action': 'BUY',
                        'price': float(latest['Close']),
                        'volume_ratio': volume_ratio,
                        'money_flow': money_flow,
                        'reason': '量價突破',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self.current_signals.append(signal)
                    self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE2信號: {symbol} 量比{volume_ratio:.2f}")
            
            if found_signals == 0:
                self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE2掃描完成，未發現量價突破")
                    
        except Exception as e:
            logger.error(f"TYPE2策略執行錯誤: {str(e)}")
            self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE2策略錯誤: {str(e)}")
    
    def _execute_type3_strategy(self):
        """執行TYPE3資金流策略"""
        logger.info("執行TYPE3資金流策略...")
        
        try:
            # 資金流策略：專注於資金流向分析
            symbols = self.yahoo_service.taiwan_stocks[:15]
            found_signals = 0
            
            for symbol in symbols:
                data = self.yahoo_service.get_stock_data(symbol, period="1mo")
                if data is None:
                    continue
                
                money_flow = self.yahoo_service.calculate_money_flow(data)
                
                # 資金流策略條件：資金流向 > 30
                if money_flow > 30:
                    latest = data.iloc[-1]
                    found_signals += 1
                    
                    signal = {
                        'strategy': 'TYPE3',
                        'symbol': symbol,
                        'action': 'BUY',
                        'price': float(latest['Close']),
                        'money_flow': money_flow,
                        'reason': '資金大量流入',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self.current_signals.append(signal)
                    self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE3信號: {symbol} 資金流{money_flow:.2f}")
            
            if found_signals == 0:
                self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE3掃描完成，未發現資金流入")
                    
        except Exception as e:
            logger.error(f"TYPE3策略執行錯誤: {str(e)}")
            self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE3策略錯誤: {str(e)}")
    
    def _execute_type4_strategy(self):
        """執行TYPE4綜合策略"""
        logger.info("執行TYPE4綜合策略...")
        
        try:
            # 綜合策略：結合黃柱、量價、資金流多重條件
            symbols = self.yahoo_service.taiwan_stocks[:20]
            found_signals = 0
            
            for symbol in symbols:
                data = self.yahoo_service.get_stock_data(symbol, period="2mo")
                if data is None or len(data) < 21:
                    continue
                
                # 檢查多重條件
                is_yellow = self.yahoo_service.calculate_yellow_column_indicator(data)
                volume_ratio = self.yahoo_service.calculate_volume_ratio(data)
                money_flow = self.yahoo_service.calculate_money_flow(data)
                
                # 綜合策略條件：黃柱 OR (量比>1.8 AND 資金流>15)
                if is_yellow or (volume_ratio > 1.8 and money_flow > 15):
                    latest = data.iloc[-1]
                    found_signals += 1
                    
                    signal = {
                        'strategy': 'TYPE4',
                        'symbol': symbol,
                        'action': 'BUY',
                        'price': float(latest['Close']),
                        'volume_ratio': volume_ratio,
                        'money_flow': money_flow,
                        'is_yellow': is_yellow,
                        'reason': '綜合信號',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self.current_signals.append(signal)
                    self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE4信號: {symbol} 綜合評分通過")
            
            if found_signals == 0:
                self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE4掃描完成，未發現綜合信號")
                    
        except Exception as e:
            logger.error(f"TYPE4策略執行錯誤: {str(e)}")
            self.trade_records.append(f"[{datetime.now().strftime('%H:%M:%S')}] TYPE4策略錯誤: {str(e)}")
    
    def _check_user_parameters(self, stock: Dict) -> bool:
        """檢查股票是否符合用戶設定的參數"""
        try:
            # 檢查成交張數（台股以張為單位，1張=1000股）
            volume_shares = stock['volume']
            if volume_shares < self.parameters['min_volume_shares']:
                return False
            
            # 檢查量比
            if stock['volume_ratio'] < self.parameters['min_volume_ratio']:
                return False
            
            # 檢查資金流向
            if stock['money_flow'] < self.parameters['min_money_flow']:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"參數檢查錯誤: {str(e)}")
            return False
    
    def get_status(self) -> Dict:
        """獲取策略引擎狀態"""
        return {
            'is_running': self.is_running,
            'strategy_type': self.strategy_type,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'signals_count': len(self.current_signals),
            'parameters': self.parameters
        }
    
    def get_signals(self) -> List[Dict]:
        """獲取當前信號"""
        return self.current_signals[-10:]  # 返回最近10個信號
    
    def get_trade_records(self) -> List[str]:
        """獲取交易記錄"""
        return self.trade_records[-20:]  # 返回最近20條記錄
    
    def clear_signals(self):
        """清除信號"""
        self.current_signals.clear()
        logger.info("信號已清除")
    
    def get_yellow_stocks(self) -> List[Dict]:
        """獲取黃柱股票（用於前端顯示）"""
        try:
            return self.yahoo_service.scan_yellow_column_stocks(max_stocks=10)
        except Exception as e:
            logger.error(f"獲取黃柱股票錯誤: {str(e)}")
            return []

