"""
策略相關路由 - 整合Yahoo Finance實際數據
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import random

# 導入新的策略引擎
from services.strategy_engine_new import StrategyEngine
from services.yahoo_finance_robust import YahooFinanceService

logger = logging.getLogger(__name__)

strategy_bp = Blueprint('strategy', __name__)

# 全局策略引擎實例
strategy_engine = StrategyEngine()
yahoo_service = YahooFinanceService()

@strategy_bp.route('/start', methods=['POST'])
def start_strategy():
    """啟動策略"""
    try:
        data = request.get_json() or {}
        strategy_type = data.get('strategy_type', 'type1')
        
        # 設定策略類型
        strategy_engine.set_strategy_type(strategy_type)
        
        # 啟動策略
        success = strategy_engine.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{strategy_type.upper()}策略已啟動',
                'strategy_type': strategy_type,
                'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
        status = strategy_engine.get_status()
        
        # 添加額外的狀態信息
        status.update({
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'system_status': '運行中' if status['is_running'] else '已停止'
        })
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"獲取策略狀態錯誤: {str(e)}")
        return jsonify({
            'is_running': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/signals', methods=['GET'])
def get_signals():
    """獲取交易信號"""
    try:
        signals = strategy_engine.get_signals()
        return jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals)
        })
        
    except Exception as e:
        logger.error(f"獲取信號錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'signals': [],
            'error': str(e)
        }), 500

@strategy_bp.route('/yellow-stocks', methods=['GET'])
def get_yellow_stocks():
    """獲取黃柱股票"""
    try:
        yellow_stocks = strategy_engine.get_yellow_stocks()
        return jsonify({
            'success': True,
            'stocks': yellow_stocks,
            'count': len(yellow_stocks),
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"獲取黃柱股票錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'stocks': [],
            'error': str(e)
        }), 500

@strategy_bp.route('/account-info', methods=['GET'])
def get_account_info():
    """獲取帳戶資訊（模擬數據）"""
    try:
        # 模擬帳戶資訊，添加一些隨機變化
        base_equity = 1000000
        variation = random.randint(-50000, 50000)
        
        account_info = {
            'total_equity': base_equity + variation,
            'available_funds': int((base_equity + variation) * 0.5),
            'position_value': int((base_equity + variation) * 0.3),
            'today_pnl': random.randint(-10000, 15000),
            'total_pnl': random.randint(-5000, 20000),
            'position_count': random.randint(0, 8),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(account_info)
        
    except Exception as e:
        logger.error(f"獲取帳戶資訊錯誤: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@strategy_bp.route('/trade-log', methods=['GET'])
def get_trade_log():
    """獲取交易記錄"""
    try:
        trade_records = strategy_engine.get_trade_records()
        
        return jsonify({
            'success': True,
            'records': trade_records,
            'count': len(trade_records)
        })
        
    except Exception as e:
        logger.error(f"獲取交易記錄錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'records': [],
            'error': str(e)
        }), 500

@strategy_bp.route('/strategy-types', methods=['GET'])
def get_strategy_types():
    """獲取可用策略類型"""
    try:
        strategy_types = [
            {
                'id': 'type1',
                'name': 'TYPE1 - 黃柱策略',
                'description': '基於黃柱信號的交易策略，篩選符合黃柱條件的股票'
            },
            {
                'id': 'type2',
                'name': 'TYPE2 - 量價策略',
                'description': '基於量價關係的交易策略，關注成交量與價格的配合'
            },
            {
                'id': 'type3',
                'name': 'TYPE3 - 資金流策略',
                'description': '基於資金流向的交易策略，追蹤主力資金動向'
            },
            {
                'id': 'type4',
                'name': 'TYPE4 - 綜合策略',
                'description': '綜合多種指標的交易策略，提供全面的市場分析'
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

@strategy_bp.route('/update-parameters', methods=['POST'])
def update_strategy_parameters():
    """更新策略參數"""
    try:
        data = request.get_json() or {}
        
        # 更新策略引擎參數
        strategy_engine.update_parameters(data)
        
        return jsonify({
            'success': True,
            'message': '策略參數已更新',
            'parameters': strategy_engine.parameters
        })
        
    except Exception as e:
        logger.error(f"更新策略參數錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新參數時發生錯誤: {str(e)}'
        }), 500

@strategy_bp.route('/stock-info/<symbol>', methods=['GET'])
def get_stock_info(symbol):
    """獲取特定股票資訊"""
    try:
        # 確保股票代碼格式正確
        if not symbol.endswith('.TW'):
            symbol = f"{symbol}.TW"
        
        stock_info = yahoo_service.get_stock_realtime_info(symbol)
        
        if stock_info:
            return jsonify({
                'success': True,
                'stock_info': stock_info
            })
        else:
            return jsonify({
                'success': False,
                'message': f'無法獲取股票 {symbol} 的資訊'
            }), 404
            
    except Exception as e:
        logger.error(f"獲取股票資訊錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/trading-hours', methods=['GET'])
def get_trading_hours():
    """獲取台股交易時間狀態"""
    try:
        trading_status = yahoo_service.get_trading_status()
        
        return jsonify({
            'success': True,
            'data': trading_status
        })
        
    except Exception as e:
        logger.error(f"獲取交易時間狀態錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/market-status', methods=['GET'])
def get_market_status():
    """獲取市場狀態（包含交易時間和系統狀態）"""
    try:
        trading_status = yahoo_service.get_trading_status()
        strategy_status = strategy_engine.get_status()
        
        return jsonify({
            'success': True,
            'data': {
                'trading_hours': trading_status,
                'strategy_status': strategy_status,
                'system_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'can_trade': trading_status.get('is_trading_hours', False) and strategy_status.get('is_running', False)
            }
        })
        
    except Exception as e:
        logger.error(f"獲取市場狀態錯誤: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

