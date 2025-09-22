"""
簡化的Yahoo Finance 數據服務
移除pandas和numpy依賴，使用基本Python數據結構
"""

import yfinance as yf
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class YahooFinanceService:
    """簡化的Yahoo Finance 數據服務類"""
    
    def __init__(self):
        self.taiwan_stocks = self._load_taiwan_stocks()
    
    def _load_taiwan_stocks(self) -> List[str]:
        """載入台股上市股票代碼列表"""
        # 台股主要上市股票代碼（前50大，減少數量避免超時）
        stocks = [
            "2330.TW", "2317.TW", "2454.TW", "2881.TW", "6505.TW",  # 台積電、鴻海、聯發科、富邦金、台塑化
            "2382.TW", "2308.TW", "2303.TW", "2002.TW", "5880.TW",  # 廣達、台達電、聯電、中鋼、合庫金
            "2886.TW", "2891.TW", "2412.TW", "2207.TW", "2379.TW",  # 兆豐金、中信金、中華電、和泰車、瑞昱
            "2884.TW", "2892.TW", "2357.TW", "1303.TW", "2395.TW",  # 玉山金、第一金、華碩、南亞、研華
            "3711.TW", "2409.TW", "2474.TW", "1301.TW", "2408.TW",  # 日月光投控、友達、可成、台塑、南亞科
        ]
        return stocks
    
    def get_stock_data(self, symbol: str, period: str = "1mo"):
        """
        獲取股票數據
        
        Args:
            symbol: 股票代碼 (例如: "2330.TW")
            period: 時間週期 ("1d", "5d", "1mo", "3mo", "6mo", "1y")
        
        Returns:
            dict: 包含OHLCV數據的字典，如果失敗返回None
        """
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)
            
            if hist.empty:
                logger.warning(f"No data found for symbol: {symbol}")
                return None
            
            # 轉換為基本Python數據結構
            data = {
                'dates': [str(date.date()) for date in hist.index],
                'open': hist['Open'].tolist(),
                'high': hist['High'].tolist(),
                'low': hist['Low'].tolist(),
                'close': hist['Close'].tolist(),
                'volume': hist['Volume'].tolist()
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def calculate_volume_ratio(self, data: dict, days: int = 20) -> float:
        """
        計算量比 (當日成交量 / 過去N日平均成交量)
        
        Args:
            data: 股票數據字典
            days: 計算平均的天數
        
        Returns:
            float: 量比值
        """
        try:
            volumes = data.get('volume', [])
            if len(volumes) < days + 1:
                return 0.0
                
            current_volume = volumes[-1]
            avg_volume = sum(volumes[-days-1:-1]) / days
            
            if avg_volume == 0:
                return 0.0
                
            return current_volume / avg_volume
        except Exception as e:
            logger.error(f"Error calculating volume ratio: {str(e)}")
            return 0.0
    
    def calculate_money_flow(self, data: dict) -> float:
        """
        計算資金流向 (簡化版本)
        
        Args:
            data: 股票數據字典
        
        Returns:
            float: 資金流向百分比
        """
        try:
            closes = data.get('close', [])
            if len(closes) < 2:
                return 0.0
                
            # 簡化的資金流向計算：基於價格變化和成交量
            price_change = (closes[-1] - closes[-2]) / closes[-2]
            volume_ratio = self.calculate_volume_ratio(data)
            
            # 資金流向 = 價格變化 * 量比 * 100
            money_flow = price_change * volume_ratio * 100
            
            return money_flow
        except Exception as e:
            logger.error(f"Error calculating money flow: {str(e)}")
            return 0.0
    
    def calculate_yellow_column_indicator(self, data: dict) -> bool:
        """
        計算黃柱指標 (TYPE1策略核心)
        
        黃柱條件：
        1. 當日收盤價 > 開盤價 (紅K)
        2. 成交量 > 20日平均成交量的1.5倍
        3. 價格漲幅 > 2%
        4. 資金流向為正
        
        Args:
            data: 股票數據字典
        
        Returns:
            bool: 是否符合黃柱條件
        """
        try:
            if len(data.get('close', [])) < 21:  # 需要至少21天數據來計算20日平均
                return False
            
            opens = data['open']
            closes = data['close']
            volumes = data['volume']
            
            latest_open = opens[-1]
            latest_close = closes[-1]
            latest_volume = volumes[-1]
            previous_close = closes[-2]
            
            # 條件1: 紅K (收盤價 > 開盤價)
            is_red_candle = latest_close > latest_open
            
            # 條件2: 成交量 > 20日平均成交量的1.5倍
            avg_volume_20 = sum(volumes[-21:-1]) / 20
            volume_condition = latest_volume > (avg_volume_20 * 1.5)
            
            # 條件3: 價格漲幅 > 2%
            price_change_pct = ((latest_close - previous_close) / previous_close) * 100
            price_condition = price_change_pct > 2.0
            
            # 條件4: 資金流向為正
            money_flow = self.calculate_money_flow(data)
            money_flow_condition = money_flow > 0
            
            # 所有條件都滿足才是黃柱
            is_yellow_column = is_red_candle and volume_condition and price_condition and money_flow_condition
            
            logger.info(f"Yellow column check - Red: {is_red_candle}, Volume: {volume_condition}, "
                       f"Price: {price_condition} ({price_change_pct:.2f}%), Money flow: {money_flow_condition} ({money_flow:.2f})")
            
            return is_yellow_column
        except Exception as e:
            logger.error(f"Error calculating yellow column indicator: {str(e)}")
            return False
    
    def scan_yellow_column_stocks(self, max_stocks: int = 10) -> List[Dict]:
        """
        掃描符合黃柱條件的股票
        
        Args:
            max_stocks: 最大掃描股票數量（減少數量避免超時）
        
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
                
                if data is None or len(data.get('close', [])) < 21:
                    continue
                
                if self.calculate_yellow_column_indicator(data):
                    closes = data['close']
                    opens = data['open']
                    highs = data['high']
                    lows = data['low']
                    volumes = data['volume']
                    
                    stock_info = {
                        'symbol': symbol,
                        'name': symbol.replace('.TW', ''),
                        'close_price': closes[-1],
                        'open_price': opens[-1],
                        'high_price': highs[-1],
                        'low_price': lows[-1],
                        'volume': int(volumes[-1]),
                        'volume_ratio': self.calculate_volume_ratio(data),
                        'price_change_pct': ((closes[-1] - closes[-2]) / closes[-2]) * 100,
                        'money_flow': self.calculate_money_flow(data),
                        'date': data['dates'][-1]
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
            
            if data is None or len(data.get('close', [])) == 0:
                return None
            
            closes = data['close']
            opens = data['open']
            highs = data['high']
            lows = data['low']
            volumes = data['volume']
            
            latest_close = closes[-1]
            latest_open = opens[-1]
            latest_high = highs[-1]
            latest_low = lows[-1]
            latest_volume = volumes[-1]
            previous_close = closes[-2] if len(closes) > 1 else latest_close
            
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': latest_close,
                'open_price': latest_open,
                'high_price': latest_high,
                'low_price': latest_low,
                'volume': int(latest_volume),
                'volume_ratio': self.calculate_volume_ratio(data),
                'price_change': latest_close - previous_close,
                'price_change_pct': ((latest_close - previous_close) / previous_close) * 100,
                'money_flow': self.calculate_money_flow(data),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"獲取股票 {symbol} 即時資訊時發生錯誤: {str(e)}")
            return None

