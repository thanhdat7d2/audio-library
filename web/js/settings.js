// Settings view (Library Path, Theme, Sidebar collapse state) persisted to app_settings.json

let currentTheme = 'emerald-dark';
let sidebarCollapsed = false;

function applyTheme(themeId) {
    const valid = themeId || 'emerald-dark';
    currentTheme = valid;
    document.documentElement.setAttribute('data-theme', valid);

    document.querySelectorAll('#settings-theme-grid .theme-card').forEach(card => {
        card.classList.toggle('active', card.getAttribute('data-theme-id') === valid);
    });

    requestAnimationFrame(() => {
        if (typeof drawWaveform === 'function') drawWaveform(waveformProgress);
    });
}

function applySidebarState(collapsed) {
    sidebarCollapsed = Boolean(collapsed);
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar) {
        sidebar.classList.toggle('collapsed', sidebarCollapsed);
    }
}

async function loadAppSettings() {
    const settings = await window.pywebview.api.get_settings();
    if (settings) {
        applyTheme(settings.theme || 'emerald-dark');
        applySidebarState(Boolean(settings.sidebar_collapsed));
        const pathInput = document.getElementById('settings-library-path');
        if (pathInput) pathInput.value = settings.library_path || '';
    }
}

function renderSettingsView() {
    const pathInput = document.getElementById('settings-library-path');
    if (pathInput) pathInput.value = libraryPath || '';
    const statusEl = document.getElementById('settings-library-status');
    if (statusEl) statusEl.innerText = '';
    applyTheme(currentTheme);
}

function setupSettingsListeners() {
    const toggleBtn = document.getElementById('btn-toggle-sidebar');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', async () => {
            applySidebarState(!sidebarCollapsed);
            await window.pywebview.api.update_settings({ sidebar_collapsed: sidebarCollapsed });
        });
    }

    document.querySelectorAll('#settings-theme-grid .theme-card').forEach(card => {
        card.addEventListener('click', async () => {
            const themeId = card.getAttribute('data-theme-id');
            applyTheme(themeId);
            await window.pywebview.api.update_settings({ theme: themeId });
        });
    });

    document.getElementById('btn-settings-browse-library').addEventListener('click', async () => {
        const res = await window.pywebview.api.select_library_folder();
        if (res.status === 'success') {
            document.getElementById('settings-library-path').value = res.library_path;
            document.getElementById('settings-library-status').innerText = 'Library path updated and saved to app_settings.json.';
            await checkLibraryStatus();
            switchView('settings');
        } else if (res.status === 'error') {
            alert('Error setting library: ' + res.message);
        }
    });

    document.getElementById('btn-settings-apply-library').addEventListener('click', async () => {
        const path = document.getElementById('settings-library-path').value.trim();
        if (!path) {
            alert('Please enter or browse a library directory path.');
            return;
        }
        const res = await window.pywebview.api.update_settings({ library_path: path });
        if (res.status === 'success') {
            document.getElementById('settings-library-status').innerText = 'Library path saved to app_settings.json.';
            await checkLibraryStatus();
            switchView('settings');
        } else {
            alert('Error updating library path: ' + res.message);
        }
    });
}
