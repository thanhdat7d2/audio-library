// App State
let libraryPath = null;
let songsList = [];
let metadataOptions = {
    keys: [],
    scales: [],
    genres: [],
    moods: [],
    artists: [],
    albums: [],
    countries: []
};

// Form selection caches (for multi-select inputs)
let selectedImportMainArtists = [];
let selectedImportFeatArtists = [];
let selectedImportGenres = [];

let selectedEditMainArtists = [];
let selectedEditFeatArtists = [];
let selectedEditGenres = [];

// Selected paths for uploads in modals
let selectedArtistAvatarPath = null;
let selectedAlbumCoverPath = null;
let selectedSongImportPath = null;

// Playback State
let currentPlaylist = [];
let currentIndex = -1;
const audio = document.getElementById('main-audio-element');
let isPlaying = false;

// Initialize on DOM load
window.addEventListener('DOMContentLoaded', () => {
    window.addEventListener('pywebviewready', () => {
        initApp();
    });
});

// Primary App Initialization
async function initApp() {
    setupEventListeners();
    await checkLibraryStatus();
}

async function checkLibraryStatus() {
    const res = await window.pywebview.api.get_library_status();
    if (res.status === 'configured') {
        libraryPath = res.library_path;
        document.getElementById('view-setup').classList.add('hidden');
        document.querySelectorAll('.nav-item').forEach(item => {
            if (item.id !== 'btn-change-library') {
                item.style.pointerEvents = 'all';
                item.style.opacity = '1';
            }
        });
        await refreshLibraryData();
        switchView('dashboard');
    } else {
        libraryPath = null;
        document.getElementById('view-setup').classList.remove('hidden');
        document.querySelectorAll('.view-panel').forEach(v => v.classList.add('hidden'));
        document.querySelectorAll('.nav-item').forEach(item => {
            if (item.id !== 'btn-change-library' && item.getAttribute('data-view') !== 'dashboard') {
                item.style.pointerEvents = 'none';
                item.style.opacity = '0.5';
            }
        });
    }
}

// Fetch all fresh DB data
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
    
    songsList = await window.pywebview.api.get_songs();
    renderSongsTable(songsList);
    renderArtistsView();
    renderAlbumsView();
}

// Navigation between views
function switchView(viewName) {
    if (!libraryPath && viewName !== 'setup') return;

    document.querySelectorAll('.sidebar .nav-item').forEach(item => {
        item.classList.remove('active');
    });

    const activeItem = document.querySelector(`.sidebar .nav-item[data-view="${viewName}"]`);
    if (activeItem) activeItem.classList.add('active');

    document.querySelectorAll('.view-panel').forEach(v => v.classList.add('hidden'));
    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) targetPanel.classList.remove('hidden');
    
    if (viewName === 'songs') {
        renderSongsTable(songsList);
    } else if (viewName === 'artists') {
        renderArtistsView();
    } else if (viewName === 'albums') {
        renderAlbumsView();
    }
}

// Populate UI Form Fields & Datalists
function populateDropdowns() {
    // 1. Select Dropdowns (Keys / Scales / Countries)
    const keySelects = [
        document.getElementById('filter-key'),
        document.getElementById('import-key'),
        document.getElementById('edit-key')
    ];
    keySelects.forEach(sel => {
        if (!sel) return;
        sel.innerHTML = sel.id === 'filter-key' ? '<option value="">All Keys</option>' : '<option value="">Unknown</option>';
        metadataOptions.keys.forEach(k => {
            sel.innerHTML += `<option value="${k}">${k}</option>`;
        });
    });

    const scaleSelects = [
        document.getElementById('filter-scale'),
        document.getElementById('import-scale'),
        document.getElementById('edit-scale')
    ];
    scaleSelects.forEach(sel => {
        if (!sel) return;
        sel.innerHTML = sel.id === 'filter-scale' ? '<option value="">All Scales</option>' : '<option value="">Unknown</option>';
        metadataOptions.scales.forEach(s => {
            sel.innerHTML += `<option value="${s}">${s}</option>`;
        });
    });

    const countrySel = document.getElementById('artist-country');
    if (countrySel) {
        countrySel.innerHTML = '<option value="">Select country...</option>';
        metadataOptions.countries.forEach(c => {
            countrySel.innerHTML += `<option value="${c.id}">${c.country_name}</option>`;
        });
    }

    const albumArtistSel = document.getElementById('album-artist');
    if (albumArtistSel) {
        albumArtistSel.innerHTML = '<option value="">Select artist...</option>';
        metadataOptions.artists.forEach(art => {
            albumArtistSel.innerHTML += `<option value="${art.slug}">${art.real_name}</option>`;
        });
    }

    const genreFilter = document.getElementById('filter-genre');
    if (genreFilter) {
        genreFilter.innerHTML = '<option value="">All Genres</option>';
        metadataOptions.genres.forEach(g => {
            genreFilter.innerHTML += `<option value="${g.id}">${g.genre_name}</option>`;
        });
    }

    // 2. Populate Autocomplete Datalists (Allows free-typing and suggestions)
    const artistsDatalist = document.getElementById('artists-datalist');
    if (artistsDatalist) {
        artistsDatalist.innerHTML = '';
        metadataOptions.artists.forEach(art => {
            artistsDatalist.innerHTML += `<option value="${art.real_name}"></option>`;
        });
    }

    const albumsDatalist = document.getElementById('albums-datalist');
    if (albumsDatalist) {
        albumsDatalist.innerHTML = '';
        metadataOptions.albums.forEach(alb => {
            albumsDatalist.innerHTML += `<option value="${alb.album_name}"></option>`;
        });
    }

    const genresDatalist = document.getElementById('genres-datalist');
    if (genresDatalist) {
        genresDatalist.innerHTML = '';
        metadataOptions.genres.forEach(g => {
            genresDatalist.innerHTML += `<option value="${g.genre_name}"></option>`;
        });
    }
}

// Render Data Views
function renderSongsTable(songs) {
    const body = document.getElementById('songs-list-body');
    body.innerHTML = '';
    
    if (songs.length === 0) {
        body.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 40px;">No songs found. Click "Import File" to add some music.</td></tr>';
        return;
    }

    songs.forEach((song, idx) => {
        const isCurrent = currentIndex >= 0 && currentPlaylist[currentIndex]?.song_file === song.song_file;
        const rowClass = isCurrent ? 'playing' : '';
        const playIcon = (isCurrent && isPlaying) ? 'fa-solid fa-pause' : 'fa-solid fa-play';
        const keyScaleStr = (song.key_name || song.scale_name) ? `${song.key_name || ''} ${song.scale_name || ''}`.trim() : 'Unknown';

        const tr = document.createElement('tr');
        tr.className = rowClass;
        tr.innerHTML = `
            <td>
                <button class="btn-play-row" onclick="event.stopPropagation(); playSongAtIndex(${idx}, songsList);"><i class="${playIcon}"></i></button>
            </td>
            <td style="font-weight: 500;" onclick="playSongAtIndex(${idx}, songsList);">${song.song_name}</td>
            <td onclick="playSongAtIndex(${idx}, songsList);">${song.main_artists || 'Unknown Artist'} ${song.feat_artists ? `<span style="color: var(--text-secondary); font-size:12px;">(feat. ${song.feat_artists})</span>` : ''}</td>
            <td onclick="playSongAtIndex(${idx}, songsList);">${song.album_name || '-'}</td>
            <td onclick="playSongAtIndex(${idx}, songsList);">${song.genres || '-'}</td>
            <td onclick="playSongAtIndex(${idx}, songsList);">${keyScaleStr}</td>
            <td onclick="playSongAtIndex(${idx}, songsList);">${song.tempo || '-'}</td>
            <td onclick="playSongAtIndex(${idx}, songsList);">${formatTime(song.duration || 0)}</td>
            <td>
                <button class="btn-secondary btn" style="padding: 6px 10px;" onclick="event.stopPropagation(); openEditSong('${song.song_file}')">
                    <i class="fa-solid fa-pen-to-square"></i>
                </button>
            </td>
        `;
        body.appendChild(tr);
    });
}

function renderArtistsView() {
    const grid = document.getElementById('artists-grid');
    grid.innerHTML = '';
    if (metadataOptions.artists.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 40px;">No artists created yet.</div>';
        return;
    }

    metadataOptions.artists.forEach(art => {
        const imgUrl = art.avatar_image ? `/media/${art.avatar_image}` : 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=150&h=150&fit=crop';
        
        const card = document.createElement('div');
        card.className = 'media-card media-card-artist glass-panel';
        card.style.position = 'relative';
        card.innerHTML = `
            <button class="btn btn-secondary" style="position: absolute; top: 10px; right: 10px; padding: 6px 10px; z-index: 5;" onclick="event.stopPropagation(); openEditArtist('${art.slug}')">
                <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <img src="${imgUrl}" class="media-img" onerror="this.src='https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=150&h=150&fit=crop'">
            <div class="media-title">${art.real_name}</div>
            <div class="media-subtitle">Artist</div>
        `;
        grid.appendChild(card);
    });
}

function renderAlbumsView() {
    const grid = document.getElementById('albums-grid');
    grid.innerHTML = '';
    if (metadataOptions.albums.length === 0) {
        grid.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 40px;">No albums created yet.</div>';
        return;
    }

    metadataOptions.albums.forEach(alb => {
        const imgUrl = alb.album_cover ? `/media/${alb.album_cover}` : 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=150&h=150&fit=crop';
        
        const card = document.createElement('div');
        card.className = 'media-card glass-panel';
        card.style.position = 'relative';
        card.innerHTML = `
            <button class="btn btn-secondary" style="position: absolute; top: 10px; right: 10px; padding: 6px 10px; z-index: 5;" onclick="event.stopPropagation(); openEditAlbum('${alb.slug}')">
                <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <img src="${imgUrl}" class="media-img" onerror="this.src='https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=150&h=150&fit=crop'">
            <div class="media-title">${alb.album_name}</div>
            <div class="media-subtitle">Album</div>
        `;
        grid.appendChild(card);
    });
}

// Tag inputs listener helper
function setupTagInput(inputId, targetList, badgeId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = input.value.trim();
            if (val && !targetList.find(x => x.label.toLowerCase() === val.toLowerCase())) {
                // Determine if this is a known slug in database
                let id = val;
                // If the input matches an artist real_name in database, map to its slug
                const matchArt = metadataOptions.artists.find(a => a.real_name.toLowerCase() === val.toLowerCase());
                const matchGenre = metadataOptions.genres.find(g => g.genre_name.toLowerCase() === val.toLowerCase());
                if (matchArt) {
                    id = matchArt.slug;
                } else if (matchGenre) {
                    id = matchGenre.id;
                }
                
                targetList.push({ id, label: val });
                renderBadges(badgeId, targetList);
                input.value = '';
            }
        }
    });
}

function removeBadgeItem(listName, id) {
    if (listName === 'import-main') {
        selectedImportMainArtists = selectedImportMainArtists.filter(x => x.id !== id);
        renderBadges('badge-main-artists', selectedImportMainArtists);
    } else if (listName === 'import-feat') {
        selectedImportFeatArtists = selectedImportFeatArtists.filter(x => x.id !== id);
        renderBadges('badge-feat-artists', selectedImportFeatArtists);
    } else if (listName === 'import-genre') {
        selectedImportGenres = selectedImportGenres.filter(x => x.id !== id);
        renderBadges('badge-genres', selectedImportGenres);
    } else if (listName === 'edit-main') {
        selectedEditMainArtists = selectedEditMainArtists.filter(x => x.id !== id);
        renderBadges('edit-badge-main-artists', selectedEditMainArtists);
    } else if (listName === 'edit-feat') {
        selectedEditFeatArtists = selectedEditFeatArtists.filter(x => x.id !== id);
        renderBadges('edit-badge-feat-artists', selectedEditFeatArtists);
    } else if (listName === 'edit-genre') {
        selectedEditGenres = selectedEditGenres.filter(x => x.id !== id);
        renderBadges('edit-badge-genres', selectedEditGenres);
    }
}

function renderBadges(containerId, list) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    
    // Map badge container to its remove list target
    let listName = '';
    if (containerId === 'badge-main-artists') listName = 'import-main';
    else if (containerId === 'badge-feat-artists') listName = 'import-feat';
    else if (containerId === 'badge-genres') listName = 'import-genre';
    else if (containerId === 'edit-badge-main-artists') listName = 'edit-main';
    else if (containerId === 'edit-badge-feat-artists') listName = 'edit-feat';
    else if (containerId === 'edit-badge-genres') listName = 'edit-genre';

    list.forEach(item => {
        container.innerHTML += `
            <span class="tag-badge">
                ${item.label}
                <span class="tag-badge-remove" onclick="removeBadgeItem('${listName}', '${item.id}')">&times;</span>
            </span>
        `;
    });
}

// Edit Mode Launchers
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

    // Main Artists
    selectedEditMainArtists = [];
    if (song.main_artists && song.main_artists_slugs) {
        const names = song.main_artists.split(',').map(x => x.trim());
        const slugs = song.main_artists_slugs.split(',').map(x => x.trim());
        for (let i = 0; i < names.length; i++) {
            if (names[i]) selectedEditMainArtists.push({ id: slugs[i], label: names[i] });
        }
    }
    renderBadges('edit-badge-main-artists', selectedEditMainArtists);

    // Feat Artists
    selectedEditFeatArtists = [];
    if (song.feat_artists && song.feat_artists_slugs) {
        const names = song.feat_artists.split(',').map(x => x.trim());
        const slugs = song.feat_artists_slugs.split(',').map(x => x.trim());
        for (let i = 0; i < names.length; i++) {
            if (names[i]) selectedEditFeatArtists.push({ id: slugs[i], label: names[i] });
        }
    }
    renderBadges('edit-badge-feat-artists', selectedEditFeatArtists);

    // Genres
    selectedEditGenres = [];
    if (song.genres && song.genres_ids) {
        const names = song.genres.split(',').map(x => x.trim());
        const ids = song.genres_ids.split(',').map(x => x.trim());
        for (let i = 0; i < names.length; i++) {
            if (names[i]) selectedEditGenres.push({ id: ids[i], label: names[i] });
        }
    }
    renderBadges('edit-badge-genres', selectedEditGenres);

    openModal('modal-edit-song');
}

function openEditArtist(slug) {
    const art = metadataOptions.artists.find(a => a.slug === slug);
    if (!art) return;
    
    document.getElementById('artist-edit-slug').value = slug;
    document.getElementById('artist-modal-title').innerText = "Edit Artist Details";
    document.getElementById('artist-name').value = art.real_name || '';
    document.getElementById('artist-real-name').value = art.real_name || '';
    document.getElementById('artist-dob').value = art.date_of_birth || '';
    document.getElementById('artist-country').value = art.country_id || '';
    document.getElementById('artist-aliases').value = '';
    
    selectedArtistAvatarPath = null;
    document.getElementById('selected-avatar-name').innerText = art.avatar_image ? art.avatar_image.split('/').pop() : '';

    openModal('modal-artist');
}

function openEditAlbum(slug) {
    const alb = metadataOptions.albums.find(a => a.slug === slug);
    if (!alb) return;
    
    document.getElementById('album-edit-slug').value = slug;
    document.getElementById('album-modal-title').innerText = "Edit Album Details";
    document.getElementById('album-title').value = alb.album_name || '';
    document.getElementById('album-artist').value = alb.artist_slug || '';
    document.getElementById('album-release-date').value = alb.release_date || '';
    
    selectedAlbumCoverPath = null;
    document.getElementById('selected-cover-name').innerText = alb.album_cover ? alb.album_cover.split('/').pop() : '';

    openModal('modal-album');
}

// Reset modals to Create Mode
function openCreateArtistModal() {
    document.getElementById('artist-edit-slug').value = '';
    document.getElementById('artist-modal-title').innerText = "Add New Artist";
    document.getElementById('form-create-artist').reset();
    selectedArtistAvatarPath = null;
    document.getElementById('selected-avatar-name').innerText = '';
    openModal('modal-artist');
}

function openCreateAlbumModal() {
    document.getElementById('album-edit-slug').value = '';
    document.getElementById('album-modal-title').innerText = "Add New Album";
    document.getElementById('form-create-album').reset();
    selectedAlbumCoverPath = null;
    document.getElementById('selected-cover-name').innerText = '';
    openModal('modal-album');
}

// Audio Playback Engine
function playSongAtIndex(index, playlist = songsList) {
    if (index < 0 || index >= playlist.length) return;
    
    currentPlaylist = playlist;
    
    if (currentIndex === index) {
        togglePlayPause();
        return;
    }

    currentIndex = index;
    const song = currentPlaylist[currentIndex];
    
    audio.src = `/media/song/${song.song_file}`;
    audio.play();
    isPlaying = true;
    
    document.getElementById('current-title').innerText = song.song_name;
    document.getElementById('current-artist').innerText = song.main_artists || 'Unknown Artist';
    
    const currentCover = document.getElementById('current-cover');
    const placeholderCover = document.getElementById('player-placeholder-cover');
    
    const albumObj = metadataOptions.albums.find(a => a.album_name === song.album_name);
    if (albumObj && albumObj.album_cover) {
        currentCover.src = `/media/${albumObj.album_cover}`;
        currentCover.classList.remove('hidden');
        placeholderCover.classList.add('hidden');
    } else {
        currentCover.classList.add('hidden');
        placeholderCover.classList.remove('hidden');
    }

    updatePlayerButtonState();
    renderSongsTable(songsList);
}

function togglePlayPause() {
    if (currentIndex === -1 && songsList.length > 0) {
        playSongAtIndex(0);
        return;
    }
    
    if (audio.paused) {
        audio.play();
        isPlaying = true;
    } else {
        audio.pause();
        isPlaying = false;
    }
    updatePlayerButtonState();
    renderSongsTable(songsList);
}

function updatePlayerButtonState() {
    const btn = document.getElementById('btn-play-pause');
    if (isPlaying) {
        btn.innerHTML = '<i class="fa-solid fa-circle-pause"></i>';
    } else {
        btn.innerHTML = '<i class="fa-solid fa-circle-play"></i>';
    }
}

// Event Listeners Configuration
function setupEventListeners() {
    document.querySelectorAll('.sidebar .nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            const view = e.currentTarget.getAttribute('data-view');
            if (view) switchView(view);
        });
    });

    document.getElementById('btn-select-folder').addEventListener('click', async () => {
        const res = await window.pywebview.api.select_library_folder();
        if (res.status === 'success') {
            await checkLibraryStatus();
        } else if (res.status === 'error') {
            alert("Error setting library: " + res.message);
        }
    });

    document.getElementById('btn-change-library').addEventListener('click', async () => {
        const res = await window.pywebview.api.select_library_folder();
        if (res.status === 'success') {
            await checkLibraryStatus();
        }
    });

    // Dropzone Song Import
    document.getElementById('import-dropzone').addEventListener('click', async () => {
        const path = await window.pywebview.api.select_file_to_import();
        if (path) {
            selectedSongImportPath = path;
            const filename = path.split('\\').pop().split('/').pop();
            document.getElementById('selected-file-name').innerText = filename;
            document.getElementById('selected-file-details').classList.remove('hidden');
            
            const cleanTitle = filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ");
            document.getElementById('import-song-title').value = cleanTitle;
        }
    });

    // Tag Inputs setup
    setupTagInput('import-main-artists-input', selectedImportMainArtists, 'badge-main-artists');
    setupTagInput('import-feat-artists-input', selectedImportFeatArtists, 'badge-feat-artists');
    setupTagInput('import-genres-input', selectedImportGenres, 'badge-genres');

    setupTagInput('edit-main-artists-input', selectedEditMainArtists, 'edit-badge-main-artists');
    setupTagInput('edit-feat-artists-input', selectedEditFeatArtists, 'edit-badge-feat-artists');
    setupTagInput('edit-genres-input', selectedEditGenres, 'edit-badge-genres');

    // Modal launchers
    document.getElementById('btn-quick-artist').addEventListener('click', openCreateArtistModal);
    document.getElementById('btn-add-artist').addEventListener('click', openCreateArtistModal);
    document.getElementById('btn-quick-album').addEventListener('click', openCreateAlbumModal);
    document.getElementById('btn-add-album').addEventListener('click', openCreateAlbumModal);

    // Modal File Choosers
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

    // Form Artist Create/Update Submit
    document.getElementById('form-create-artist').addEventListener('submit', async (e) => {
        e.preventDefault();
        const editSlug = document.getElementById('artist-edit-slug').value;
        const artistData = {
            name: document.getElementById('artist-name').value,
            real_name: document.getElementById('artist-real-name').value,
            dob: document.getElementById('artist-dob').value,
            country_id: document.getElementById('artist-country').value || null,
            avatar_file_src: selectedArtistAvatarPath,
            aliases: document.getElementById('artist-aliases').value.split(',').map(s => s.trim())
        };
        
        let res;
        if (editSlug) {
            res = await window.pywebview.api.update_artist(editSlug, artistData);
        } else {
            res = await window.pywebview.api.create_artist(artistData);
        }
        
        if (res.status === 'success') {
            closeModal('modal-artist');
            await refreshLibraryData();
            document.getElementById('form-create-artist').reset();
            selectedArtistAvatarPath = null;
            document.getElementById('selected-avatar-name').innerText = '';
        } else {
            alert("Error: " + res.message);
        }
    });

    // Form Album Create/Update Submit
    document.getElementById('form-create-album').addEventListener('submit', async (e) => {
        e.preventDefault();
        const editSlug = document.getElementById('album-edit-slug').value;
        const albumData = {
            name: document.getElementById('album-title').value,
            artist_slug: document.getElementById('album-artist').value,
            release_date: document.getElementById('album-release-date').value,
            cover_file_src: selectedAlbumCoverPath
        };
        
        let res;
        if (editSlug) {
            res = await window.pywebview.api.update_album(editSlug, albumData);
        } else {
            res = await window.pywebview.api.create_album(albumData);
        }
        
        if (res.status === 'success') {
            closeModal('modal-album');
            await refreshLibraryData();
            document.getElementById('form-create-album').reset();
            selectedAlbumCoverPath = null;
            document.getElementById('selected-cover-name').innerText = '';
        } else {
            alert("Error: " + res.message);
        }
    });

    // Form Import Song Submit
    document.getElementById('import-song-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedSongImportPath) {
            alert("Please select a file to import first.");
            return;
        }
        
        const songData = {
            song_name: document.getElementById('import-song-title').value,
            main_artists: selectedImportMainArtists.map(x => x.id),
            featured_artists: selectedImportFeatArtists.map(x => x.id),
            album_slug: document.getElementById('import-album').value || null,
            track_number: document.getElementById('import-track-no').value || null,
            key: document.getElementById('import-key').value || null,
            scale: document.getElementById('import-scale').value || null,
            tempo: document.getElementById('import-tempo').value || null,
            release_date: document.getElementById('import-release-date').value || null,
            genres: selectedImportGenres.map(x => x.id)
        };

        const res = await window.pywebview.api.import_song(selectedSongImportPath, songData);
        if (res.status === 'success') {
            alert("Song imported successfully!");
            document.getElementById('import-song-form').reset();
            document.getElementById('selected-file-details').classList.add('hidden');
            document.getElementById('selected-file-name').innerText = '';
            selectedSongImportPath = null;
            selectedImportMainArtists = [];
            selectedImportFeatArtists = [];
            selectedImportGenres = [];
            renderBadges('badge-main-artists', []);
            renderBadges('badge-feat-artists', []);
            renderBadges('badge-genres', []);
            
            await refreshLibraryData();
            switchView('songs');
        } else {
            alert("Error importing song: " + res.message);
        }
    });

    // Form Edit Song Submit
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
            genres: selectedEditGenres.map(x => x.id)
        };

        const res = await window.pywebview.api.update_song(songFile, songData);
        if (res.status === 'success') {
            closeModal('modal-edit-song');
            await refreshLibraryData();
        } else {
            alert("Error updating song: " + res.message);
        }
    });

    // Filtering & Searching
    const triggerFilter = () => {
        const query = document.getElementById('search-songs').value.toLowerCase();
        const genreId = document.getElementById('filter-genre').value;
        const key = document.getElementById('filter-key').value;
        const scale = document.getElementById('filter-scale').value;

        const filtered = songsList.filter(song => {
            const matchesQuery = !query || 
                                 (song.song_name && song.song_name.toLowerCase().includes(query)) ||
                                 (song.main_artists && song.main_artists.toLowerCase().includes(query)) ||
                                 (song.feat_artists && song.feat_artists.toLowerCase().includes(query));
            
            let matchesGenre = true;
            if (genreId) {
                const genreObj = metadataOptions.genres.find(g => g.id == genreId);
                const genreName = genreObj ? genreObj.genre_name.toLowerCase() : '';
                matchesGenre = song.genres && song.genres.toLowerCase().includes(genreName);
            }

            const matchesKey = !key || song.key_name === key;
            const matchesScale = !scale || song.scale_name === scale;

            return matchesQuery && matchesGenre && matchesKey && matchesScale;
        });

        renderSongsTable(filtered);
    };

    document.getElementById('search-songs').addEventListener('input', triggerFilter);
    document.getElementById('filter-genre').addEventListener('change', triggerFilter);
    document.getElementById('filter-key').addEventListener('change', triggerFilter);
    document.getElementById('filter-scale').addEventListener('change', triggerFilter);

    // Audio Playback Events
    document.getElementById('btn-play-pause').addEventListener('click', togglePlayPause);
    
    document.getElementById('btn-prev').addEventListener('click', () => {
        if (currentIndex > 0) playSongAtIndex(currentIndex - 1);
    });

    document.getElementById('btn-next').addEventListener('click', () => {
        if (currentIndex < currentPlaylist.length - 1) playSongAtIndex(currentIndex + 1);
    });

    audio.addEventListener('timeupdate', () => {
        const cur = audio.currentTime;
        const dur = audio.duration || 0;
        document.getElementById('player-current-time').innerText = formatTime(cur);
        document.getElementById('player-total-time').innerText = formatTime(dur);
        
        const pct = dur > 0 ? (cur / dur) * 100 : 0;
        document.getElementById('player-progress-fill').style.width = `${pct}%`;
    });

    const progressBar = document.getElementById('player-progress-bar');
    progressBar.addEventListener('click', (e) => {
        const rect = progressBar.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const width = rect.width;
        const pct = clickX / width;
        if (audio.duration) {
            audio.currentTime = pct * audio.duration;
        }
    });

    const volumeBar = document.getElementById('player-volume-bar');
    volumeBar.addEventListener('click', (e) => {
        const rect = volumeBar.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const width = rect.width;
        let pct = clickX / width;
        if (pct < 0) pct = 0;
        if (pct > 1) pct = 1;
        audio.volume = pct;
        document.getElementById('player-volume-fill').style.width = `${pct * 100}%`;
    });

    audio.addEventListener('ended', () => {
        if (currentIndex < currentPlaylist.length - 1) {
            playSongAtIndex(currentIndex + 1);
        } else {
            isPlaying = false;
            updatePlayerButtonState();
        }
    });
}

// Modals actions
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Helper formatting utilities
function formatTime(seconds) {
    if (isNaN(seconds) || seconds === 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// Native JS string helper
if (!String.prototype.strip) {
    String.prototype.strip = function() {
        return this.replace(/^\s+|\s+$/g, '');
    };
}
