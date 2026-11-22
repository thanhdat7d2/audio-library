// Shared application state & utility helpers

let libraryPath = null;
let songsList = [];
let projectsList = [];
let metadataOptions = {
    keys: [],
    scales: [],
    genres: [],
    moods: [],
    tags: [],
    artists: [],
    albums: [],
    countries: []
};

// Multi-select form caches
let selectedImportMainArtists = [];
let selectedImportFeatArtists = [];
let selectedImportGenres = [];
let selectedImportTags = [];

let selectedEditMainArtists = [];
let selectedEditFeatArtists = [];
let selectedEditGenres = [];
let selectedEditTags = [];

// Pending file paths in modals / import
let selectedArtistAvatarPath = null;
let selectedAlbumCoverPath = null;
let selectedSongImportPath = null;
let selectedSpreadsheetPath = null;

// Audio playback state
let currentPlaylist = [];
let currentIndex = -1;
const audio = document.getElementById('main-audio-element');
let isPlaying = false;

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatTime(seconds) {
    if (isNaN(seconds) || seconds === 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
}

function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

if (!String.prototype.strip) {
    String.prototype.strip = function() {
        return this.replace(/^\s+|\s+$/g, '');
    };
}
