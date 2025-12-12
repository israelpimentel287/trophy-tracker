class SyncManager {
    constructor() {
        this.currentTaskId = null;
        this.pollInterval = null;
        this.startTime = null;
        this.lastProcessedCount = 0;
        this.progressModal = null;
        
        this.initializeElements();
        this.bindEvents();
        this.checkActiveSyncs();
    }

    initializeElements() {
        this.progressModal = new bootstrap.Modal(document.getElementById('syncProgressModal'));
        this.elements = {
            syncStatus: document.getElementById('syncStatus'),
            syncPercentage: document.getElementById('syncPercentage'),
            syncProgressBar: document.getElementById('syncProgressBar'),
            syncCurrent: document.getElementById('syncCurrent'),
            syncTotal: document.getElementById('syncTotal'),
            gamesSynced: document.getElementById('gamesSynced'),
            gamesSkipped: document.getElementById('gamesSkipped'),
            gamesFailed: document.getElementById('gamesFailed'),
            currentGameCard: document.getElementById('currentGameCard'),
            currentGameName: document.getElementById('currentGameName'),
            syncDuration: document.getElementById('syncDuration'),
            syncETA: document.getElementById('syncETA'),
            syncRate: document.getElementById('syncRate'),
            syncTypeIcon: document.getElementById('syncTypeIcon'),
            syncTypeText: document.getElementById('syncTypeText'),
            cancelSyncBtn: document.getElementById('cancelSyncBtn'),
            completeSyncBtn: document.getElementById('completeSyncBtn'),
            syncCloseBtn: document.getElementById('syncCloseBtn'),
            activeSyncBar: document.getElementById('activeSyncBar'),
            activeSyncStatus: document.getElementById('activeSyncStatus'),
            showSyncProgress: document.getElementById('showSyncProgress'),
            platinumCount: document.getElementById('platinumCount'),
            goldCount: document.getElementById('goldCount'),
            silverCount: document.getElementById('silverCount'),
            bronzeCount: document.getElementById('bronzeCount'),
            totalTrophies: document.getElementById('totalTrophies'),
            trophyLevel: document.getElementById('trophyLevel'),
            completionRate: document.getElementById('completionRate'),
            achievementsContainer: document.getElementById('achievementsContainer')
        };
    }

    bindEvents() {
        document.querySelectorAll('.sync-trigger').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const syncType = btn.dataset.syncType;
                const url = btn.dataset.url;
                this.startSync(syncType, url);
            });
        });

        this.elements.cancelSyncBtn?.addEventListener('click', () => {
            this.cancelCurrentSync();
        });

        if (this.elements.showSyncProgress) {
            this.elements.showSyncProgress.addEventListener('click', () => {
                this.progressModal.show();
            });
        }

        document.getElementById('syncProgressModal')?.addEventListener('hidden.bs.modal', () => {
            if (this.currentTaskId && this.elements.activeSyncBar?.style.display === 'none') {
                this.elements.activeSyncBar.style.display = 'block';
            }
        });
    }

    async startSync(syncType, url) {
        try {
            this.toggleSyncButtons(false);
            
            this.setupSyncModal(syncType);
            this.progressModal.show();
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.redirected) {
                const redirectUrl = new URL(response.url);
                const pathParts = redirectUrl.pathname.split('/');
                this.currentTaskId = pathParts[pathParts.length - 1];
            } else if (response.ok) {
                const data = await response.json();
                this.currentTaskId = data.task_id;
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            this.startPolling();
            
        } catch (error) {
            console.error('Error starting sync:', error);
            this.showError('Failed to start sync. Please try again.');
            this.toggleSyncButtons(true);
            this.progressModal.hide();
        }
    }

    async checkActiveSyncs() {
        try {
            const response = await fetch('/api/active-tasks');
            if (response.ok) {
                const data = await response.json();
                const tasks = Array.isArray(data.tasks) ? data.tasks : [];
                
                if (tasks.length > 0) {
                    const task = tasks[0];
                    this.currentTaskId = task.task_id;
                    this.showActiveSyncBar(`Active sync in progress (${task.name || 'Unknown'})`);
                    this.startPolling();
                }
            }
        } catch (error) {
            console.error('Error checking active syncs:', error);
        }
    }

    setupSyncModal(syncType) {
        if (syncType === 'quick') {
            this.elements.syncTypeIcon.innerHTML = '<i class="fas fa-bolt"></i>';
            this.elements.syncTypeText.textContent = 'Quick Steam Sync';
        } else {
            this.elements.syncTypeIcon.innerHTML = '<i class="fas fa-sync"></i>';
            this.elements.syncTypeText.textContent = 'Full Steam Sync';
        }

        this.resetModalState();
        
        this.elements.cancelSyncBtn.style.display = 'block';
        this.elements.completeSyncBtn.style.display = 'none';
        this.elements.syncCloseBtn.style.display = 'none';
        
        this.startTime = Date.now();
    }

    resetModalState() {
        this.elements.syncStatus.textContent = 'Initializing sync...';
        this.elements.syncPercentage.textContent = '0%';
        this.elements.syncProgressBar.style.width = '0%';
        this.elements.syncProgressBar.setAttribute('aria-valuenow', '0');
        this.elements.syncCurrent.textContent = '0';
        this.elements.syncTotal.textContent = '0';
        this.elements.gamesSynced.textContent = '0';
        this.elements.gamesSkipped.textContent = '0';
        this.elements.gamesFailed.textContent = '0';
        this.elements.syncDuration.textContent = '0s';
        this.elements.syncETA.textContent = 'Calculating...';
        this.elements.syncRate.textContent = '- games/min';
        
        this.elements.currentGameCard.style.display = 'none';
        
        document.querySelectorAll('.phase-step').forEach(step => {
            step.classList.remove('active', 'completed');
        });
        document.querySelector('[data-phase="initialization"]')?.classList.add('active');
    }

    startPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        this.pollInterval = setInterval(() => {
            this.updateSyncStatus();
        }, 1000);
        
        this.updateSyncStatus();
    }

    async updateSyncStatus() {
        if (!this.currentTaskId) return;

        try {
            const response = await fetch(`/api/task-status/${this.currentTaskId}`);
            if (response.ok) {
                const status = await response.json();
                this.processSyncStatus(status);
            }
        } catch (error) {
            console.error('Error fetching sync status:', error);
        }
    }

    processSyncStatus(status) {
        const { state, percentage = 0, current = 0, total = 1 } = status;

        this.elements.syncProgressBar.style.width = `${percentage}%`;
        this.elements.syncProgressBar.setAttribute('aria-valuenow', percentage);
        this.elements.syncPercentage.textContent = `${Math.round(percentage)}%`;
        
        this.elements.syncCurrent.textContent = current;
        this.elements.syncTotal.textContent = total;
        
        if (status.games_synced !== undefined) {
            this.elements.gamesSynced.textContent = status.games_synced;
        }
        if (status.games_skipped !== undefined) {
            this.elements.gamesSkipped.textContent = status.games_skipped;
        }
        if (status.failed_games !== undefined) {
            this.elements.gamesFailed.textContent = Array.isArray(status.failed_games) ? status.failed_games.length : status.failed_games;
        }

        if (status.status) {
            this.elements.syncStatus.textContent = status.status;
        }

        if (status.current_game) {
            this.elements.currentGameName.textContent = status.current_game;
            this.elements.currentGameCard.style.display = 'block';
        }

        if (status.phase) {
            this.updatePhaseIndicators(status.phase);
        }
        
        this.updateTimingInfo(current, total);
        
        if (state !== 'SUCCESS' && state !== 'FAILURE') {
            this.showActiveSyncBar(status.status || 'Sync in progress...');
        }

        if (state === 'SUCCESS') {
            this.handleSyncSuccess(status);
        } else if (state === 'FAILURE') {
            this.handleSyncFailure(status);
        }
    }

    updatePhaseIndicators(currentPhase) {
        const phases = ['initialization', 'syncing', 'finalizing', 'completed'];
        const currentIndex = phases.indexOf(currentPhase);
        
        document.querySelectorAll('.phase-step').forEach((step, index) => {
            step.classList.remove('active', 'completed');
            
            if (index < currentIndex) {
                step.classList.add('completed');
            } else if (index === currentIndex) {
                step.classList.add('active');
            }
        });
    }

    updateTimingInfo(current, total) {
        if (this.startTime) {
            const elapsed = Date.now() - this.startTime;
            const elapsedSeconds = Math.floor(elapsed / 1000);
            
            this.elements.syncDuration.textContent = this.formatDuration(elapsedSeconds);
            
            if (current > 0 && current > this.lastProcessedCount) {
                const rate = (current / elapsedSeconds) * 60;
                this.elements.syncRate.textContent = `${rate.toFixed(1)} games/min`;
                
                if (current < total) {
                    const remainingItems = total - current;
                    const remainingSeconds = remainingItems / (current / elapsedSeconds);
                    this.elements.syncETA.textContent = this.formatDuration(Math.ceil(remainingSeconds));
                }
            }
            
            this.lastProcessedCount = current;
        }
    }

    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }

    async handleSyncSuccess(status) {
        this.stopPolling();
        
        this.elements.syncStatus.textContent = status.result?.message || 'Sync completed';
        this.elements.syncProgressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
        this.elements.syncProgressBar.classList.add('bg-success');
        
        document.querySelectorAll('.phase-step').forEach(step => {
            step.classList.remove('active');
            step.classList.add('completed');
        });
        
        this.elements.currentGameCard.style.display = 'none';
        this.elements.cancelSyncBtn.style.display = 'none';
        this.elements.completeSyncBtn.style.display = 'block';
        this.elements.syncCloseBtn.style.display = 'block';
        this.elements.activeSyncBar.style.display = 'none';
        
        this.toggleSyncButtons(true);
        
        await this.refreshTrophyData();
        
        setTimeout(() => {
            if (document.getElementById('syncProgressModal')?.classList.contains('show')) {
                this.progressModal.hide();
            }
        }, 3000);
        
        this.currentTaskId = null;
    }

    handleSyncFailure(status) {
        this.stopPolling();
        
        this.elements.syncStatus.textContent = status.error || 'Sync failed. Please try again.';
        this.elements.syncProgressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
        this.elements.syncProgressBar.classList.add('bg-danger');
        
        this.elements.cancelSyncBtn.style.display = 'none';
        this.elements.completeSyncBtn.style.display = 'block';
        this.elements.syncCloseBtn.style.display = 'block';
        this.elements.activeSyncBar.style.display = 'none';
        
        this.toggleSyncButtons(true);
        
        this.currentTaskId = null;
    }

    async cancelCurrentSync() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/cancel-sync/${this.currentTaskId}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.stopPolling();
                this.elements.syncStatus.textContent = 'Sync cancelled by user';
                this.elements.syncProgressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
                this.elements.syncProgressBar.classList.add('bg-warning');
                
                this.elements.cancelSyncBtn.style.display = 'none';
                this.elements.completeSyncBtn.style.display = 'block';
                this.elements.syncCloseBtn.style.display = 'block';
                this.elements.activeSyncBar.style.display = 'none';
                
                this.toggleSyncButtons(true);
                
                this.currentTaskId = null;
            }
        } catch (error) {
            console.error('Error cancelling sync:', error);
        }
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    showActiveSyncBar(message) {
        if (this.elements.activeSyncStatus && this.elements.activeSyncBar) {
            this.elements.activeSyncStatus.textContent = message;
            this.elements.activeSyncBar.style.display = 'block';
        }
    }

    toggleSyncButtons(enabled) {
        document.querySelectorAll('.sync-trigger').forEach(btn => {
            btn.disabled = !enabled;
            if (enabled) {
                btn.classList.remove('disabled');
            } else {
                btn.classList.add('disabled');
            }
        });
        
        const dropdown = document.getElementById('syncDropdown');
        if (dropdown) {
            dropdown.disabled = !enabled;
        }
    }

    async refreshTrophyData() {
        try {
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } catch (error) {
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        }
    }

    showError(message) {
        const alertHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error:</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        const content = document.querySelector('.container-fluid') || document.body;
        content.insertAdjacentHTML('afterbegin', alertHtml);
    }

    destroy() {
        this.stopPolling();
        if (this.progressModal) {
            this.progressModal.dispose();
        }
    }
}

class HTTPPollingUpdates {
    constructor() {
        this.pollInterval = null;
        this.isPolling = false;
        
        if (document.body.dataset.userId) {
            this.startPolling();
        }
    }

    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollInterval = setInterval(() => {
            this.checkForUpdates();
        }, 10000);
    }

    async checkForUpdates() {
        try {
            const response = await fetch('/ws/sync-updates');
            if (response.ok) {
                const data = await response.json();
                this.handleUpdate(data);
            }
        } catch (error) {
        }
    }

    handleUpdate(data) {
        if (data.type === 'sync_update' && Array.isArray(data.active_tasks) && data.active_tasks.length > 0) {
            if (window.syncManager && !window.syncManager.currentTaskId) {
                const task = data.active_tasks[0];
                window.syncManager.currentTaskId = task.task_id;
                window.syncManager.showActiveSyncBar(`Active sync in progress (${task.name || 'Unknown'})`);
                window.syncManager.startPolling();
            }
        }
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isPolling = false;
    }

    destroy() {
        this.stopPolling();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.syncManager = new SyncManager();
    window.httpPollingUpdates = new HTTPPollingUpdates();
});

window.addEventListener('beforeunload', function() {
    if (window.syncManager) {
        window.syncManager.destroy();
    }
    if (window.httpPollingUpdates) {
        window.httpPollingUpdates.destroy();
    }
});