"""
策略相關路由 - 整合Yahoo Finance實際數據和交易時間管理
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import random

# 導入新的策略引擎
from services.strategy_engine_new import StrategyEngine
from services.yahoo_finance_fixed import YahooFinanceService
from services.trading_time_manager import TradingTimeManager

logger = logging.getLogger(__name__)

strategy_bp = Blueprint('strategy', __name__)

# 全局策略引擎實例
strategy_engine = StrategyEngine()
yahoo_service = YahooFinanceService()
trading_time_manager = TradingTimeManager()

@strategy_bp.route('/start', methods=['POST'])
def start_strategy():
    """啟動策略"""
    try:
        data = request.get_json() or {}
        strategy_type = data.get('strategy_type', 'type1')
        
        # 檢查交易時間
        can_trade, reason = trading_time_manager.should_allow_trading(strategy_type)
        trading_status = trading_time_manager.get_trading_status()
        
        # 設定策略類型
        strategy_engine.set_strategy_type(strategy_type)
        
        # 啟動策略（包含交易時間資訊）
        success = strategy_engine.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{strategy_type.upper()}策略已啟動 - {reason}',
                'strategy_type': strategy_type,
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'trading_status': trading_status,
                'can_trade': can_trade,
                'reason': reason
            })
        else:
            return jsonify({
                'success': False,
                'message': '策略啟動失敗，可能已在運行中'
            }), 400
            
    except Exception as e:
        logger.error(f"啟動策略錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'啟動策略時發生錯誤: {str(e)}'
        }), 500

@strategy_bp.route('/stop', methods=['POST'])
def stop_strategy():
    """停止策略"""
    try:
        success = strategy_engine.stop()
        
        if success:
            return jsonify({
                'success': True,
                'message': '策略已停止'
            })
        else:
            return jsonify({
                'success': False,
                'message': '策略停止失敗，可能未在運行'
            }), 400
            
    except Exception as e:
        logger.error(f"停止策略錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'停止策略時發生錯誤: {str(e)}'
        }), 500

@strategy_bp.route('/status', methods=['GET'])
def get_strategy_status():
    """獲取策略狀態"""
    try:
        # 獲取策略引擎狀態
        engine_status = strategy_engine.get_status()
        
        # 獲取交易時間狀態
        trading_status = trading_time_manager.get_trading_status()
        
        # 檢查當前策略是否可以交易
        can_trade, reason = trading_time_manager.should_allow_trading(engine_status['strategy_type'])
        
        return jsonify({
            'success': True,
            'strategy_status': engine_status,
            'trading_status': trading_status,
            'can_trade': can_trade,
            'reason': reason,
            'market_hours': trading_time_manager.get_market_hours_info()
        })
        
    except Exception as e:
        logger.error(f"獲取策略狀態錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/trading-time', methods=['GET'])
def get_trading_time_status():
    """獲取交易時間狀態"""
    try:
        trading_status = trading_time_manager.get_trading_status()
        market_hours = trading_time_manager.get_market_hours_info()
        
        return jsonify({
            'success': True,
            'trading_status': trading_status,
            'market_hours': market_hours
        })
        
    except Exception as e:
        logger.error(f"獲取交易時間狀態錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/parameters', methods=['GET', 'POST'])
def handle_strategy_parameters():
    """處理策略參數"""
    try:
        if request.method == 'GET':
            # 獲取當前參數
            status = strategy_engine.get_status()
            return jsonify({
                'success': True,
                'parameters': status['parameters']
            })
        
        elif request.method == 'POST':
            # 更新參數
            data = request.get_json() or {}
            strategy_engine.update_parameters(data)
            
            return jsonify({
                'success': True,
                'message': '策略參數已更新',
                'parameters': data
            })
            
    except Exception as e:
        logger.error(f"處理策略參數錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/signals', methods=['GET'])
def get_current_signals():
    """獲取當前信號"""
    try:
        signals = strategy_engine.get_current_signals()
        
        return jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"獲取當前信號錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/scan', methods=['POST'])
def scan_stocks():
    """手動掃描股票"""
    try:
        data = request.get_json() or {}
        strategy_type = data.get('strategy_type', 'type1')
        max_stocks = data.get('max_stocks', 8)
        
        # 檢查交易時間
        can_trade, reason = trading_time_manager.should_allow_trading(strategy_type)
        
        logger.info(f"開始手動掃描 - 策略: {strategy_type}, 最大數量: {max_stocks}")
        logger.info(f"交易狀態: {reason}")
        
        if strategy_type.lower() == 'type1':
            # TYPE1 黃柱策略掃描
            results = yahoo_service.scan_yellow_column_stocks(max_stocks)
        else:
            # 其他策略的模擬掃描
            results = _generate_mock_scan_results(strategy_type, max_stocks)
        
        return jsonify({
            'success': True,
            'strategy_type': strategy_type,
            'results': results,
            'count': len(results),
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trading_status': {
                'can_trade': can_trade,
                'reason': reason
            }
        })
        
    except Exception as e:
        logger.error(f"掃描股票錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _generate_mock_scan_results(strategy_type: str, max_stocks: int) -> list:
    """生成模擬掃描結果"""
    mock_stocks = ["2330", "2317", "2454", "2881", "6505"]
    results = []
    
    for i, stock_code in enumerate(mock_stocks[:max_stocks]):
        result = {
            'symbol': f"{stock_code}.TW",
            'name': stock_code,
            'close_price': round(random.uniform(100, 500), 2),
            'price_change_pct': round(random.uniform(-5, 5), 2),
            'volume': random.randint(10000, 100000) * 1000,
            'volume_ratio': round(random.uniform(0.8, 3.0), 2),
            'money_flow': round(random.uniform(-10, 20), 2),
            'signal_strength': random.choice(['強', '中', '弱']),
            'strategy_type': strategy_type,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'data_source': 'mock'
        }
        results.append(result)
    
    return results

@strategy_bp.route('/records', methods=['GET'])
def get_trade_records():
    """獲取交易記錄"""
    try:
        records = strategy_engine.get_trade_records()
        
        return jsonify({
            'success': True,
            'records': records,
            'count': len(records)
        })
        
    except Exception as e:
        logger.error(f"獲取交易記錄錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/strategy-types', methods=['GET'])
def get_strategy_types():
    """獲取可用的策略類型"""
    try:
        strategy_types = [
            {
                'id': 'type1',
                'name': 'TYPE1 - 黃柱策略',
                'description': '基於黃柱信號的交易策略，篩選符合黃柱條件的股票',
                'trading_hours': '盤前、交易時間、盤後'
            },
            {
                'id': 'type2',
                'name': 'TYPE2 - 量價策略',
                'description': '基於量價關係的交易策略，關注成交量與價格的配合',
                'trading_hours': '僅交易時間'
            },
            {
                'id': 'type3',
                'name': 'TYPE3 - 資金流策略',
                'description': '基於資金流向的交易策略，追蹤主力資金動向',
                'trading_hours': '僅交易時間'
            },
            {
                'id': 'type4',
                'name': 'TYPE4 - 綜合策略',
                'description': '綜合多種指標的交易策略，提供全面的市場分析',
                'trading_hours': '僅交易時間'
            }
        ]
        
        return jsonify({
            'success': True,
            'strategy_types': strategy_types
        })
        
    except Exception as e:
        logger.error(f"獲取策略類型錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/current-strategy', methods=['GET'])
def get_current_strategy():
    """獲取當前策略"""
    try:
        status = strategy_engine.get_status()
        return jsonify({
            'success': True,
            'current_strategy': status['strategy_type'],
            'is_running': status['is_running']
        })
        
    except Exception as e:
        logger.error(f"獲取當前策略錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
