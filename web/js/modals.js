// Tag/artist/genre badge inputs, linked projects mini-panel, and modal launchers

function setupTagInput(inputId, targetList, badgeId, kind) {
    const input = document.getElementById(inputId);
    if (!input) return;

    input.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        const val = input.value.trim();
        if (!val || targetList.find(x => x.label.toLowerCase() === val.toLowerCase())) return;

        let id = val;
        if (kind === 'artist') {
            const m = (metadataOptions.artists || []).find(a => a.real_name.toLowerCase() === val.toLowerCase());
            if (m) id = m.slug;
        } else if (kind === 'genre') {
            const m = (metadataOptions.genres || []).find(g => g.genre_name.toLowerCase() === val.toLowerCase());
            if (m) id = m.id;
        } else if (kind === 'tag') {
            const m = (metadataOptions.tags || []).find(t => t.tag_name.toLowerCase() === val.toLowerCase());
            if (m) id = m.id;
        }

        targetList.push({ id, label: val });
        renderBadges(badgeId, targetList);
        syncAiToggleFromTags(badgeId, targetList);
        input.value = '';
    });
}

function syncAiToggleFromTags(badgeId, list) {
    if (badgeId === 'badge-tags') {
        const cb = document.getElementById('import-ai-generated');
        if (cb) cb.checked = list.some(x => x.label.toLowerCase() === 'ai generated');
    } else if (badgeId === 'edit-badge-tags') {
        const cb = document.getElementById('edit-ai-generated');
        if (cb) cb.checked = list.some(x => x.label.toLowerCase() === 'ai generated');
    }
}

function toggleAiTagInList(checked, targetList, badgeId) {
    const idx = targetList.findIndex(x => x.label.toLowerCase() === 'ai generated');
    if (checked && idx === -1) {
        const m = (metadataOptions.tags || []).find(t => t.tag_name.toLowerCase() === 'ai generated');
        targetList.push({ id: m ? m.id : 'AI Generated', label: 'AI Generated' });
    } else if (!checked && idx !== -1) {
        targetList.splice(idx, 1);
    }
    renderBadges(badgeId, targetList);
}

function removeBadgeItem(listName, id) {
    const strId = String(id);
    const map = {
        'import-main': [() => { selectedImportMainArtists = selectedImportMainArtists.filter(x => String(x.id) !== strId); return selectedImportMainArtists; }, 'badge-main-artists'],
        'import-feat': [() => { selectedImportFeatArtists = selectedImportFeatArtists.filter(x => String(x.id) !== strId); return selectedImportFeatArtists; }, 'badge-feat-artists'],
        'import-genre': [() => { selectedImportGenres = selectedImportGenres.filter(x => String(x.id) !== strId); return selectedImportGenres; }, 'badge-genres'],
        'import-tag': [() => { selectedImportTags = selectedImportTags.filter(x => String(x.id) !== strId); return selectedImportTags; }, 'badge-tags'],
        'edit-main': [() => { selectedEditMainArtists = selectedEditMainArtists.filter(x => String(x.id) !== strId); return selectedEditMainArtists; }, 'edit-badge-main-artists'],
        'edit-feat': [() => { selectedEditFeatArtists = selectedEditFeatArtists.filter(x => String(x.id) !== strId); return selectedEditFeatArtists; }, 'edit-badge-feat-artists'],
        'edit-genre': [() => { selectedEditGenres = selectedEditGenres.filter(x => String(x.id) !== strId); return selectedEditGenres; }, 'edit-badge-genres'],
        'edit-tag': [() => { selectedEditTags = selectedEditTags.filter(x => String(x.id) !== strId); return selectedEditTags; }, 'edit-badge-tags']
    };
    const entry = map[listName];
    if (!entry) return;
    const updated = entry[0]();
    renderBadges(entry[1], updated);
    syncAiToggleFromTags(entry[1], updated);
}

function renderBadges(containerId, list) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    const listNameMap = {
        'badge-main-artists': 'import-main',
        'badge-feat-artists': 'import-feat',
        'badge-genres': 'import-genre',
        'badge-tags': 'import-tag',
        'edit-badge-main-artists': 'edit-main',
        'edit-badge-feat-artists': 'edit-feat',
        'edit-badge-genres': 'edit-genre',
        'edit-badge-tags': 'edit-tag'
    };
    const listName = listNameMap[containerId] || '';

    list.forEach(item => {
        const span = document.createElement('span');
        span.className = item.label.toLowerCase() === 'ai generated' ? 'tag-badge pill-ai' : 'tag-badge';
        span.innerHTML = `${escapeHtml(item.label)} <span class="tag-badge-remove">&times;</span>`;
        span.querySelector('.tag-badge-remove').addEventListener('click', () => removeBadgeItem(listName, item.id));
        container.appendChild(span);
    });
}

function renderEntityLinkedProjects(containerId, entityType, entityId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const linked = projectsList.filter(p => p.entity_type === entityType && p.entity_id === entityId);
    if (linked.length === 0) {
        container.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    container.classList.remove('hidden');
    container.innerHTML = `<div class="linked-projects-box"><span class="form-label">Linked Projects (${linked.length})</span></div>`;
    const box = container.firstElementChild;

    linked.forEach(p => {
        const row = document.createElement('div');
        row.className = 'linked-project-item';
        row.innerHTML = `
            <div style="min-width: 0; flex: 1;">
                <div style="font-weight: 600;">${escapeHtml(p.project_name)}</div>
                <div class="linked-project-path">${escapeHtml(p.project_path)}</div>
            </div>
            <div style="display:flex; gap: 6px;">
                <button type="button" class="btn btn-secondary btn-sm" data-action="open" title="Open"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>
                <button type="button" class="btn btn-danger btn-sm" data-action="delete" title="Remove link"><i class="fa-solid fa-trash"></i></button>
            </div>
        `;
        row.querySelector('[data-action="open"]').addEventListener('click', async () => {
            const res = await window.pywebview.api.open_project_path(p.project_path);
            if (res.status === 'error') alert(res.message);
        });
        row.querySelector('[data-action="delete"]').addEventListener('click', async () => {
            const res = await window.pywebview.api.delete_project(p.id);
            if (res.status === 'success') {
                await refreshLibraryData();
                renderEntityLinkedProjects(containerId, entityType, entityId);
            }
        });
        box.appendChild(row);
    });
}

async function attachAudioToSong(songFile) {
    const path = await window.pywebview.api.select_file_to_import();
    if (!path) return;
    const res = await window.pywebview.api.attach_song_audio(songFile, path);
    if (res.status === 'success') {
        await refreshLibraryData();
        const statusEl = document.getElementById('edit-song-audio-status');
        if (statusEl && document.getElementById('edit-song-file').value === songFile) {
            statusEl.innerText = res.audio_file;
        }
    } else {
        alert('Error attaching audio: ' + res.message);
    }
}

function _parsePairedBadges(namesStr, idsStr) {
    const result = [];
    if (!namesStr || !idsStr) return result;
    const names = namesStr.split(',').map(x => x.trim());
    const ids = idsStr.split(',').map(x => x.trim());
    for (let i = 0; i < names.length; i++) {
        if (names[i]) result.push({ id: ids[i], label: names[i] });
    }
    return result;
}

function openEditSong(songFile) {
    const song = songsList.find(s => s.song_file === songFile);
    if (!song) return;

    document.getElementById('edit-song-file').value = songFile;
    document.getElementById('edit-song-title').value = song.song_name || '';
    document.getElementById('edit-track-no').value = song.track_number || '';
    document.getElementById('edit-tempo').value = song.tempo || '';
    document.getElementById('edit-release-date').value = song.release_date || '';
    document.getElementById('edit-key').value = song.key_name || '';
    document.getElementById('edit-scale').value = song.scale_name || '';
    document.getElementById('edit-album').value = song.album_name || '';
    document.getElementById('edit-song-project-path').value = '';
    document.getElementById('edit-song-audio-status').innerText = song.has_audio
        ? (song.audio_file || song.song_file)
        : 'No audio file attached yet';

    selectedEditMainArtists = _parsePairedBadges(song.main_artists, song.main_artists_slugs);
    selectedEditFeatArtists = _parsePairedBadges(song.feat_artists, song.feat_artists_slugs);
    selectedEditGenres = _parsePairedBadges(song.genres, song.genres_ids);
    selectedEditTags = _parsePairedBadges(song.tags, song.tags_ids);

    renderBadges('edit-badge-main-artists', selectedEditMainArtists);
    renderBadges('edit-badge-feat-artists', selectedEditFeatArtists);
    renderBadges('edit-badge-genres', selectedEditGenres);
    renderBadges('edit-badge-tags', selectedEditTags);
    syncAiToggleFromTags('edit-badge-tags', selectedEditTags);

    renderEntityLinkedProjects('edit-song-linked-projects', 'song', songFile);
    openModal('modal-edit-song');
}

function openEditArtist(slug) {
    const art = metadataOptions.artists.find(a => a.slug === slug);
    if (!art) return;

    document.getElementById('artist-edit-slug').value = slug;
    document.getElementById('artist-modal-title').innerText = 'Edit Artist Details';
    document.getElementById('artist-name').value = art.real_name || '';
    document.getElementById('artist-real-name').value = art.real_name || '';
    document.getElementById('artist-dob').value = art.date_of_birth || '';
    document.getElementById('artist-country').value = art.country_id || '';
    document.getElementById('artist-aliases').value = '';
    document.getElementById('artist-project-path').value = '';
    selectedArtistAvatarPath = null;
    document.getElementById('selected-avatar-name').innerText = art.avatar_image ? art.avatar_image.split('/').pop() : '';

    renderEntityLinkedProjects('artist-linked-projects', 'artist', slug);
    openModal('modal-artist');
}

function openEditAlbum(slug) {
    const alb = metadataOptions.albums.find(a => a.slug === slug);
    if (!alb) return;

    document.getElementById('album-edit-slug').value = slug;
    document.getElementById('album-modal-title').innerText = 'Edit Album Details';
    document.getElementById('album-title').value = alb.album_name || '';
    document.getElementById('album-artist').value = alb.artist_slug || '';
    document.getElementById('album-release-date').value = alb.release_date || '';
    document.getElementById('album-project-path').value = '';
    selectedAlbumCoverPath = null;
    document.getElementById('selected-cover-name').innerText = alb.album_cover ? alb.album_cover.split('/').pop() : '';

    renderEntityLinkedProjects('album-linked-projects', 'album', slug);
    openModal('modal-album');
}

function openCreateArtistModal() {
    document.getElementById('artist-edit-slug').value = '';
    document.getElementById('artist-modal-title').innerText = 'Add New Artist';
    document.getElementById('form-create-artist').reset();
    selectedArtistAvatarPath = null;
    document.getElementById('selected-avatar-name').innerText = '';
    document.getElementById('artist-linked-projects').classList.add('hidden');
    openModal('modal-artist');
}

function openCreateAlbumModal() {
    document.getElementById('album-edit-slug').value = '';
    document.getElementById('album-modal-title').innerText = 'Add New Album';
    document.getElementById('form-create-album').reset();
    selectedAlbumCoverPath = null;
    document.getElementById('selected-cover-name').innerText = '';
    document.getElementById('album-linked-projects').classList.add('hidden');
    openModal('modal-album');
}

function populateProjectEntitySelect(entityType, selectedId = '') {
    const sel = document.getElementById('project-entity-id');
    if (!sel) return;
    sel.innerHTML = '<option value="">Select item...</option>';
    if (entityType === 'song') {
        songsList.forEach(s => { sel.innerHTML += `<option value="${escapeHtml(s.song_file)}">${escapeHtml(s.song_name)}</option>`; });
    } else if (entityType === 'artist') {
        (metadataOptions.artists || []).forEach(a => { sel.innerHTML += `<option value="${escapeHtml(a.slug)}">${escapeHtml(a.real_name)}</option>`; });
    } else if (entityType === 'album') {
        (metadataOptions.albums || []).forEach(al => { sel.innerHTML += `<option value="${escapeHtml(al.slug)}">${escapeHtml(al.album_name)}</option>`; });
    }
    if (selectedId) sel.value = selectedId;
}

function openCreateProjectModal(defaultType = 'song', defaultEntityId = '') {
    document.getElementById('project-edit-id').value = '';
    document.getElementById('project-modal-title').innerText = 'Link Production Project';
    document.getElementById('form-project').reset();
    document.getElementById('project-entity-type').value = defaultType;
    populateProjectEntitySelect(defaultType, defaultEntityId);
    openModal('modal-project');
}

function openEditProjectModal(proj) {
    document.getElementById('project-edit-id').value = proj.id;
    document.getElementById('project-modal-title').innerText = 'Edit Project Link';
    document.getElementById('project-entity-type').value = proj.entity_type;
    populateProjectEntitySelect(proj.entity_type, proj.entity_id);
    document.getElementById('project-name').value = proj.project_name || '';
    document.getElementById('project-path').value = proj.project_path || '';
    document.getElementById('project-notes').value = proj.notes || '';
    openModal('modal-project');
}

function bindProjectPathPickers(folderBtnId, fileBtnId, inputId) {
    const folderBtn = document.getElementById(folderBtnId);
    const fileBtn = document.getElementById(fileBtnId);
    const input = document.getElementById(inputId);

    if (folderBtn && input) {
        folderBtn.addEventListener('click', async () => {
            const path = await window.pywebview.api.select_project_folder();
            if (path) input.value = path;
        });
    }
    if (fileBtn && input) {
        fileBtn.addEventListener('click', async () => {
            const path = await window.pywebview.api.select_project_file();
            if (path) input.value = path;
        });
    }
}
