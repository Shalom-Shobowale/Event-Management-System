// EventFlow - Core Application JavaScript


// ========================================
// Dark Mode
// ========================================

function initializeDarkMode() {
    try {
        const saved = localStorage.getItem('darkMode');

        const prefersDark = window.matchMedia(
            '(prefers-color-scheme: dark)'
        ).matches;

        if (saved === 'true' || (saved === null && prefersDark)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }

    } catch (error) {
        console.error('Dark mode initialization failed:', error);
    }
}


function toggleDarkMode() {
    const html = document.documentElement;

    const isDark = html.classList.toggle('dark');

    try {
        localStorage.setItem(
            'darkMode',
            isDark ? 'true' : 'false'
        );
    } catch (error) {
        console.error('Could not save dark mode preference:', error);
    }
}


// ========================================
// Sidebar
// ========================================

function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (!sidebar || !overlay) {
        console.error('Sidebar elements not found');
        return;
    }

    sidebar.classList.remove('-translate-x-full');
    overlay.classList.remove('hidden');
}


function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (!sidebar || !overlay) {
        console.error('Sidebar elements not found');
        return;
    }

    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
}


function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');

    if (!sidebar) {
        console.error('Sidebar element not found');
        return;
    }

    if (sidebar.classList.contains('-translate-x-full')) {
        openSidebar();
    } else {
        closeSidebar();
    }
}


// ========================================
// Toast Notifications
// ========================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');

    if (!container) {
        return;
    }

    const icons = {
        success:
            '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#c6f24e" stroke-width="2">' +
            '<circle cx="12" cy="12" r="9"/>' +
            '<path d="M8 12l3 3 5-6"/>' +
            '</svg>',

        error:
            '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#ff4800" stroke-width="2">' +
            '<circle cx="12" cy="12" r="9"/>' +
            '<path d="M12 8v4M12 16h.01"/>' +
            '</svg>',

        warning:
            '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#ff7a3d" stroke-width="2">' +
            '<circle cx="12" cy="12" r="9"/>' +
            '<path d="M12 8v4M12 16h.01"/>' +
            '</svg>',

        info:
            '<svg class="w-4 h-4 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="#9b84ff" stroke-width="2">' +
            '<circle cx="12" cy="12" r="9"/>' +
            '<path d="M12 16v-4M12 8h.01"/>' +
            '</svg>'
    };

    const toast = document.createElement('div');

    toast.className = 'ef-toast';
    toast.dataset.type = type || 'info';

    toast.innerHTML =
        (icons[type] || icons.info) +
        '<span>' +
        message +
        '</span>';

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.transition =
            'opacity .3s, transform .3s';

        toast.style.opacity = '0';
        toast.style.transform =
            'translateX(12px)';

        setTimeout(() => {
            toast.remove();
        }, 300);

    }, 4200);
}


// ========================================
// Page Initialization
// ========================================

function initializeApp() {

    // ------------------------------------
    // Dark mode
    // ------------------------------------

    initializeDarkMode();

    const darkModeButton =
        document.getElementById('dark-mode-toggle');

    if (darkModeButton) {
        darkModeButton.addEventListener(
            'click',
            toggleDarkMode
        );
    }


    // ------------------------------------
    // Sidebar
    // ------------------------------------

    const sidebarButton =
        document.getElementById('sidebar-toggle');

    if (sidebarButton) {
        sidebarButton.addEventListener(
            'click',
            toggleSidebar
        );
    }


    // ------------------------------------
    // Sidebar overlay
    // ------------------------------------

    const sidebarOverlay =
        document.getElementById('sidebar-overlay');

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener(
            'click',
            closeSidebar
        );
    }


    // ------------------------------------
    // Django messages
    // ------------------------------------

    const djangoMessages =
        document.querySelectorAll(
            '#django-messages .django-message'
        );

    djangoMessages.forEach(messageElement => {

        const message =
            messageElement.dataset.message;

        const type =
            messageElement.dataset.type || 'info';

        showToast(message, type);
    });
}


// ========================================
// Start Application
// ========================================

if (document.readyState === 'loading') {

    document.addEventListener(
        'DOMContentLoaded',
        initializeApp
    );

} else {

    initializeApp();

}