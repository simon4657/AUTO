"""
Yahoo Finance 數據服務
用於獲取台股上市股票的實際資訊
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class YahooFinanceService:
    """Yahoo Finance 數據服務類"""
    
    def __init__(self):
        self.taiwan_stocks = self._load_taiwan_stocks()
    
    def _load_taiwan_stocks(self) -> List[str]:
        """載入台股上市股票代碼列表"""
        # 台股主要上市股票代碼（前100大）
        stocks = [
            "2330.TW", "2317.TW", "2454.TW", "2881.TW", "6505.TW",  # 台積電、鴻海、聯發科、富邦金、台塑化
            "2382.TW", "2308.TW", "2303.TW", "2002.TW", "5880.TW",  # 廣達、台達電、聯電、中鋼、合庫金
            "2886.TW", "2891.TW", "2412.TW", "2207.TW", "2379.TW",  # 兆豐金、中信金、中華電、和泰車、瑞昱
            "2884.TW", "2892.TW", "2357.TW", "1303.TW", "2395.TW",  # 玉山金、第一金、華碩、南亞、研華
            "3711.TW", "2409.TW", "2474.TW", "1301.TW", "2408.TW",  # 日月光投控、友達、可成、台塑、南亞科
            "2885.TW", "2890.TW", "2883.TW", "2887.TW", "2880.TW",  # 元大金、永豐金、開發金、台新金、華南金
            "1216.TW", "2301.TW", "2105.TW", "3008.TW", "2344.TW",  # 統一、光寶科、正新、大立光、華邦電
            "2327.TW", "1101.TW", "2609.TW", "2615.TW", "1102.TW",  # 國巨、台泥、陽明、萬海、亞泥
            "2356.TW", "2324.TW", "2360.TW", "2347.TW", "2353.TW",  # 英業達、仁寶、致茂、聯強、宏碁
            "2377.TW", "2376.TW", "2354.TW", "2351.TW", "2352.TW"   # 微星、技嘉、鴻準、順德、佳世達
        ]
        return stocks
    
    def get_stock_data(self, symbol: str, period: str = "1mo") -> Optional[pd.DataFrame]:
        """
        獲取股票數據
        
        Args:
            symbol: 股票代碼 (例如: "2330.TW")
            period: 時間週期 ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
        
        Returns:
            DataFrame: 包含OHLCV數據的DataFrame
        """
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period=period)
            
            if data.empty:
                logger.warning(f"No data found for symbol: {symbol}")
                return None
                
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def get_multiple_stocks_data(self, symbols: List[str], period: str = "1mo") -> Dict[str, pd.DataFrame]:
        """
        批量獲取多個股票數據
        
        Args:
            symbols: 股票代碼列表
            period: 時間週期
        
        Returns:
            Dict: 股票代碼為key，DataFrame為value的字典
        """
        results = {}
        
        for symbol in symbols:
            data = self.get_stock_data(symbol, period)
            if data is not None:
                results[symbol] = data
                
        return results
    
    def calculate_volume_ratio(self, data: pd.DataFrame, days: int = 20) -> float:
        """
        計算量比 (當日成交量 / 過去N日平均成交量)
        
        Args:
            data: 股票數據DataFrame
            days: 計算平均的天數
        
        Returns:
            float: 量比值
        """
        if len(data) < days + 1:
            return 0.0
            
        current_volume = data['Volume'].iloc[-1]
        avg_volume = data['Volume'].iloc[-days-1:-1].mean()
        
        if avg_volume == 0:
            return 0.0
            
        return current_volume / avg_volume
    
    def calculate_money_flow(self, data: pd.DataFrame) -> float:
        """
        計算資金流向 (簡化版本)
        
        Args:
            data: 股票數據DataFrame
        
        Returns:
            float: 資金流向百分比
        """
        if len(data) < 2:
            return 0.0
            
        # 簡化的資金流向計算：基於價格變化和成交量
        price_change = (data['Close'].iloc[-1] - data['Close'].iloc[-2]) / data['Close'].iloc[-2]
        volume_ratio = self.calculate_volume_ratio(data)
        
        # 資金流向 = 價格變化 * 量比 * 100
        money_flow = price_change * volume_ratio * 100
        
        return money_flow
    
    def calculate_yellow_column_indicator(self, data: pd.DataFrame) -> bool:
        """
        計算黃柱指標 (TYPE1策略核心)
        
        黃柱條件：
        1. 當日收盤價 > 開盤價 (紅K)
        2. 成交量 > 20日平均成交量的1.5倍
        3. 價格漲幅 > 2%
        4. 資金流向為正
        
        Args:
            data: 股票數據DataFrame
        
        Returns:
            bool: 是否符合黃柱條件
        """
        if len(data) < 21:  # 需要至少21天數據來計算20日平均
            return False
            
        latest = data.iloc[-1]
        previous = data.iloc[-2]
        
        # 條件1: 紅K (收盤價 > 開盤價)
        is_red_candle = latest['Close'] > latest['Open']
        
        # 條件2: 成交量 > 20日平均成交量的1.5倍
        avg_volume_20 = data['Volume'].iloc[-21:-1].mean()
        volume_condition = latest['Volume'] > (avg_volume_20 * 1.5)
        
        # 條件3: 價格漲幅 > 2%
        price_change_pct = ((latest['Close'] - previous['Close']) / previous['Close']) * 100
        price_condition = price_change_pct > 2.0
        
        # 條件4: 資金流向為正
        money_flow = self.calculate_money_flow(data)
        money_flow_condition = money_flow > 0
        
        # 所有條件都滿足才是黃柱
        is_yellow_column = is_red_candle and volume_condition and price_condition and money_flow_condition
        
        logger.info(f"Yellow column check - Red: {is_red_candle}, Volume: {volume_condition}, "
                   f"Price: {price_condition} ({price_change_pct:.2f}%), Money flow: {money_flow_condition} ({money_flow:.2f})")
        
        return is_yellow_column
    
    def scan_yellow_column_stocks(self, max_stocks: int = 50) -> List[Dict]:
        """
        掃描符合黃柱條件的股票
        
        Args:
            max_stocks: 最大掃描股票數量
        
        Returns:
            List[Dict]: 符合條件的股票列表
        """
        yellow_stocks = []
        scanned_count = 0
        
        logger.info(f"開始掃描黃柱股票，最大掃描數量: {max_stocks}")
        
        for symbol in self.taiwan_stocks[:max_stocks]:
            try:
                scanned_count += 1
                logger.info(f"掃描進度: {scanned_count}/{max_stocks} - {symbol}")
                
                data = self.get_stock_data(symbol, period="2mo")  # 獲取2個月數據確保有足夠的歷史數據
                
                if data is None or len(data) < 21:
                    continue
                
                if self.calculate_yellow_column_indicator(data):
                    latest = data.iloc[-1]
                    previous = data.iloc[-2]
                    
                    stock_info = {
                        'symbol': symbol,
                        'name': symbol.replace('.TW', ''),
                        'close_price': float(latest['Close']),
                        'open_price': float(latest['Open']),
                        'high_price': float(latest['High']),
                        'low_price': float(latest['Low']),
                        'volume': int(latest['Volume']),
                        'volume_ratio': self.calculate_volume_ratio(data),
                        'price_change_pct': ((latest['Close'] - previous['Close']) / previous['Close']) * 100,
                        'money_flow': self.calculate_money_flow(data),
                        'date': latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)
                    }
                    
                    yellow_stocks.append(stock_info)
                    logger.info(f"發現黃柱股票: {symbol} - 價格: {stock_info['close_price']}, 漲幅: {stock_info['price_change_pct']:.2f}%")
                
            except Exception as e:
                logger.error(f"掃描股票 {symbol} 時發生錯誤: {str(e)}")
                continue
        
        logger.info(f"黃柱掃描完成，共發現 {len(yellow_stocks)} 支符合條件的股票")
        return yellow_stocks
    
    def get_stock_realtime_info(self, symbol: str) -> Optional[Dict]:
        """
        獲取股票即時資訊
        
        Args:
            symbol: 股票代碼
        
        Returns:
            Dict: 股票即時資訊
        """
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            data = self.get_stock_data(symbol, period="5d")
            
            if data is None or len(data) == 0:
                return None
            
            latest = data.iloc[-1]
            previous = data.iloc[-2] if len(data) > 1 else latest
            
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': float(latest['Close']),
                'open_price': float(latest['Open']),
                'high_price': float(latest['High']),
                'low_price': float(latest['Low']),
                'volume': int(latest['Volume']),
                'volume_ratio': self.calculate_volume_ratio(data),
                'price_change': float(latest['Close'] - previous['Close']),
                'price_change_pct': ((latest['Close'] - previous['Close']) / previous['Close']) * 100,
                'money_flow': self.calculate_money_flow(data),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"獲取股票 {symbol} 即時資訊時發生錯誤: {str(e)}")
            return None

