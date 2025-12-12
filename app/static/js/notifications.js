class NotificationPoller {
    constructor() {
        this.pollInterval = 5000;
        this.intervalId = null;
        this.activeNotifications = new Set();
        this.container = null;
    }

    init() {
        console.log('Notification poller initialized');
        this.createContainer();
        this.startPolling();
        this.checkForNotifications();
    }

    createContainer() {
        if (document.getElementById('notification-container')) {
            this.container = document.getElementById('notification-container');
            return;
        }

        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        `;
        document.body.appendChild(this.container);
    }

    startPolling() {
        if (this.intervalId) return;
        
        console.log(`Polling every ${this.pollInterval}ms`);
        this.intervalId = setInterval(() => this.checkForNotifications(), this.pollInterval);
    }

    stopPolling() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log('Polling stopped');
        }
    }

    async checkForNotifications() {
        try {
            const response = await fetch('/api/notifications/unread');
            
            if (!response.ok) {
                if (response.status === 401) {
                    this.stopPolling();
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success && data.notifications) {
                const newNotifications = data.notifications.filter(
                    n => !this.activeNotifications.has(n.id)
                );

                newNotifications.forEach(n => this.showNotification(n));
            }
        } catch (error) {
            console.error('Error checking notifications:', error);
        }
    }

    showNotification(notification) {
        this.activeNotifications.add(notification.id);

        if (notification.type === 'platinum_trophy') {
            const audio = new Audio('/static/sounds/platinum.mp3');
            audio.volume = 0.7;
            audio.play().catch(e => console.log('Sound blocked by browser:', e));
        }

        const element = this.createNotificationElement(notification);
        this.container.appendChild(element);

        this.markAsRead(notification.id);

        const duration = notification.display_duration || 5000;
        setTimeout(() => {
            this.dismissNotification(notification.id, element);
        }, duration);
    }

    createNotificationElement(notification) {
        const div = document.createElement('div');
        div.className = 'notification-popup';
        div.dataset.notificationId = notification.id;
        div.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease-out;
            cursor: pointer;
            min-width: 300px;
            display: flex;
            align-items: center;
            gap: 16px;
        `;

        const typeColors = {
            'platinum_trophy': 'linear-gradient(135deg, #4a0033 0%, #800020 100%)',
            'sync_complete': 'linear-gradient(135deg, #56ab2f 0%, #a8e063 100%)',
            'sync_error': 'linear-gradient(135deg, #eb3349 0%, #f45c43 100%)',
            'trophy_unlock': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
        };

        if (typeColors[notification.type]) {
            div.style.background = typeColors[notification.type];
        }

        // Get icon from notification data or use default
        const iconHtml = notification.data?.icon_html || '<span style="font-size: 32px;">🔔</span>';
        
        const iconContainer = document.createElement('div');
        iconContainer.innerHTML = iconHtml;
        iconContainer.style.cssText = 'display: flex; align-items: center; justify-content: center;';

        const textContainer = document.createElement('div');
        textContainer.style.cssText = 'flex: 1;';

        const title = document.createElement('div');
        title.style.cssText = 'font-weight: bold; font-size: 16px; margin-bottom: 4px;';
        title.textContent = notification.title;

        const message = document.createElement('div');
        message.style.cssText = 'font-size: 14px; opacity: 0.9;';
        message.textContent = notification.message;

        textContainer.appendChild(title);
        textContainer.appendChild(message);

        div.appendChild(iconContainer);
        div.appendChild(textContainer);

        div.addEventListener('click', () => {
            this.dismissNotification(notification.id, div);
        });

        return div;
    }

    async markAsRead(notificationId) {
        try {
            await fetch(`/api/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    async dismissNotification(notificationId, element) {
        element.style.animation = 'slideOut 0.3s ease-in';
        
        setTimeout(async () => {
            element.remove();
            this.activeNotifications.delete(notificationId);

            try {
                await fetch(`/api/notifications/${notificationId}/dismiss`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            } catch (error) {
                console.error('Error dismissing notification:', error);
            }
        }, 300);
    }
}

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

const notificationPoller = new NotificationPoller();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => notificationPoller.init());
} else {
    notificationPoller.init();
}