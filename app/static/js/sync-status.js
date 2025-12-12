class SyncStatusPage {
    constructor(taskId) {
        this.taskId = taskId;
        this.startTime = Date.now();
        this.pollInterval = 1000;
        this.maxRetries = 5;
        this.retryCount = 0;
        this.isComplete = false;
        
        this.init();
    }

    init() {
        this.pollTaskStatus();
        
        this.pollTimer = setInterval(() => {
            if (!this.isComplete) {
                this.pollTaskStatus();
            }
        }, this.pollInterval);

        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.cancelTask();
        });

        this.durationTimer = setInterval(() => {
            this.updateDuration();
        }, 1000);

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pausePolling();
            } else {
                this.resumePolling();
            }
        });
    }

    async pollTaskStatus() {
        try {
            const response = await fetch(`/api/task-status/${this.taskId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const status = await response.json();
            this.retryCount = 0;
            this.updateUI(status);

            if (status.ready) {
                this.handleTaskCompletion(status);
            }

        } catch (error) {
            console.error('Error polling task status:', error);
            this.handlePollError(error);
        }
    }

    updateUI(status) {
        this.updateSyncType(status.sync_type);
        this.updateStateBadge(status.state);
        this.updateProgress(status);
        this.updateCurrentStatus(status);
        this.updateStatistics(status);
        this.updateCancelButton(status);
    }

    updateSyncType(syncType) {
        const typeMap = {
            'full': { title: 'Full Steam Sync', icon: 'fas fa-sync' },
            'quick': { title: 'Quick Steam Sync', icon: 'fas fa-bolt' },
            'specific': { title: 'Game Sync', icon: 'fas fa-gamepad' },
            'achievement_refresh': { title: 'Achievement Refresh', icon: 'fas fa-trophy' },
            'user_stats': { title: 'Statistics Update', icon: 'fas fa-chart-bar' },
            'batch': { title: 'Batch Sync', icon: 'fas fa-layer-group' }
        };

        const type = typeMap[syncType] || { title: 'Steam Sync', icon: 'fas fa-sync-alt' };
        
        document.getElementById('sync-title').textContent = type.title;
        document.getElementById('sync-type-icon').innerHTML = `<i class="${type.icon}"></i>`;
    }

    updateStateBadge(state) {
        const badge = document.getElementById('task-state-badge');
        const stateMap = {
            'PENDING': { text: 'Pending', class: 'bg-secondary' },
            'STARTED': { text: 'Started', class: 'bg-info' },
            'PROGRESS': { text: 'In Progress', class: 'bg-primary' },
            'SUCCESS': { text: 'Completed', class: 'bg-success' },
            'FAILURE': { text: 'Failed', class: 'bg-danger' },
            'RETRY': { text: 'Retrying', class: 'bg-warning' },
            'REVOKED': { text: 'Cancelled', class: 'bg-dark' }
        };

        const stateInfo = stateMap[state] || { text: state, class: 'bg-secondary' };
        badge.textContent = stateInfo.text;
        badge.className = `badge ${stateInfo.class} me-2`;
    }

    updateProgress(status) {
        const percentage = Math.round(status.percentage || 0);
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-percentage');

        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        progressText.textContent = `${percentage}%`;

        progressBar.className = 'progress-bar progress-bar-striped';
        if (status.state === 'SUCCESS') {
            progressBar.classList.add('bg-success');
            progressBar.classList.remove('progress-bar-animated');
        } else if (status.state === 'FAILURE') {
            progressBar.classList.add('bg-danger');
            progressBar.classList.remove('progress-bar-animated');
        } else if (status.state === 'PROGRESS') {
            progressBar.classList.add('progress-bar-animated');
        }
    }

    updateCurrentStatus(status) {
        // Simplified status messages
        let statusText = status.status || 'Processing...';
        
        // Replace verbose messages with minimal ones
        if (statusText.includes('Preparing sync') || statusText.includes('initialization')) {
            statusText = 'Starting...';
        } else if (statusText.includes('Getting game list') || statusText.includes('fetching_games')) {
            statusText = 'Loading games...';
        } else if (statusText.includes('Processing') || statusText.includes('syncing_games')) {
            statusText = 'Syncing...';
        } else if (statusText.includes('Updating') || statusText.includes('calculating_stats')) {
            statusText = 'Finalizing...';
        } else if (statusText.includes('Completing') || statusText.includes('finalizing')) {
            statusText = 'Finishing up...';
        } else if (statusText.includes('completed')) {
            statusText = 'Complete';
        }
        
        document.getElementById('status-text').textContent = statusText;
        
        const currentGameEl = document.getElementById('current-game');
        const gameNameEl = document.getElementById('game-name');
        
        if (status.current_game) {
            gameNameEl.textContent = status.current_game;
            currentGameEl.style.display = 'block';
        } else {
            currentGameEl.style.display = 'none';
        }

        const etaContainer = document.getElementById('eta-container');
        const etaText = document.getElementById('eta-text');
        
        if (status.eta && !status.ready) {
            etaText.textContent = status.eta;
            etaContainer.style.display = 'block';
        } else {
            etaContainer.style.display = 'none';
        }
    }

    updateStatistics(status) {
        document.getElementById('synced-count').textContent = status.games_synced || 0;
        document.getElementById('skipped-count').textContent = status.games_skipped || 0;
        document.getElementById('failed-count').textContent = status.failed_games || 0;
        document.getElementById('total-count').textContent = status.total || 0;
    }

    updateCancelButton(status) {
        const cancelBtn = document.getElementById('cancel-btn');
        const showCancel = status.state === 'PROGRESS' || status.state === 'STARTED';
        cancelBtn.style.display = showCancel ? 'inline-block' : 'none';
    }

    updateDuration() {
        const duration = Date.now() - this.startTime;
        const durationText = this.formatDuration(duration);
        document.getElementById('duration-text').textContent = durationText;
    }

    formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        if (seconds < 60) return `${seconds}s`;
        
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
        
        const hours = Math.floor(minutes / 60);
        return `${hours}h ${minutes % 60}m`;
    }

    handleTaskCompletion(status) {
        this.isComplete = true;
        clearInterval(this.pollTimer);
        
        if (status.successful) {
            this.showCompletionResults(status);
        } else if (status.failed) {
            this.showErrorAlert(status);
        }
    }

    showCompletionResults(status) {
        const resultsCard = document.getElementById('results-card');
        const resultsContent = document.getElementById('results-content');
        
        const duration = this.formatDuration(Date.now() - this.startTime);
        const result = status.result || {};
        
        resultsContent.innerHTML = `
            <div class="alert alert-success mb-3">
                <i class="fas fa-check-circle me-2"></i>
                Sync completed successfully in ${duration}
            </div>
            <div class="d-flex gap-2">
                <a href="${window.trophiesUrl}" class="btn btn-primary">
                    <i class="fas fa-trophy"></i> View Trophies
                </a>
                <a href="/games" class="btn btn-outline-secondary">
                    <i class="fas fa-gamepad"></i> View Games
                </a>
            </div>
        `;
        
        resultsCard.style.display = 'block';
    }

    showErrorAlert(status) {
        const errorAlert = document.getElementById('error-alert');
        const errorMessage = document.getElementById('error-message');
        
        errorMessage.innerHTML = `
            <p><strong>Error:</strong> ${status.error || 'Unknown error occurred'}</p>
            ${status.traceback ? `<pre class="small mt-2">${status.traceback}</pre>` : ''}
        `;
        
        errorAlert.style.display = 'block';
    }

    handlePollError(error) {
        this.retryCount++;
        
        if (this.retryCount >= this.maxRetries) {
            this.showErrorAlert({
                error: 'Lost connection to server. Please refresh the page to check task status.',
                traceback: null
            });
            clearInterval(this.pollTimer);
        } 
    }

    async cancelTask() {
        try {
            const response = await fetch(`/api/cancel-sync/${this.taskId}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                document.getElementById('cancel-btn').disabled = true;
                document.getElementById('cancel-btn').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cancelling...';
            }
        } catch (error) {
            console.error('Error cancelling task:', error);
            alert('Failed to cancel task. Please try again.');
        }
    }

    pausePolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    resumePolling() {
        if (!this.pollTimer && !this.isComplete) {
            this.pollTimer = setInterval(() => {
                this.pollTaskStatus();
            }, this.pollInterval);
        }
    }

    cleanup() {
        if (this.pollTimer) clearInterval(this.pollTimer);
        if (this.durationTimer) clearInterval(this.durationTimer);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const taskId = window.syncTaskId;
    window.syncStatus = new SyncStatusPage(taskId);
});

window.addEventListener('beforeunload', function() {
    if (window.syncStatus) {
        window.syncStatus.cleanup();
    }
});