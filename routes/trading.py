from flask import Blueprint, request, jsonify
from models.user import db
from models.trading import TradingParameters, Position, TradeRecord, SystemLog, SignalHistory
from datetime import datetime
from decimal import Decimal
import logging

trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/parameters', methods=['GET'])
def get_trading_parameters():
    """獲取交易參數"""
    try:
        params = TradingParameters.query.first()
        if not params:
            # 如果沒有參數記錄，創建默認參數
            params = TradingParameters()
            db.session.add(params)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': params.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bp.route('/parameters', methods=['PUT'])
def update_trading_parameters():
    """更新交易參數"""
    try:
        data = request.get_json()
        
        # 參數驗證
        validation_errors = []
        
        if 'take_profit_pct' in data:
            if data['take_profit_pct'] <= 0 or data['take_profit_pct'] > 100:
                validation_errors.append('停利百分比必須在0-100之間')
        
        if 'stop_loss_pct' in data:
            if data['stop_loss_pct'] >= 0 or data['stop_loss_pct'] < -50:
                validation_errors.append('停損百分比必須在-50-0之間')
        
        if 'min_volume_shares' in data:
            if data['min_volume_shares'] <= 0:
                validation_errors.append('最低成交張數必須大於0')
        
        if 'min_volume_ratio' in data:
            if data['min_volume_ratio'] <= 0:
                validation_errors.append('最低量比必須大於0')
        
        if 'per_order_value' in data:
            if data['per_order_value'] <= 0:
                validation_errors.append('單筆下單金額必須大於0')
        
        if validation_errors:
            return jsonify({
                'success': False,
                'errors': validation_errors
            }), 400
        
        # 獲取或創建參數記錄
        params = TradingParameters.query.first()
        if not params:
            params = TradingParameters()
            db.session.add(params)
        
        # 更新參數
        for key, value in data.items():
            if hasattr(params, key):
                if key in ['min_volume_ratio', 'min_money_flow', 'take_profit_pct', 
                          'stop_loss_pct', 'per_order_value', 'max_total_position']:
                    setattr(params, key, Decimal(str(value)))
                else:
                    setattr(params, key, value)
        
        params.last_updated = datetime.utcnow()
        db.session.commit()
        
        # 記錄系統日誌
        log = SystemLog(
            level='INFO',
            message=f'交易參數已更新: {data}',
            module='trading_parameters'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': params.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bp.route('/positions', methods=['GET'])
def get_positions():
    """獲取當前持倉"""
    try:
        positions = Position.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'data': [pos.to_dict() for pos in positions]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bp.route('/trades', methods=['GET'])
def get_trade_history():
    """獲取交易歷史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        trades = TradeRecord.query.order_by(TradeRecord.trade_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [trade.to_dict() for trade in trades.items],
            'pagination': {
                'page': page,
                'pages': trades.pages,
                'per_page': per_page,
                'total': trades.total
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bp.route('/signals', methods=['GET'])
def get_signal_history():
    """獲取信號歷史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        signals = SignalHistory.query.order_by(SignalHistory.signal_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [signal.to_dict() for signal in signals.items],
            'pagination': {
                'page': page,
                'pages': signals.pages,
                'per_page': per_page,
                'total': signals.total
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bp.route('/logs', methods=['GET'])
def get_system_logs():
    """獲取系統日誌"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        level = request.args.get('level', None)
        
        query = SystemLog.query
        if level:
            query = query.filter_by(level=level.upper())
        
        logs = query.order_by(SystemLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': [log.to_dict() for log in logs.items],
            'pagination': {
                'page': page,
                'pages': logs.pages,
                'per_page': per_page,
                'total': logs.total
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bp.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    """獲取儀表板數據"""
    try:
        # 獲取基本統計數據
        total_positions = Position.query.filter_by(is_active=True).count()
        today = datetime.now().date()
        today_trades = TradeRecord.query.filter(
            TradeRecord.trade_date >= datetime.combine(today, datetime.min.time())
        ).count()
        
        # 計算總持倉市值
        positions = Position.query.filter_by(is_active=True).all()
        total_market_value = sum(float(pos.market_value or 0) for pos in positions)
        total_unrealized_pnl = sum(float(pos.unrealized_pnl or 0) for pos in positions)
        
        # 獲取最近的系統日誌
        recent_logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'data': {
                'total_positions': total_positions,
                'today_trades': today_trades,
                'total_market_value': total_market_value,
                'total_unrealized_pnl': total_unrealized_pnl,
                'recent_logs': [log.to_dict() for log in recent_logs]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trading_bp.route('/emergency-stop', methods=['POST'])
def emergency_stop():
    """緊急停止交易"""
    try:
        # 停用交易參數
        params = TradingParameters.query.first()
        if params:
            params.is_active = False
            db.session.commit()
        
        # 記錄緊急停止日誌
        log = SystemLog(
            level='WARNING',
            message='用戶觸發緊急停止，所有交易活動已暫停',
            module='emergency_control'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '緊急停止已執行，所有交易活動已暫停'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

