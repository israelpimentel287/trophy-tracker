let themeManager;

function initializeManagers() {
    if (typeof ThemeManager !== 'undefined') {
        themeManager = new ThemeManager();
        window.themeManager = themeManager;
    } else {
        console.error('ThemeManager not loaded');
    }
}

function setupGlobalEventListeners() {
    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'T') {
            event.preventDefault();
            if (themeManager) {
                themeManager.toggleTheme();
            }
        }
    });
}

function setupDevelopmentHelpers() {
    const isDevelopment = window.location.hostname === 'localhost' || 
                         window.location.hostname === '127.0.0.1';
    
    if (!isDevelopment) return;
    
    window.debug = {
        themeManager,
        
        getStatus: () => {
            return {
                theme: themeManager?.getTheme()
            };
        }
    };
}

function checkDependencies() {
    const required = [
        { name: 'Bootstrap', check: () => typeof bootstrap !== 'undefined' },
    ];
    
    const missing = required.filter(dep => !dep.check());
    
    if (missing.length > 0) {
        console.error('Missing required dependencies:', missing.map(d => d.name).join(', '));
        return false;
    }
    
    return true;
}

function initialize() {
    if (!checkDependencies()) {
        console.error('Cannot initialize - missing dependencies');
        return;
    }
    
    initializeManagers();
    setupGlobalEventListeners();
    setupDevelopmentHelpers();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        themeManager
    };
}