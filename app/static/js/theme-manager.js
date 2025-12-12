class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || 'dark';
        this.themes = ['light', 'dark', 'auto'];
        this.themeIcons = {
            'light': 'fas fa-sun',
            'dark': 'fas fa-moon',
            'auto': 'fas fa-adjust'
        };
        this.themeNames = {
            'light': 'Light Theme',
            'dark': 'Dark Theme', 
            'auto': 'Auto Theme (System)'
        };
        this.mediaQuery = null;
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.updateThemeIcon();
        this.addMediaQueryListener();
        this.setupKeyboardShortcuts();
    }

    getStoredTheme() {
        try {
            return localStorage.getItem('theme');
        } catch (error) {
            console.warn('LocalStorage not available:', error);
            return null;
        }
    }

    setStoredTheme(theme) {
        try {
            localStorage.setItem('theme', theme);
        } catch (error) {
            console.warn('Could not save theme to localStorage:', error);
        }
    }

    applyTheme(theme) {
        if (!this.themes.includes(theme)) {
            console.warn('Invalid theme:', theme);
            return;
        }

        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        this.setStoredTheme(theme);
        this.updateThemeIcon();
        
        document.body.classList.add('theme-transition');
        setTimeout(() => {
            document.body.classList.remove('theme-transition');
        }, 500);

        this.dispatchThemeChangeEvent(theme);
    }

    updateThemeIcon() {
        const icon = document.getElementById('theme-icon');
        if (icon) {
            icon.className = `theme-icon ${this.themeIcons[this.currentTheme]}`;
        }
    }

    toggleTheme() {
        const currentIndex = this.themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % this.themes.length;
        const nextTheme = this.themes[nextIndex];
        
        this.applyTheme(nextTheme);
        
        if (window.taskManager) {
            window.taskManager.showToast(
                'info', 
                'Theme Changed', 
                `Switched to ${this.themeNames[nextTheme]}`
            );
        }
    }

    getTheme() {
        return this.currentTheme;
    }

    getEffectiveTheme() {
        if (this.currentTheme === 'auto') {
            return this.getSystemTheme();
        }
        return this.currentTheme;
    }

    getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    addMediaQueryListener() {
        if (!window.matchMedia) {
            return;
        }

        this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        
        if (this.mediaQuery.addEventListener) {
            this.mediaQuery.addEventListener('change', (e) => {
                this.handleSystemThemeChange(e);
            });
        } else if (this.mediaQuery.addListener) {
            this.mediaQuery.addListener((e) => {
                this.handleSystemThemeChange(e);
            });
        }
    }

    handleSystemThemeChange(event) {
        if (this.currentTheme === 'auto') {
            const effectiveTheme = event.matches ? 'dark' : 'light';
            
            document.body.classList.add('theme-transition');
            this.dispatchThemeChangeEvent('auto');
            
            setTimeout(() => {
                document.body.classList.remove('theme-transition');
            }, 500);
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'T') {
                event.preventDefault();
                this.toggleTheme();
            }
        });
    }

    dispatchThemeChangeEvent(theme) {
        const event = new CustomEvent('themeChanged', {
            detail: {
                theme: theme,
                effectiveTheme: this.getEffectiveTheme()
            }
        });
        document.dispatchEvent(event);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
}