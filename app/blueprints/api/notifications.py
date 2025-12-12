"""Notification API endpoints for HTTP polling."""
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Notification
from datetime import datetime

notifications_api_bp = Blueprint('notifications_api', __name__, url_prefix='/api/notifications')


@notifications_api_bp.route('/unread', methods=['GET'])
@login_required
def get_unread_notifications():
    """Get all unread/undismissed notifications for the current user.
    
    Returns notifications that haven't been dismissed yet,
    ordered by creation time (newest first).
    
    Used by frontend polling to check for new notifications.
    """
    try:
        # Query for non-dismissed notifications for this user
        notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).filter(
            Notification.dismissed_at.is_(None)
        ).order_by(
            Notification.created_at.desc()
        ).all()
        
        # Convert to JSON-friendly format
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'type': notification.type,
                'title': notification.title,
                'message': notification.message,
                'data': notification.data,
                'priority': notification.priority,
                'display_duration': notification.display_duration,
                'created_at': notification.created_at.isoformat() if notification.created_at else None,
                'is_read': notification.is_read
            })
        
        return jsonify({
            'success': True,
            'notifications': notifications_data,
            'count': len(notifications_data)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@notifications_api_bp.route('/<notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read.
    
    Sets the read_at timestamp on the notification.
    """
    try:
        # Get notification and verify it belongs to current user
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False,
                'error': 'Notification not found'
            }), 404
        
        # Mark as read using the model's method
        notification.mark_read()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'notification_id': notification_id,
            'read_at': notification.read_at.isoformat() if notification.read_at else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@notifications_api_bp.route('/<notification_id>/dismiss', methods=['POST'])
@login_required
def dismiss_notification(notification_id):
    """Mark a notification as dismissed.
    
    Sets the dismissed_at timestamp on the notification.
    Dismissed notifications won't be returned by the /unread endpoint.
    """
    try:
        # Get notification and verify it belongs to current user
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False,
                'error': 'Notification not found'
            }), 404
        
        # Mark as dismissed using the model's method
        notification.mark_dismissed()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'notification_id': notification_id,
            'dismissed_at': notification.dismissed_at.isoformat() if notification.dismissed_at else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@notifications_api_bp.route('/count', methods=['GET'])
@login_required
def get_notification_count():
    """Get count of unread/undismissed notifications.
    
    Lightweight endpoint for showing notification badge counts.
    """
    try:
        count = Notification.query.filter_by(
            user_id=current_user.id
        ).filter(
            Notification.dismissed_at.is_(None)
        ).count()
        
        return jsonify({
            'success': True,
            'count': count
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500