"""
台灣股市交易時間管理器
管理台股交易時間、休市日期和交易狀態
"""

import pytz
from datetime import datetime, time, date
from typing import Dict, List, Tuple, Optional
import logging
import requests
import json

logger = logging.getLogger(__name__)

class TradingTimeManager:
    """台灣股市交易時間管理器"""
    
    def __init__(self):
        self.taiwan_tz = pytz.timezone('Asia/Taipei')
        
        # 台股交易時間設定
        self.trading_sessions = {
            'morning': {
                'start': time(9, 0),    # 09:00
                'end': time(12, 0)      # 12:00
            },
            'afternoon': {
                'start': time(13, 30),  # 13:30
                'end': time(13, 30)     # 13:30 (收盤)
            }
        }
        
        # 盤前盤後時間
        self.pre_market = {
            'start': time(8, 30),   # 08:30 盤前
            'end': time(9, 0)       # 09:00
        }
        
        self.after_market = {
            'start': time(13, 30),  # 13:30 收盤後
            'end': time(14, 30)     # 14:30 盤後
        }
        
        # 2025年台股休市日期（主要節日）
        self.holidays_2025 = [
            date(2025, 1, 1),   # 元旦
            date(2025, 1, 27),  # 農曆除夕前一日
            date(2025, 1, 28),  # 農曆除夕
            date(2025, 1, 29),  # 農曆初一
            date(2025, 1, 30),  # 農曆初二
            date(2025, 1, 31),  # 農曆初三
            date(2025, 2, 28),  # 和平紀念日
            date(2025, 4, 4),   # 兒童節
            date(2025, 4, 5),   # 清明節
            date(2025, 5, 1),   # 勞動節
            date(2025, 5, 31),  # 端午節
            date(2025, 10, 6),  # 中秋節
            date(2025, 10, 10), # 國慶日
        ]
    
    def get_current_taiwan_time(self) -> datetime:
        """獲取當前台灣時間"""
        return datetime.now(self.taiwan_tz)
    
    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """
        檢查是否為交易日
        
        Args:
            check_date: 要檢查的日期，預設為今日
            
        Returns:
            bool: 是否為交易日
        """
        if check_date is None:
            check_date = self.get_current_taiwan_time().date()
        
        # 檢查是否為週末
        if check_date.weekday() >= 5:  # 週六(5)、週日(6)
            return False
        
        # 檢查是否為國定假日
        if check_date in self.holidays_2025:
            return False
        
        return True
    
    def is_trading_hours(self, check_time: Optional[datetime] = None) -> bool:
        """
        檢查是否在交易時間內
        
        Args:
            check_time: 要檢查的時間，預設為現在
            
        Returns:
            bool: 是否在交易時間內
        """
        if check_time is None:
            check_time = self.get_current_taiwan_time()
        
        # 檢查是否為交易日
        if not self.is_trading_day(check_time.date()):
            return False
        
        current_time = check_time.time()
        
        # 檢查上午交易時間 (09:00-12:00)
        morning_start = self.trading_sessions['morning']['start']
        morning_end = self.trading_sessions['morning']['end']
        
        if morning_start <= current_time <= morning_end:
            return True
        
        # 檢查下午交易時間 (13:30-13:30，實際上只有開盤瞬間)
        # 台股下午只有13:30開盤，沒有下午交易時段
        afternoon_time = self.trading_sessions['afternoon']['start']
        
        # 給予13:30前後1分鐘的緩衝時間
        if time(13, 29) <= current_time <= time(13, 31):
            return True
        
        return False
    
    def is_pre_market_hours(self, check_time: Optional[datetime] = None) -> bool:
        """檢查是否在盤前時間"""
        if check_time is None:
            check_time = self.get_current_taiwan_time()
        
        if not self.is_trading_day(check_time.date()):
            return False
        
        current_time = check_time.time()
        return self.pre_market['start'] <= current_time < self.pre_market['end']
    
    def is_after_market_hours(self, check_time: Optional[datetime] = None) -> bool:
        """檢查是否在盤後時間"""
        if check_time is None:
            check_time = self.get_current_taiwan_time()
        
        if not self.is_trading_day(check_time.date()):
            return False
        
        current_time = check_time.time()
        return self.after_market['start'] <= current_time <= self.after_market['end']
    
    def get_trading_status(self, check_time: Optional[datetime] = None) -> Dict:
        """
        獲取詳細的交易狀態資訊
        
        Args:
            check_time: 要檢查的時間，預設為現在
            
        Returns:
            Dict: 交易狀態資訊
        """
        if check_time is None:
            check_time = self.get_current_taiwan_time()
        
        current_date = check_time.date()
        current_time = check_time.time()
        
        is_trading_day = self.is_trading_day(current_date)
        is_trading = self.is_trading_hours(check_time)
        is_pre_market = self.is_pre_market_hours(check_time)
        is_after_market = self.is_after_market_hours(check_time)
        
        # 判斷市場狀態
        if not is_trading_day:
            if current_date.weekday() >= 5:
                market_status = "週末休市"
            else:
                market_status = "國定假日休市"
        elif is_pre_market:
            market_status = "盤前準備"
        elif is_trading:
            if time(9, 0) <= current_time <= time(12, 0):
                market_status = "上午交易中"
            else:
                market_status = "下午收盤"
        elif is_after_market:
            market_status = "盤後時間"
        elif current_time < time(8, 30):
            market_status = "開市前"
        elif time(12, 0) < current_time < time(13, 30):
            market_status = "午休時間"
        else:
            market_status = "收市後"
        
        # 計算下一個交易時段
        next_session = self._get_next_trading_session(check_time)
        
        return {
            'current_time': check_time.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': 'Asia/Taipei',
            'is_trading_day': is_trading_day,
            'is_trading_hours': is_trading,
            'is_pre_market': is_pre_market,
            'is_after_market': is_after_market,
            'market_status': market_status,
            'weekday': check_time.strftime('%A'),
            'trading_sessions': {
                'morning': f"{self.trading_sessions['morning']['start'].strftime('%H:%M')}-{self.trading_sessions['morning']['end'].strftime('%H:%M')}",
                'afternoon_close': self.trading_sessions['afternoon']['start'].strftime('%H:%M')
            },
            'next_session': next_session
        }
    
    def _get_next_trading_session(self, current_time: datetime) -> Dict:
        """獲取下一個交易時段資訊"""
        current_date = current_time.date()
        current_time_only = current_time.time()
        
        # 如果是交易日
        if self.is_trading_day(current_date):
            # 如果還沒到上午開盤
            if current_time_only < self.trading_sessions['morning']['start']:
                return {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'session': '上午開盤',
                    'time': self.trading_sessions['morning']['start'].strftime('%H:%M')
                }
            # 如果在上午交易時間內
            elif current_time_only <= self.trading_sessions['morning']['end']:
                return {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'session': '上午收盤',
                    'time': self.trading_sessions['morning']['end'].strftime('%H:%M')
                }
            # 如果在午休時間
            elif current_time_only < self.trading_sessions['afternoon']['start']:
                return {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'session': '下午收盤',
                    'time': self.trading_sessions['afternoon']['start'].strftime('%H:%M')
                }
        
        # 尋找下一個交易日
        next_trading_date = self._get_next_trading_date(current_date)
        return {
            'date': next_trading_date.strftime('%Y-%m-%d'),
            'session': '上午開盤',
            'time': self.trading_sessions['morning']['start'].strftime('%H:%M')
        }
    
    def _get_next_trading_date(self, current_date: date) -> date:
        """獲取下一個交易日"""
        check_date = current_date
        for _ in range(10):  # 最多檢查10天
            check_date = date(check_date.year, check_date.month, check_date.day)
            # 加一天
            if check_date.month == 12 and check_date.day == 31:
                check_date = date(check_date.year + 1, 1, 1)
            elif check_date.day == 28 and check_date.month == 2:  # 簡化的2月處理
                check_date = date(check_date.year, 3, 1)
            elif check_date.day == 30 and check_date.month in [4, 6, 9, 11]:
                check_date = date(check_date.year, check_date.month + 1, 1)
            elif check_date.day == 31:
                check_date = date(check_date.year, check_date.month + 1, 1)
            else:
                check_date = date(check_date.year, check_date.month, check_date.day + 1)
            
            if self.is_trading_day(check_date):
                return check_date
        
        # 如果找不到，返回當前日期加1天
        return date(current_date.year, current_date.month, current_date.day + 1)
    
    def get_market_hours_info(self) -> Dict:
        """獲取市場交易時間資訊"""
        return {
            'market_name': '台灣證券交易所',
            'timezone': 'Asia/Taipei (UTC+8)',
            'trading_days': '週一至週五（除國定假日）',
            'trading_hours': {
                'morning_session': {
                    'start': '09:00',
                    'end': '12:00',
                    'description': '上午交易時段'
                },
                'afternoon_close': {
                    'time': '13:30',
                    'description': '下午收盤'
                }
            },
            'pre_market': {
                'start': '08:30',
                'end': '09:00',
                'description': '盤前準備時間'
            },
            'lunch_break': {
                'start': '12:00',
                'end': '13:30',
                'description': '午休時間'
            },
            'after_market': {
                'start': '13:30',
                'end': '14:30',
                'description': '盤後時間'
            }
        }
    
    def should_allow_trading(self, strategy_type: str = "type1") -> Tuple[bool, str]:
        """
        根據策略類型判斷是否允許交易
        
        Args:
            strategy_type: 策略類型
            
        Returns:
            Tuple[bool, str]: (是否允許交易, 原因說明)
        """
        current_time = self.get_current_taiwan_time()
        trading_status = self.get_trading_status(current_time)
        
        # TYPE1 黃柱策略：可以在盤前、交易時間和盤後運行
        if strategy_type.lower() == "type1":
            if trading_status['is_trading_day']:
                if (trading_status['is_pre_market'] or 
                    trading_status['is_trading_hours'] or 
                    trading_status['is_after_market']):
                    return True, f"TYPE1策略運行中 - {trading_status['market_status']}"
                else:
                    return False, f"非交易時段 - {trading_status['market_status']}"
            else:
                return False, f"非交易日 - {trading_status['market_status']}"
        
        # 其他策略：僅在交易時間運行
        else:
            if trading_status['is_trading_hours']:
                return True, f"{strategy_type.upper()}策略運行中 - {trading_status['market_status']}"
            else:
                return False, f"非交易時間 - {trading_status['market_status']}"
