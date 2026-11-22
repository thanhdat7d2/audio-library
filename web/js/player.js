// Audio playback engine & player bar controls

function playSongAtIndex(index, playlist = songsList) {
    if (index < 0 || index >= playlist.length) return;

    const targetSong = playlist[index];
    if (!targetSong.has_audio) {
        alert(`"${targetSong.song_name}" does not have an audio file attached yet.`);
        return;
    }

    currentPlaylist = playlist;

    if (currentIndex === index) {
        togglePlayPause();
        return;
    }

    currentIndex = index;
    const song = currentPlaylist[currentIndex];
    const audioFilename = song.audio_file || song.song_file;
    const audioUrl = `/media/song/${encodeURIComponent(audioFilename)}`;

    audio.src = audioUrl;
    audio.play();
    isPlaying = true;
    loadWaveformForUrl(audioUrl, song.song_file);

    document.getElementById('current-title').innerText = song.song_name;
    document.getElementById('current-artist').innerText = song.main_artists || 'Unknown Artist';

    const currentCover = document.getElementById('current-cover');
    const placeholderCover = document.getElementById('player-placeholder-cover');

    const albumObj = (metadataOptions.albums || []).find(a => a.album_name === song.album_name);
    if (albumObj && albumObj.album_cover) {
        currentCover.src = `/media/${albumObj.album_cover}`;
        currentCover.classList.remove('hidden');
        placeholderCover.classList.add('hidden');
    } else {
        currentCover.classList.add('hidden');
        placeholderCover.classList.remove('hidden');
    }

    updatePlayerButtonState();
    renderSongsTable(getFilteredSongs());
}

function togglePlayPause() {
    if (currentIndex === -1 && songsList.length > 0) {
        const firstPlayable = songsList.findIndex(s => s.has_audio);
        if (firstPlayable !== -1) playSongAtIndex(firstPlayable);
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
    renderSongsTable(getFilteredSongs());
}

function updatePlayerButtonState() {
    const btn = document.getElementById('btn-play-pause');
    btn.innerHTML = isPlaying
        ? '<i class="fa-solid fa-circle-pause"></i>'
        : '<i class="fa-solid fa-circle-play"></i>';
}

function setupPlayerListeners() {
    setupWaveformInteractions();

    document.getElementById('btn-play-pause').addEventListener('click', togglePlayPause);

    document.getElementById('btn-prev').addEventListener('click', () => {
        for (let i = currentIndex - 1; i >= 0; i--) {
            if (currentPlaylist[i]?.has_audio) {
                playSongAtIndex(i, currentPlaylist);
                break;
            }
        }
    });

    document.getElementById('btn-next').addEventListener('click', () => {
        for (let i = currentIndex + 1; i < currentPlaylist.length; i++) {
            if (currentPlaylist[i]?.has_audio) {
                playSongAtIndex(i, currentPlaylist);
                break;
            }
        }
    });

    audio.addEventListener('timeupdate', () => {
        const cur = audio.currentTime;
        const dur = audio.duration || 0;
        document.getElementById('player-current-time').innerText = formatTime(cur);
        document.getElementById('player-total-time').innerText = formatTime(dur);
        drawWaveform(dur > 0 ? cur / dur : 0);
    });

    const volumeBar = document.getElementById('player-volume-bar');
    const setVolumeFromEvent = (e) => {
        const rect = volumeBar.getBoundingClientRect();
        const pct = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
        audio.volume = pct;
        document.getElementById('player-volume-fill').style.width = `${pct * 100}%`;
    };
    let volDragging = false;
    volumeBar.addEventListener('mousedown', (e) => { volDragging = true; setVolumeFromEvent(e); });
    window.addEventListener('mousemove', (e) => { if (volDragging) setVolumeFromEvent(e); });
    window.addEventListener('mouseup', () => { volDragging = false; });

    audio.addEventListener('ended', () => {
        let nextIdx = -1;
        for (let i = currentIndex + 1; i < currentPlaylist.length; i++) {
            if (currentPlaylist[i]?.has_audio) {
                nextIdx = i;
                break;
            }
        }
        if (nextIdx !== -1) {
            playSongAtIndex(nextIdx, currentPlaylist);
        } else {
            isPlaying = false;
            updatePlayerButtonState();
            drawWaveform(0);
            renderSongsTable(getFilteredSongs());
        }
    });
}
