// App bootstrap, navigation, data refresh, and form submit wiring

window.addEventListener('DOMContentLoaded', () => {
    window.addEventListener('pywebviewready', () => {
        initApp();
    });
});

async function initApp() {
    setupEventListeners();
    setupSpreadsheetListeners();
    setupSettingsListeners();
    setupPlayerListeners();
    await loadAppSettings();
    await checkLibraryStatus();
}

async function checkLibraryStatus() {
    const res = await window.pywebview.api.get_library_status();
    if (res.status === 'configured') {
        libraryPath = res.library_path;
        document.getElementById('view-setup').classList.add('hidden');
        document.querySelectorAll('.nav-item').forEach(item => {
            item.style.pointerEvents = 'all';
            item.style.opacity = '1';
        });
        await refreshLibraryData();
        switchView('dashboard');
    } else {
        libraryPath = null;
        document.getElementById('view-setup').classList.remove('hidden');
        document.querySelectorAll('.view-panel').forEach(v => v.classList.add('hidden'));
        document.querySelectorAll('.nav-item').forEach(item => {
            const view = item.getAttribute('data-view');
            if (view !== 'settings' && view !== 'dashboard') {
                item.style.pointerEvents = 'none';
                item.style.opacity = '0.5';
            }
        });
    }
}

async function refreshLibraryData() {
    if (!libraryPath) return;

    const options = await window.pywebview.api.get_metadata_options();
    if (options) {
        metadataOptions = options;
        populateDropdowns();
    }

    const stats = await window.pywebview.api.get_stats();
    document.getElementById('stat-songs').innerText = stats.songs || 0;
    document.getElementById('stat-artists').innerText = stats.artists || 0;
    document.getElementById('stat-albums').innerText = stats.albums || 0;
    document.getElementById('stat-genres').innerText = stats.genres || 0;
    document.getElementById('stat-projects').innerText = stats.projects || 0;
    document.getElementById('stat-pending-audio').innerText = stats.songs_without_audio || 0;

    songsList = await window.pywebview.api.get_songs();
    projectsList = await window.pywebview.api.get_projects();

    renderDashboardRecent();
    renderSongsTable(getFilteredSongs());
    renderArtistsView();
    renderAlbumsView();
    renderProjectsTable(getFilteredProjects());
}

function switchView(viewName) {
    if (!libraryPath && viewName !== 'setup' && viewName !== 'settings') return;

    document.querySelectorAll('.sidebar .nav-item').forEach(item => item.classList.remove('active'));
    const activeItem = document.querySelector(`.sidebar .nav-item[data-view="${viewName}"]`);
    if (activeItem) activeItem.classList.add('active');

    document.getElementById('view-setup').classList.add('hidden');
    document.querySelectorAll('.view-panel').forEach(v => v.classList.add('hidden'));
    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) targetPanel.classList.remove('hidden');

    if (viewName === 'dashboard') renderDashboardRecent();
    else if (viewName === 'songs') renderSongsTable(getFilteredSongs());
    else if (viewName === 'artists') renderArtistsView();
    else if (viewName === 'albums') renderAlbumsView();
    else if (viewName === 'projects') renderProjectsTable(getFilteredProjects());
    else if (viewName === 'settings') renderSettingsView();
}

function updateImportSubmitButton() {
    const btn = document.getElementById('btn-submit-import-song');
    if (!btn) return;
    btn.innerHTML = selectedSongImportPath
        ? '<i class="fa-solid fa-file-import"></i> Copy &amp; Register Track'
        : '<i class="fa-solid fa-plus"></i> Register Track (No Audio Yet)';
}

function setupEventListeners() {
    document.querySelectorAll('.sidebar .nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            const view = e.currentTarget.getAttribute('data-view');
            if (view) switchView(view);
        });
    });

    document.getElementById('btn-select-folder').addEventListener('click', async () => {
        const res = await window.pywebview.api.select_library_folder();
        if (res.status === 'success') await checkLibraryStatus();
        else if (res.status === 'error') alert('Error setting library: ' + res.message);
    });

    document.getElementById('import-dropzone').addEventListener('click', async (e) => {
        if (e.target.closest('#btn-clear-import-file')) return;
        const path = await window.pywebview.api.select_file_to_import();
        if (!path) return;
        selectedSongImportPath = path;
        const filename = path.split('\\').pop().split('/').pop();
        document.getElementById('selected-file-name').innerText = filename;
        document.getElementById('selected-file-details').classList.remove('hidden');
        if (!document.getElementById('import-song-title').value.trim()) {
            document.getElementById('import-song-title').value = filename.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');
        }
        updateImportSubmitButton();
    });

    document.getElementById('btn-clear-import-file').addEventListener('click', (e) => {
        e.stopPropagation();
        selectedSongImportPath = null;
        document.getElementById('selected-file-name').innerText = '';
        document.getElementById('selected-file-details').classList.add('hidden');
        updateImportSubmitButton();
    });

    // Multi-badge inputs & AI Generated toggles
    setupTagInput('import-main-artists-input', selectedImportMainArtists, 'badge-main-artists', 'artist');
    setupTagInput('import-feat-artists-input', selectedImportFeatArtists, 'badge-feat-artists', 'artist');
    setupTagInput('import-genres-input', selectedImportGenres, 'badge-genres', 'genre');
    setupTagInput('import-tags-input', selectedImportTags, 'badge-tags', 'tag');
    setupTagInput('edit-main-artists-input', selectedEditMainArtists, 'edit-badge-main-artists', 'artist');
    setupTagInput('edit-feat-artists-input', selectedEditFeatArtists, 'edit-badge-feat-artists', 'artist');
    setupTagInput('edit-genres-input', selectedEditGenres, 'edit-badge-genres', 'genre');
    setupTagInput('edit-tags-input', selectedEditTags, 'edit-badge-tags', 'tag');

    document.getElementById('import-ai-generated').addEventListener('change', (e) => {
        toggleAiTagInList(e.target.checked, selectedImportTags, 'badge-tags');
    });
    document.getElementById('edit-ai-generated').addEventListener('change', (e) => {
        toggleAiTagInList(e.target.checked, selectedEditTags, 'edit-badge-tags');
    });

    // Project path pickers
    bindProjectPathPickers('btn-import-project-folder', 'btn-import-project-file', 'import-project-path');
    bindProjectPathPickers('btn-edit-song-project-folder', 'btn-edit-song-project-file', 'edit-song-project-path');
    bindProjectPathPickers('btn-artist-project-folder', 'btn-artist-project-file', 'artist-project-path');
    bindProjectPathPickers('btn-album-project-folder', 'btn-album-project-file', 'album-project-path');
    bindProjectPathPickers('btn-modal-project-folder', 'btn-modal-project-file', 'project-path');

    // Modal launchers & file choosers
    document.getElementById('btn-quick-artist').addEventListener('click', openCreateArtistModal);
    document.getElementById('btn-add-artist').addEventListener('click', openCreateArtistModal);
    document.getElementById('btn-quick-album').addEventListener('click', openCreateAlbumModal);
    document.getElementById('btn-add-album').addEventListener('click', openCreateAlbumModal);
    document.getElementById('btn-quick-project').addEventListener('click', () => openCreateProjectModal('song'));
    document.getElementById('btn-add-project').addEventListener('click', () => openCreateProjectModal('song'));
    document.getElementById('project-entity-type').addEventListener('change', (e) => populateProjectEntitySelect(e.target.value));

    document.getElementById('btn-edit-attach-audio').addEventListener('click', async () => {
        const songFile = document.getElementById('edit-song-file').value;
        if (songFile) await attachAudioToSong(songFile);
    });

    document.getElementById('btn-select-avatar').addEventListener('click', async () => {
        const path = await window.pywebview.api.select_file_to_import();
        if (path) {
            selectedArtistAvatarPath = path;
            document.getElementById('selected-avatar-name').innerText = path.split(/[\\/]/).pop();
        }
    });

    document.getElementById('btn-select-cover').addEventListener('click', async () => {
        const path = await window.pywebview.api.select_file_to_import();
        if (path) {
            selectedAlbumCoverPath = path;
            document.getElementById('selected-cover-name').innerText = path.split(/[\\/]/).pop();
        }
    });

    // Form submissions
    document.getElementById('form-create-artist').addEventListener('submit', async (e) => {
        e.preventDefault();
        const editSlug = document.getElementById('artist-edit-slug').value;
        const artistData = {
            name: document.getElementById('artist-name').value,
            real_name: document.getElementById('artist-real-name').value,
            dob: document.getElementById('artist-dob').value,
            country_id: document.getElementById('artist-country').value || null,
            avatar_file_src: selectedArtistAvatarPath,
            aliases: document.getElementById('artist-aliases').value.split(',').map(s => s.trim()),
            project_path: document.getElementById('artist-project-path').value.trim() || null
        };
        const res = editSlug
            ? await window.pywebview.api.update_artist(editSlug, artistData)
            : await window.pywebview.api.create_artist(artistData);
        if (res.status === 'success') {
            closeModal('modal-artist');
            await refreshLibraryData();
            document.getElementById('form-create-artist').reset();
            selectedArtistAvatarPath = null;
            document.getElementById('selected-avatar-name').innerText = '';
        } else alert('Error: ' + res.message);
    });

    document.getElementById('form-create-album').addEventListener('submit', async (e) => {
        e.preventDefault();
        const editSlug = document.getElementById('album-edit-slug').value;
        const albumData = {
            name: document.getElementById('album-title').value,
            artist_slug: document.getElementById('album-artist').value,
            release_date: document.getElementById('album-release-date').value,
            cover_file_src: selectedAlbumCoverPath,
            project_path: document.getElementById('album-project-path').value.trim() || null
        };
        const res = editSlug
            ? await window.pywebview.api.update_album(editSlug, albumData)
            : await window.pywebview.api.create_album(albumData);
        if (res.status === 'success') {
            closeModal('modal-album');
            await refreshLibraryData();
            document.getElementById('form-create-album').reset();
            selectedAlbumCoverPath = null;
            document.getElementById('selected-cover-name').innerText = '';
        } else alert('Error: ' + res.message);
    });

    document.getElementById('import-song-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('import-song-title').value.trim();
        if (!selectedSongImportPath && !title) {
            alert('Please enter a song title (or select an audio file).');
            return;
        }
        const songData = {
            song_name: title,
            main_artists: selectedImportMainArtists.map(x => x.id),
            featured_artists: selectedImportFeatArtists.map(x => x.id),
            album_slug: document.getElementById('import-album').value || null,
            track_number: document.getElementById('import-track-no').value || null,
            key: document.getElementById('import-key').value || null,
            scale: document.getElementById('import-scale').value || null,
            tempo: document.getElementById('import-tempo').value || null,
            release_date: document.getElementById('import-release-date').value || null,
            genres: selectedImportGenres.map(x => x.id),
            tags: selectedImportTags.map(x => x.id),
            ai_generated: document.getElementById('import-ai-generated').checked,
            project_path: document.getElementById('import-project-path').value.trim() || null
        };
        const res = await window.pywebview.api.import_song(selectedSongImportPath, songData);
        if (res.status === 'success') {
            alert(res.has_audio ? 'Song imported successfully!' : 'Song registered (without audio file yet)!');
            document.getElementById('import-song-form').reset();
            document.getElementById('selected-file-details').classList.add('hidden');
            document.getElementById('selected-file-name').innerText = '';
            selectedSongImportPath = null;
            selectedImportMainArtists = [];
            selectedImportFeatArtists = [];
            selectedImportGenres = [];
            selectedImportTags = [];
            ['badge-main-artists', 'badge-feat-artists', 'badge-genres', 'badge-tags'].forEach(id => renderBadges(id, []));
            updateImportSubmitButton();
            await refreshLibraryData();
            switchView('songs');
        } else alert('Error importing song: ' + res.message);
    });

    document.getElementById('form-edit-song').addEventListener('submit', async (e) => {
        e.preventDefault();
        const songFile = document.getElementById('edit-song-file').value;
        const songData = {
            song_name: document.getElementById('edit-song-title').value,
            main_artists: selectedEditMainArtists.map(x => x.id),
            featured_artists: selectedEditFeatArtists.map(x => x.id),
            album_slug: document.getElementById('edit-album').value || null,
            track_number: document.getElementById('edit-track-no').value || null,
            key: document.getElementById('edit-key').value || null,
            scale: document.getElementById('edit-scale').value || null,
            tempo: document.getElementById('edit-tempo').value || null,
            release_date: document.getElementById('edit-release-date').value || null,
            genres: selectedEditGenres.map(x => x.id),
            tags: selectedEditTags.map(x => x.id),
            ai_generated: document.getElementById('edit-ai-generated').checked,
            project_path: document.getElementById('edit-song-project-path').value.trim() || null
        };
        const res = await window.pywebview.api.update_song(songFile, songData);
        if (res.status === 'success') {
            closeModal('modal-edit-song');
            await refreshLibraryData();
        } else alert('Error updating song: ' + res.message);
    });

    document.getElementById('form-project').addEventListener('submit', async (e) => {
        e.preventDefault();
        const editId = document.getElementById('project-edit-id').value;
        const payload = {
            entity_type: document.getElementById('project-entity-type').value,
            entity_id: document.getElementById('project-entity-id').value,
            project_name: document.getElementById('project-name').value,
            project_path: document.getElementById('project-path').value,
            notes: document.getElementById('project-notes').value
        };
        const res = editId
            ? await window.pywebview.api.update_project(editId, payload)
            : await window.pywebview.api.create_project(payload);
        if (res.status === 'success') {
            closeModal('modal-project');
            await refreshLibraryData();
        } else alert('Error saving project: ' + res.message);
    });

    // Filters
    const triggerSongFilter = () => renderSongsTable(getFilteredSongs());
    ['search-songs', 'filter-tag', 'filter-genre', 'filter-key', 'filter-scale', 'filter-audio'].forEach(id => {
        const el = document.getElementById(id);
        el.addEventListener(id === 'search-songs' ? 'input' : 'change', triggerSongFilter);
    });

    const triggerProjectFilter = () => renderProjectsTable(getFilteredProjects());
    document.getElementById('search-projects').addEventListener('input', triggerProjectFilter);
    document.getElementById('filter-project-type').addEventListener('change', triggerProjectFilter);
}
