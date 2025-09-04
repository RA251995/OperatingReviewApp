/**
 * Auto-reload functionality for date/time changes
 * Automatically refreshes data when date or time inputs change
 */

class AutoReloadManager {
    constructor() {
        this.isLoading = false;
        this.debounceTimer = null;
        this.debounceDelay = 500; // milliseconds
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupLoadingIndicator();
    }

    bindEvents() {
        // Bind to date inputs
        const dateInputs = document.querySelectorAll('input[type="date"], input[type="month"]');
        dateInputs.forEach(input => {
            input.addEventListener('change', (e) => this.handleDateChange(e));
        });

        // Bind to time inputs
        const timeInputs = document.querySelectorAll('select[name="time"]');
        timeInputs.forEach(input => {
            input.addEventListener('change', (e) => this.handleTimeChange(e));
        });
    }

    handleDateChange(event) {
        this.debounce(() => {
            this.reloadData();
        });
    }

    handleTimeChange(event) {
        this.debounce(() => {
            this.reloadData();
        });
    }

    debounce(func) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(func, this.debounceDelay);
    }

    reloadData() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading();

        const form = document.querySelector('.review-form');
        if (!form) {
            this.isLoading = false;
            this.hideLoading();
            return;
        }

        const formData = new FormData(form);
        const url = window.location.pathname;

        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            this.updatePageContent(html);
        })
        .catch(error => {
            console.error('Auto-reload failed:', error);
            this.showError();
        })
        .finally(() => {
            this.isLoading = false;
            this.hideLoading();
        });
    }

    updatePageContent(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update table content
        const newTables = doc.querySelectorAll('.tables-flex');
        const currentTables = document.querySelectorAll('.tables-flex');
        
        if (newTables.length > 0 && currentTables.length > 0) {
            currentTables[0].innerHTML = newTables[0].innerHTML;
        }

        // Re-bind events to new elements
        this.bindEvents();
    }

    setupLoadingIndicator() {
        if (!document.querySelector('.loading-indicator')) {
            const indicator = document.createElement('div');
            indicator.className = 'loading-indicator';
            indicator.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <span>Loading...</span>
                </div>
            `;
            indicator.style.display = 'none';
            document.body.appendChild(indicator);
        }
    }

    showLoading() {
        const indicator = document.querySelector('.loading-indicator');
        if (indicator) {
            indicator.style.display = 'flex';
        }
    }

    hideLoading() {
        const indicator = document.querySelector('.loading-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    showError() {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'auto-reload-error';
        errorDiv.textContent = 'Failed to reload data. Please refresh the page.';
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4444;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 1000;
        `;
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
}

// Initialize auto-reload when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/hourly-review') || 
        window.location.pathname.includes('/daily-review') || 
        window.location.pathname.includes('/mor-energy') || 
        window.location.pathname.includes('/mor-eht-tf-interruptions') || 
        window.location.pathname.includes('/mor-ht-interruptions') ||
        window.location.pathname.includes('/abc-details')) {
        window.autoReloadManager = new AutoReloadManager();
    }
});
