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

    audio.src = `/media/song/${encodeURIComponent(audioFilename)}`;
    audio.play();
    isPlaying = true;

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
        const pct = dur > 0 ? (cur / dur) * 100 : 0;
        document.getElementById('player-progress-fill').style.width = `${pct}%`;
    });

    const progressBar = document.getElementById('player-progress-bar');
    progressBar.addEventListener('click', (e) => {
        const rect = progressBar.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        if (audio.duration) audio.currentTime = pct * audio.duration;
    });

    const volumeBar = document.getElementById('player-volume-bar');
    volumeBar.addEventListener('click', (e) => {
        const rect = volumeBar.getBoundingClientRect();
        const pct = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
        audio.volume = pct;
        document.getElementById('player-volume-fill').style.width = `${pct * 100}%`;
    });

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
            renderSongsTable(getFilteredSongs());
        }
    });
}
