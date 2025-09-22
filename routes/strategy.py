"""
策略控制API路由
提供策略引擎的控制和監控接口
"""

from flask import Blueprint, request, jsonify
from models.user import db
from models.trading import SystemLog
from services.broker_adapter import create_broker_adapter
from services.risk_manager import RiskManager
from services.signal_processor import create_signal_processor
from services.strategy_engine import StrategyEngine
from datetime import datetime
import logging

strategy_bp = Blueprint('strategy', __name__)

# 全局策略引擎實例
strategy_engine = None

def get_strategy_engine():
    """獲取策略引擎實例"""
    global strategy_engine
    if strategy_engine is None:
        # 創建服務實例
        broker = create_broker_adapter('mock')  # 默認使用模擬券商
        risk_manager = RiskManager()
        signal_processor = create_signal_processor('mock')  # 默認使用模擬信號
        
        strategy_engine = StrategyEngine(broker, risk_manager, signal_processor)
    
    return strategy_engine

@strategy_bp.route('/start', methods=['POST'])
def start_strategy():
    """啟動策略引擎"""
    try:
        data = request.get_json() or {}
        strategy_type = data.get('strategy_type', 'type1')
        
        engine = get_strategy_engine()
        
        if engine.is_running:
            return jsonify({
                'success': False,
                'message': '策略引擎已在運行中'
            }), 400
        
        # 設置策略類型
        engine.strategy_type = strategy_type
        engine.start()
        
        # 記錄策略啟動
        log = SystemLog(
            level='INFO',
            message=f'策略引擎已啟動: {strategy_type}',
            module='strategy_control'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'策略引擎已啟動 ({strategy_type})',
            'data': {
                'strategy_type': strategy_type,
                'is_running': True
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/stop', methods=['POST'])
def stop_strategy():
    """停止策略引擎"""
    try:
        engine = get_strategy_engine()
        
        if not engine.is_running:
            return jsonify({
                'success': False,
                'message': '策略引擎未在運行'
            }), 400
        
        engine.stop()
        
        return jsonify({
            'success': True,
            'message': '策略引擎已停止'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/status', methods=['GET'])
def get_strategy_status():
    """獲取策略引擎狀態"""
    try:
        engine = get_strategy_engine()
        
        return jsonify({
            'success': True,
            'data': {
                'is_running': engine.is_running,
                'broker_type': type(engine.broker).__name__,
                'last_check': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/run-cycle', methods=['POST'])
def run_strategy_cycle():
    """手動執行一次策略週期"""
    try:
        engine = get_strategy_engine()
        
        # 臨時啟動引擎以執行週期
        was_running = engine.is_running
        if not was_running:
            engine.is_running = True
        
        results = engine.run_single_cycle()
        
        # 恢復原始狀態
        if not was_running:
            engine.is_running = False
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/evaluate-signals', methods=['POST'])
def evaluate_signals():
    """手動評估當前信號"""
    try:
        engine = get_strategy_engine()
        
        # 臨時啟動引擎以評估信號
        was_running = engine.is_running
        if not was_running:
            engine.is_running = True
        
        buy_decisions = engine.evaluate_buy_signals()
        
        # 恢復原始狀態
        if not was_running:
            engine.is_running = False
        
        return jsonify({
            'success': True,
            'data': {
                'buy_decisions': len(buy_decisions),
                'decisions': buy_decisions
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/monitor-positions', methods=['POST'])
def monitor_positions():
    """手動監控持倉"""
    try:
        engine = get_strategy_engine()
        
        # 臨時啟動引擎以監控持倉
        was_running = engine.is_running
        if not was_running:
            engine.is_running = True
        
        sell_decisions = engine.monitor_positions_for_sell()
        
        # 恢復原始狀態
        if not was_running:
            engine.is_running = False
        
        return jsonify({
            'success': True,
            'data': {
                'sell_decisions': len(sell_decisions),
                'decisions': sell_decisions
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/broker-config', methods=['GET'])
def get_broker_config():
    """獲取券商配置"""
    try:
        engine = get_strategy_engine()
        
        # 獲取券商信息
        account_info = engine.broker.get_account_info()
        balance_info = engine.broker.get_balance()
        
        return jsonify({
            'success': True,
            'data': {
                'account_info': account_info,
                'balance_info': balance_info,
                'broker_type': type(engine.broker).__name__
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/broker-config', methods=['PUT'])
def update_broker_config():
    """更新券商配置"""
    try:
        data = request.get_json()
        broker_type = data.get('broker_type', 'mock')
        
        # 重新創建策略引擎
        global strategy_engine
        
        broker = create_broker_adapter(broker_type, **data.get('broker_config', {}))
        risk_manager = RiskManager()
        signal_processor = create_signal_processor(
            data.get('signal_processor_type', 'mock'),
            **data.get('signal_config', {})
        )
        
        strategy_engine = StrategyEngine(broker, risk_manager, signal_processor)
        
        # 記錄配置更新
        log = SystemLog(
            level='INFO',
            message=f'券商配置已更新: {broker_type}',
            module='strategy_config'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '券商配置已更新'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/test-broker', methods=['POST'])
def test_broker_connection():
    """測試券商連接"""
    try:
        engine = get_strategy_engine()
        
        # 測試認證
        auth_result = engine.broker.authenticate()
        
        if auth_result:
            # 測試基本功能
            account_info = engine.broker.get_account_info()
            balance_info = engine.broker.get_balance()
            
            return jsonify({
                'success': True,
                'data': {
                    'authentication': True,
                    'account_info': account_info,
                    'balance_info': balance_info
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '券商認證失敗'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/risk-stats', methods=['GET'])
def get_risk_statistics():
    """獲取風險統計"""
    try:
        engine = get_strategy_engine()
        risk_stats = engine.risk_manager.get_risk_statistics()
        
        return jsonify({
            'success': True,
            'data': risk_stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@strategy_bp.route('/account-info', methods=['GET'])
def get_account_info():
    """獲取帳戶資訊"""
    try:
        engine = get_strategy_engine()
        
        # 獲取帳戶基本資訊
        account_info = engine.broker.get_account_info()
        balance_info = engine.broker.get_balance()
        
        # 模擬即時帳戶資訊
        import random
        account_data = {
            'total_equity': balance_info.get('total_equity', 1000000 + random.randint(-50000, 100000)),
            'available_funds': balance_info.get('available_funds', 500000 + random.randint(-25000, 50000)),
            'position_value': balance_info.get('position_value', 300000 + random.randint(-15000, 30000)),
            'today_pnl': random.randint(-20000, 20000),
            'total_pnl': random.randint(-50000, 50000),
            'position_count': random.randint(0, 10),
            'account_id': account_info.get('account_id', 'DEMO001'),
            'last_update': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': account_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/trade-log', methods=['GET'])
def get_trade_log():
    """獲取交易記錄"""
    try:
        # 獲取查詢參數
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 模擬交易記錄
        import random
        from datetime import datetime, timedelta
        
        trade_types = ['buy', 'sell', 'info']
        messages = [
            '掃描到符合條件股票: 2330',
            '買入 2330 1000股 @580.0',
            '賣出 2454 500股 @125.5',
            '停利觸發: 2317 +2.5%',
            '停損觸發: 2382 -1.8%',
            '策略信號: Type1 黃柱出現',
            '風險檢查通過',
            '下單成功: 訂單號 #12345',
            '成交回報: 2330 部分成交 500股'
        ]
        
        logs = []
        for i in range(limit):
            log_time = datetime.now() - timedelta(minutes=random.randint(0, 1440))
            logs.append({
                'id': offset + i + 1,
                'timestamp': log_time.isoformat(),
                'type': random.choice(trade_types),
                'message': random.choice(messages),
                'time_str': log_time.strftime('%H:%M:%S')
            })
        
        return jsonify({
            'success': True,
            'data': {
                'logs': logs,
                'total': 1000,  # 模擬總記錄數
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
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
                'name': 'Type1 - 黃柱策略',
                'description': '基於黃柱信號的交易策略',
                'parameters': ['min_volume_shares', 'min_volume_ratio']
            },
            {
                'id': 'type2',
                'name': 'Type2 - 量價策略',
                'description': '基於量價關係的交易策略',
                'parameters': ['min_volume_shares', 'min_volume_ratio', 'min_money_flow']
            },
            {
                'id': 'type3',
                'name': 'Type3 - 資金流策略',
                'description': '基於資金流向的交易策略',
                'parameters': ['min_money_flow', 'take_profit_pct', 'stop_loss_pct']
            },
            {
                'id': 'type4',
                'name': 'Type4 - 綜合策略',
                'description': '綜合多種指標的交易策略',
                'parameters': ['min_volume_shares', 'min_volume_ratio', 'min_money_flow', 'take_profit_pct', 'stop_loss_pct']
            }
        ]
        
        return jsonify({
            'success': True,
            'data': strategy_types
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@strategy_bp.route('/current-strategy', methods=['GET'])
def get_current_strategy():
    """獲取當前策略資訊"""
    try:
        engine = get_strategy_engine()
        
        current_strategy = getattr(engine, 'strategy_type', 'type1')
        
        return jsonify({
            'success': True,
            'data': {
                'strategy_type': current_strategy,
                'is_running': engine.is_running,
                'start_time': getattr(engine, 'start_time', None),
                'last_update': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

