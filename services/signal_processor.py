"""
信號處理服務
負責從股票篩選器獲取黃柱信號，並進行初步處理
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from models.trading import SignalHistory
from models.user import db

logger = logging.getLogger(__name__)

class SignalProcessor:
    """信號處理器"""
    
    def __init__(self, screener_url: str = "http://localhost:5000"):
        self.screener_url = screener_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def fetch_yellow_candle_signals(self) -> List[Dict[str, Any]]:
        """從股票篩選器獲取黃柱信號"""
        try:
            # 調用現有的股票篩選器API
            response = self.session.get(f"{self.screener_url}/api/screen")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    signals = []
                    for stock in data['data']:
                        # 轉換篩選器的數據格式為信號格式
                        signal = {
                            'stock_code': stock.get('股票代碼', ''),
                            'stock_name': stock.get('股票名稱', ''),
                            'signal_type': 'YELLOW_CANDLE',
                            'volume_shares': self._parse_volume(stock.get('成交張數', '0')),
                            'volume_ratio': self._parse_decimal(stock.get('量比', '0')),
                            'money_flow': self._parse_decimal(stock.get('資金流向', '0')),
                            'current_price': self._parse_decimal(stock.get('收盤價', '0')),
                            'price_change_pct': self._parse_decimal(stock.get('漲跌幅', '0')),
                            'signal_time': datetime.now()
                        }
                        signals.append(signal)
                    
                    logger.info(f"Fetched {len(signals)} yellow candle signals")
                    return signals
                else:
                    logger.warning(f"Invalid response format from screener: {data}")
                    return []
            else:
                logger.error(f"Failed to fetch signals: HTTP {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching signals: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error while fetching signals: {e}")
            return []
    
    def process_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """處理和過濾信號"""
        processed_signals = []
        
        for signal in signals:
            try:
                # 基本數據驗證
                if not signal.get('stock_code') or not signal.get('stock_name'):
                    logger.warning(f"Invalid signal data: missing stock_code or stock_name")
                    continue
                
                # 確保股票代碼格式正確（添加.TW後綴如果沒有）
                stock_code = signal['stock_code']
                if not stock_code.endswith('.TW') and not stock_code.endswith('.TWO'):
                    # 根據股票代碼判斷市場
                    if stock_code.startswith(('1', '2', '3', '4', '5', '6', '9')):
                        stock_code += '.TW'  # 上市
                    else:
                        stock_code += '.TWO'  # 上櫃
                    signal['stock_code'] = stock_code
                
                # 保存信號到歷史記錄
                self._save_signal_to_history(signal)
                
                processed_signals.append(signal)
                
            except Exception as e:
                logger.error(f"Error processing signal {signal}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_signals)} signals")
        return processed_signals
    
    def _parse_volume(self, volume_str: str) -> int:
        """解析成交張數"""
        try:
            # 移除逗號和其他非數字字符
            clean_str = ''.join(c for c in str(volume_str) if c.isdigit())
            return int(clean_str) if clean_str else 0
        except (ValueError, TypeError):
            return 0
    
    def _parse_decimal(self, value_str: str) -> Decimal:
        """解析小數值"""
        try:
            # 移除百分號和其他非數字字符（保留小數點和負號）
            clean_str = ''.join(c for c in str(value_str) if c.isdigit() or c in '.-')
            return Decimal(clean_str) if clean_str and clean_str != '.' else Decimal('0')
        except (ValueError, TypeError, Exception):
            return Decimal('0')
    
    def _save_signal_to_history(self, signal: Dict[str, Any]):
        """保存信號到歷史記錄"""
        try:
            signal_record = SignalHistory(
                stock_code=signal['stock_code'],
                stock_name=signal['stock_name'],
                signal_type=signal['signal_type'],
                volume_shares=signal.get('volume_shares'),
                volume_ratio=signal.get('volume_ratio'),
                money_flow=signal.get('money_flow'),
                signal_time=signal.get('signal_time', datetime.now()),
                processed=False
            )
            
            db.session.add(signal_record)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to save signal to history: {e}")
            db.session.rollback()
    
    def mark_signal_processed(self, signal_id: int, action_taken: str, rejection_reason: str = None):
        """標記信號為已處理"""
        try:
            signal = SignalHistory.query.get(signal_id)
            if signal:
                signal.processed = True
                signal.action_taken = action_taken
                signal.rejection_reason = rejection_reason
                db.session.commit()
                logger.info(f"Signal {signal_id} marked as processed: {action_taken}")
        except Exception as e:
            logger.error(f"Failed to mark signal as processed: {e}")
            db.session.rollback()
    
    def get_unprocessed_signals(self) -> List[SignalHistory]:
        """獲取未處理的信號"""
        try:
            return SignalHistory.query.filter_by(processed=False).all()
        except Exception as e:
            logger.error(f"Failed to get unprocessed signals: {e}")
            return []
    
    def cleanup_old_signals(self, days_to_keep: int = 30):
        """清理舊的信號記錄"""
        try:
            cutoff_date = datetime.now() - datetime.timedelta(days=days_to_keep)
            old_signals = SignalHistory.query.filter(
                SignalHistory.signal_time < cutoff_date
            ).all()
            
            for signal in old_signals:
                db.session.delete(signal)
            
            db.session.commit()
            logger.info(f"Cleaned up {len(old_signals)} old signal records")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old signals: {e}")
            db.session.rollback()

class MockSignalProcessor(SignalProcessor):
    """模擬信號處理器，用於測試"""
    
    def __init__(self):
        super().__init__()
        self.mock_signals = [
            {
                'stock_code': '2330.TW',
                'stock_name': '台積電',
                'signal_type': 'YELLOW_CANDLE',
                'volume_shares': 15000,
                'volume_ratio': Decimal('2.5'),
                'money_flow': Decimal('50.0'),
                'current_price': Decimal('500.0'),
                'price_change_pct': Decimal('3.2'),
                'signal_time': datetime.now()
            },
            {
                'stock_code': '2454.TW',
                'stock_name': '聯發科',
                'signal_type': 'YELLOW_CANDLE',
                'volume_shares': 8000,
                'volume_ratio': Decimal('1.8'),
                'money_flow': Decimal('30.0'),
                'current_price': Decimal('800.0'),
                'price_change_pct': Decimal('2.1'),
                'signal_time': datetime.now()
            }
        ]
    
    def fetch_yellow_candle_signals(self) -> List[Dict[str, Any]]:
        """返回模擬信號"""
        logger.info(f"Returning {len(self.mock_signals)} mock signals")
        return self.mock_signals.copy()
    
    def add_mock_signal(self, stock_code: str, stock_name: str, volume_shares: int,
                       volume_ratio: float, money_flow: float):
        """添加模擬信號（測試用）"""
        signal = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'signal_type': 'YELLOW_CANDLE',
            'volume_shares': volume_shares,
            'volume_ratio': Decimal(str(volume_ratio)),
            'money_flow': Decimal(str(money_flow)),
            'current_price': Decimal('100.0'),
            'price_change_pct': Decimal('1.0'),
            'signal_time': datetime.now()
        }
        self.mock_signals.append(signal)
        logger.info(f"Added mock signal: {stock_code}")

def create_signal_processor(processor_type: str = "real", **kwargs) -> SignalProcessor:
    """信號處理器工廠函數"""
    if processor_type.lower() == 'mock':
        return MockSignalProcessor()
    else:
        return SignalProcessor(**kwargs)

