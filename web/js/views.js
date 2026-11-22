// Dropdown population, filtering, and catalog/projects view renderers

function populateDropdowns() {
    const keySelects = [
        document.getElementById('filter-key'),
        document.getElementById('import-key'),
        document.getElementById('edit-key')
    ];
    keySelects.forEach(sel => {
        if (!sel) return;
        const prev = sel.value;
        sel.innerHTML = sel.id === 'filter-key' ? '<option value="">All Keys</option>' : '<option value="">Unknown</option>';
        (metadataOptions.keys || []).forEach(k => {
            sel.innerHTML += `<option value="${escapeHtml(k)}">${escapeHtml(k)}</option>`;
        });
        sel.value = prev;
    });

    const scaleSelects = [
        document.getElementById('filter-scale'),
        document.getElementById('import-scale'),
        document.getElementById('edit-scale')
    ];
    scaleSelects.forEach(sel => {
        if (!sel) return;
        const prev = sel.value;
        sel.innerHTML = sel.id === 'filter-scale' ? '<option value="">All Scales</option>' : '<option value="">Unknown</option>';
        (metadataOptions.scales || []).forEach(s => {
            sel.innerHTML += `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`;
        });
        sel.value = prev;
    });

    const countrySel = document.getElementById('artist-country');
    if (countrySel) {
        countrySel.innerHTML = '<option value="">Select country...</option>';
        (metadataOptions.countries || []).forEach(c => {
            countrySel.innerHTML += `<option value="${c.id}">${escapeHtml(c.country_name)}</option>`;
        });
    }

    const albumArtistSel = document.getElementById('album-artist');
    if (albumArtistSel) {
        albumArtistSel.innerHTML = '<option value="">Select artist...</option>';
        (metadataOptions.artists || []).forEach(art => {
            albumArtistSel.innerHTML += `<option value="${escapeHtml(art.slug)}">${escapeHtml(art.real_name)}</option>`;
        });
    }

    const genreFilter = document.getElementById('filter-genre');
    if (genreFilter) {
        const prev = genreFilter.value;
        genreFilter.innerHTML = '<option value="">All Genres</option>';
        (metadataOptions.genres || []).forEach(g => {
            genreFilter.innerHTML += `<option value="${g.id}">${escapeHtml(g.genre_name)}</option>`;
        });
        genreFilter.value = prev;
    }

    const tagFilter = document.getElementById('filter-tag');
    if (tagFilter) {
        const prev = tagFilter.value;
        tagFilter.innerHTML = '<option value="">All Tags</option>';
        (metadataOptions.tags || []).forEach(t => {
            tagFilter.innerHTML += `<option value="${escapeHtml(t.tag_name)}">${escapeHtml(t.tag_name)}</option>`;
        });
        tagFilter.value = prev;
    }

    const fillDatalist = (id, items, key) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = (items || []).map(item => `<option value="${escapeHtml(item[key])}"></option>`).join('');
    };
    fillDatalist('artists-datalist', metadataOptions.artists, 'real_name');
    fillDatalist('albums-datalist', metadataOptions.albums, 'album_name');
    fillDatalist('genres-datalist', metadataOptions.genres, 'genre_name');
    fillDatalist('tags-datalist', metadataOptions.tags, 'tag_name');
}

function getFilteredSongs() {
    const query = (document.getElementById('search-songs')?.value || '').toLowerCase();
    const genreId = document.getElementById('filter-genre')?.value || '';
    const tagName = (document.getElementById('filter-tag')?.value || '').toLowerCase();
    const key = document.getElementById('filter-key')?.value || '';
    const scale = document.getElementById('filter-scale')?.value || '';
    const audioFilter = document.getElementById('filter-audio')?.value || '';

    return songsList.filter(song => {
        const matchesQuery = !query ||
            (song.song_name && song.song_name.toLowerCase().includes(query)) ||
            (song.main_artists && song.main_artists.toLowerCase().includes(query)) ||
            (song.feat_artists && song.feat_artists.toLowerCase().includes(query)) ||
            (song.tags && song.tags.toLowerCase().includes(query));

        let matchesGenre = true;
        if (genreId) {
            const genreObj = (metadataOptions.genres || []).find(g => g.id == genreId);
            const genreName = genreObj ? genreObj.genre_name.toLowerCase() : '';
            matchesGenre = Boolean(song.genres && song.genres.toLowerCase().includes(genreName));
        }

        let matchesTag = true;
        if (tagName) {
            const songTags = (song.tags || '').split(',').map(t => t.trim().toLowerCase());
            matchesTag = songTags.includes(tagName);
        }

        const matchesKey = !key || song.key_name === key;
        const matchesScale = !scale || song.scale_name === scale;
        const matchesAudio = !audioFilter || (audioFilter === 'has' ? Boolean(song.has_audio) : !song.has_audio);

        return matchesQuery && matchesGenre && matchesTag && matchesKey && matchesScale && matchesAudio;
    });
}

function getFilteredProjects() {
    const query = (document.getElementById('search-projects')?.value || '').toLowerCase();
    const typeFilter = document.getElementById('filter-project-type')?.value || '';

    return projectsList.filter(p => {
        const matchesType = !typeFilter || p.entity_type === typeFilter;
        const matchesQuery = !query ||
            (p.project_name && p.project_name.toLowerCase().includes(query)) ||
            (p.project_path && p.project_path.toLowerCase().includes(query)) ||
            (p.entity_label && p.entity_label.toLowerCase().includes(query)) ||
            (p.notes && p.notes.toLowerCase().includes(query));
        return matchesType && matchesQuery;
    });
}

function renderTagPills(tagsStr) {
    if (!tagsStr) return '<span style="color: var(--text-muted);">-</span>';
    const tags = tagsStr.split(',').map(t => t.trim()).filter(Boolean);
    if (tags.length === 0) return '<span style="color: var(--text-muted);">-</span>';
    return `<div class="tag-list-cell">${tags.map(t => {
        const isAi = t.toLowerCase() === 'ai generated';
        const cls = isAi ? 'pill-badge pill-ai' : 'pill-badge';
        const icon = isAi ? '<i class="fa-solid fa-wand-magic-sparkles"></i>' : '';
        return `<span class="${cls}">${icon}${escapeHtml(t)}</span>`;
    }).join('')}</div>`;
}

function renderDashboardRecent() {
    const grid = document.getElementById('dashboard-recent-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const recent = songsList.slice(0, 8);
    if (recent.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; padding: 20px 0;">No tracks yet. Add or import songs to get started.</div>';
        return;
    }

    recent.forEach((song) => {
        const masterIdx = songsList.findIndex(s => s.song_file === song.song_file);
        const coverUrl = `/media/song-cover/${encodeURIComponent(song.song_file)}`;
        const card = document.createElement('div');
        card.className = 'media-card';
        card.innerHTML = `
            <div class="media-img" style="display:flex; align-items:center; justify-content:center; overflow:hidden; position:relative;">
                <i class="fa-solid fa-music" style="font-size: 28px; color: var(--text-muted);"></i>
                <img src="${coverUrl}" style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover;" onload="this.previousElementSibling.style.display='none'" onerror="this.remove()">
            </div>
            <div class="media-title">${escapeHtml(song.song_name)}</div>
            <div class="media-subtitle">${escapeHtml(song.main_artists || 'Unknown Artist')}</div>
        `;
        card.addEventListener('click', () => {
            if (song.has_audio) playSongAtIndex(masterIdx, songsList);
            else openEditSong(song.song_file);
        });
        grid.appendChild(card);
    });
}

function renderSongsTable(songs) {
    const body = document.getElementById('songs-list-body');
    body.innerHTML = '';

    if (songs.length === 0) {
        body.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 40px;">No songs found. Click "Add / Import" to add tracks or import a spreadsheet.</td></tr>';
        return;
    }

    songs.forEach((song) => {
        const masterIdx = songsList.findIndex(s => s.song_file === song.song_file);
        const hasAudio = Boolean(song.has_audio);
        const isCurrent = hasAudio && currentIndex >= 0 && currentPlaylist[currentIndex]?.song_file === song.song_file;
        const playIcon = (isCurrent && isPlaying) ? 'fa-solid fa-pause' : 'fa-solid fa-play';
        const keyScaleStr = (song.key_name || song.scale_name) ? `${song.key_name || ''} ${song.scale_name || ''}`.trim() : '-';
        const coverUrl = `/media/song-cover/${encodeURIComponent(song.song_file)}`;

        const tr = document.createElement('tr');
        tr.className = isCurrent ? 'playing' : '';

        const playCellHtml = hasAudio
            ? `<button class="btn-play-row" data-action="play" title="Play"><i class="${playIcon}"></i></button>`
            : `<button class="btn-play-row" data-action="attach" title="Attach audio file" style="color: #f59e0b;"><i class="fa-solid fa-upload"></i></button>`;

        const noAudioBadge = hasAudio ? '' : `<span class="pill-badge pill-no-audio">No Audio</span>`;
        const projectBadge = song.project_count > 0
            ? `<button class="pill-badge pill-project" data-action="projects" title="View linked projects"><i class="fa-solid fa-sliders"></i> ${song.project_count}</button>`
            : '';

        tr.innerHTML = `
            <td>${playCellHtml}</td>
            <td>
                <div class="song-title-cell">
                    <div class="song-row-cover-wrap">
                        <i class="fa-solid fa-music song-row-cover-fallback"></i>
                        <img src="${coverUrl}" class="song-row-cover" style="position:absolute; inset:0;" onload="this.previousElementSibling.style.display='none'" onerror="this.remove()" loading="lazy">
                    </div>
                    <div style="min-width:0;">
                        <span class="song-title-text" style="font-weight: 500;">${escapeHtml(song.song_name)}</span>${noAudioBadge}
                    </div>
                </div>
            </td>
            <td>${escapeHtml(song.main_artists || 'Unknown Artist')} ${song.feat_artists ? `<span style="color: var(--text-secondary); font-size:12px;">(feat. ${escapeHtml(song.feat_artists)})</span>` : ''}</td>
            <td style="color: var(--text-secondary);">${escapeHtml(song.album_name || '-')}</td>
            <td style="color: var(--text-secondary);">${escapeHtml(song.genres || '-')}</td>
            <td>${renderTagPills(song.tags)}</td>
            <td style="color: var(--text-secondary);">${escapeHtml(keyScaleStr)}</td>
            <td style="color: var(--text-secondary);">${song.tempo || '-'}</td>
            <td style="color: var(--text-secondary); font-family: monospace;">${hasAudio ? formatTime(song.duration || 0) : '-'}</td>
            <td>
                <div style="display:flex; align-items:center; gap: 6px; justify-content: flex-end;">
                    ${projectBadge}
                    <button class="btn-secondary btn btn-sm" data-action="link-project" title="Link production project"><i class="fa-solid fa-link"></i></button>
                    <button class="btn-secondary btn btn-sm" data-action="edit" title="Edit song"><i class="fa-solid fa-pen-to-square"></i></button>
                </div>
            </td>
        `;

        tr.addEventListener('click', (e) => {
            const actionBtn = e.target.closest('[data-action]');
            if (actionBtn) {
                e.stopPropagation();
                const action = actionBtn.getAttribute('data-action');
                if (action === 'play') playSongAtIndex(masterIdx, songsList);
                else if (action === 'attach') attachAudioToSong(song.song_file);
                else if (action === 'edit') openEditSong(song.song_file);
                else if (action === 'link-project') openCreateProjectModal('song', song.song_file);
                else if (action === 'projects') {
                    document.getElementById('filter-project-type').value = 'song';
                    document.getElementById('search-projects').value = song.song_name;
                    switchView('projects');
                }
                return;
            }
            if (hasAudio) playSongAtIndex(masterIdx, songsList);
            else openEditSong(song.song_file);
        });

        body.appendChild(tr);
    });
}

function renderArtistsView() {
    const grid = document.getElementById('artists-grid');
    grid.innerHTML = '';
    if (!metadataOptions.artists || metadataOptions.artists.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 40px;">No artists created yet.</div>';
        return;
    }

    metadataOptions.artists.forEach(art => {
        const fallback = 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=150&h=150&fit=crop';
        const imgUrl = art.avatar_image ? `/media/${art.avatar_image}` : fallback;
        const projBadge = art.project_count > 0
            ? `<button class="pill-badge pill-project media-project-badge" data-action="projects" title="View artist projects"><i class="fa-solid fa-sliders"></i> ${art.project_count}</button>`
            : '';

        const card = document.createElement('div');
        card.className = 'media-card media-card-artist';
        card.style.position = 'relative';
        card.innerHTML = `
            ${projBadge}
            <button class="btn btn-secondary btn-sm" data-action="edit" style="position: absolute; top: 10px; right: 10px; z-index: 5;" title="Edit artist">
                <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <img src="${imgUrl}" class="media-img" onerror="this.src='${fallback}'">
            <div class="media-title">${escapeHtml(art.real_name)}</div>
            <div class="media-subtitle">Artist</div>
        `;
        card.addEventListener('click', (e) => {
            const actionBtn = e.target.closest('[data-action]');
            if (!actionBtn) return;
            e.stopPropagation();
            const action = actionBtn.getAttribute('data-action');
            if (action === 'edit') openEditArtist(art.slug);
            else if (action === 'projects') {
                document.getElementById('filter-project-type').value = 'artist';
                document.getElementById('search-projects').value = art.real_name;
                switchView('projects');
            }
        });
        grid.appendChild(card);
    });
}

function renderAlbumsView() {
    const grid = document.getElementById('albums-grid');
    grid.innerHTML = '';
    if (!metadataOptions.albums || metadataOptions.albums.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 40px;">No albums created yet.</div>';
        return;
    }

    metadataOptions.albums.forEach(alb => {
        const fallback = 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=150&h=150&fit=crop';
        const imgUrl = alb.album_cover ? `/media/${alb.album_cover}` : fallback;
        const projBadge = alb.project_count > 0
            ? `<button class="pill-badge pill-project media-project-badge" data-action="projects" title="View album projects"><i class="fa-solid fa-sliders"></i> ${alb.project_count}</button>`
            : '';

        const card = document.createElement('div');
        card.className = 'media-card';
        card.style.position = 'relative';
        card.innerHTML = `
            ${projBadge}
            <button class="btn btn-secondary btn-sm" data-action="edit" style="position: absolute; top: 10px; right: 10px; z-index: 5;" title="Edit album">
                <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <img src="${imgUrl}" class="media-img" onerror="this.src='${fallback}'">
            <div class="media-title">${escapeHtml(alb.album_name)}</div>
            <div class="media-subtitle">Album</div>
        `;
        card.addEventListener('click', (e) => {
            const actionBtn = e.target.closest('[data-action]');
            if (!actionBtn) return;
            e.stopPropagation();
            const action = actionBtn.getAttribute('data-action');
            if (action === 'edit') openEditAlbum(alb.slug);
            else if (action === 'projects') {
                document.getElementById('filter-project-type').value = 'album';
                document.getElementById('search-projects').value = alb.album_name;
                switchView('projects');
            }
        });
        grid.appendChild(card);
    });
}

function renderProjectsTable(projects) {
    const body = document.getElementById('projects-list-body');
    if (!body) return;
    body.innerHTML = '';

    if (projects.length === 0) {
        body.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 40px;">No production projects linked yet. Click "Link Project" to add a project path.</td></tr>';
        return;
    }

    projects.forEach(proj => {
        const tr = document.createElement('tr');
        const pathStatus = proj.path_exists ? '' : '<span class="pill-badge pill-no-audio" style="margin-left: 6px;">Path Missing</span>';

        tr.innerHTML = `
            <td style="font-weight: 600;">${escapeHtml(proj.project_name)}</td>
            <td>
                <span class="pill-badge pill-entity-${escapeHtml(proj.entity_type)}" style="text-transform: capitalize; margin-right: 6px;">${escapeHtml(proj.entity_type)}</span>
                <span>${escapeHtml(proj.entity_label)}</span>
            </td>
            <td><span class="linked-project-path">${escapeHtml(proj.project_path)}</span>${pathStatus}</td>
            <td style="color: var(--text-secondary); font-size: 13px;">${escapeHtml(proj.notes || '-')}</td>
            <td>
                <div style="display:flex; gap: 6px;">
                    <button class="btn btn-primary btn-sm" data-action="open" title="Open project location"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>
                    <button class="btn btn-secondary btn-sm" data-action="edit" title="Edit project link"><i class="fa-solid fa-pen-to-square"></i></button>
                    <button class="btn btn-danger btn-sm" data-action="delete" title="Delete link"><i class="fa-solid fa-trash"></i></button>
                </div>
            </td>
        `;

        tr.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            e.stopPropagation();
            const action = btn.getAttribute('data-action');
            if (action === 'open') {
                const res = await window.pywebview.api.open_project_path(proj.project_path);
                if (res.status === 'error') alert(res.message);
            } else if (action === 'edit') {
                openEditProjectModal(proj);
            } else if (action === 'delete') {
                if (confirm(`Remove link to "${proj.project_name}"? (Your files on disk will not be deleted.)`)) {
                    const res = await window.pywebview.api.delete_project(proj.id);
                    if (res.status === 'success') await refreshLibraryData();
                    else alert('Error: ' + res.message);
                }
            }
        });
        body.appendChild(tr);
    });
}
