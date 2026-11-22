// High-density slim-line HTML5 Canvas audio waveform decoder & renderer

const waveformCache = new Map();
const RAW_PEAK_RESOLUTION = 2048;
const BAR_WIDTH = 2;     // Always slim 2px vertical stripe
const BAR_GAP = 1.5;     // Constant tight gap at any viewport width
const BAR_PITCH = BAR_WIDTH + BAR_GAP;

let waveformRawPeaks = null;
let waveformProgress = 0;
let waveformHoverPct = null;
let waveformAudioCtx = null;
let activeWaveformKey = null;

function _placeholderPeaks(count) {
    const arr = new Array(count);
    for (let i = 0; i < count; i++) {
        arr[i] = 0.2 + 0.16 * Math.abs(Math.sin(i * 0.22)) + 0.08 * Math.abs(Math.cos(i * 0.57));
    }
    return arr;
}

function _resamplePeaks(raw, targetCount) {
    if (!raw || raw.length === 0) return _placeholderPeaks(targetCount);
    const out = new Array(targetCount);
    const ratio = raw.length / targetCount;
    for (let i = 0; i < targetCount; i++) {
        const start = Math.floor(i * ratio);
        const end = Math.max(start + 1, Math.min(raw.length, Math.floor((i + 1) * ratio)));
        let peak = 0;
        for (let j = start; j < end; j++) {
            if (raw[j] > peak) peak = raw[j];
        }
        out[i] = peak;
    }
    return out;
}

function drawWaveform(progress = waveformProgress) {
    waveformProgress = Math.min(1, Math.max(0, progress || 0));
    const canvas = document.getElementById('player-waveform-canvas');
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const dpr = window.devicePixelRatio || 1;
    const width = Math.round(rect.width * dpr);
    const height = Math.round(rect.height * dpr);
    if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
    }

    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const styles = getComputedStyle(document.documentElement);
    const accent = (styles.getPropertyValue('--accent') || '#10b981').trim();
    const muted = (styles.getPropertyValue('--waveform-muted') || 'rgba(148,163,184,0.26)').trim();

    // Compute bar count directly from CSS pixel width so stripe width & density stay constant
    const barCount = Math.max(24, Math.floor(rect.width / BAR_PITCH));
    const peaks = _resamplePeaks(waveformRawPeaks, barCount);
    const midY = rect.height / 2;
    const maxHalf = rect.height * 0.46;
    const playedX = waveformProgress * rect.width;

    for (let i = 0; i < barCount; i++) {
        const x = i * BAR_PITCH;
        const amp = Math.max(0.08, peaks[i]);
        const halfH = Math.max(1.5, amp * maxHalf);
        ctx.fillStyle = (x + BAR_WIDTH / 2 <= playedX) ? accent : muted;
        ctx.fillRect(x, midY - halfH, BAR_WIDTH, halfH * 2);
    }

    if (waveformHoverPct !== null) {
        const hx = waveformHoverPct * rect.width;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
        ctx.fillRect(hx - 0.5, 0, 1, rect.height);
    }

    if (waveformProgress > 0) {
        ctx.fillStyle = accent;
        ctx.fillRect(playedX - 0.75, 0, 1.5, rect.height);
    }
}

async function loadWaveformForUrl(url, cacheKey) {
    activeWaveformKey = cacheKey;
    waveformProgress = 0;

    if (waveformCache.has(cacheKey)) {
        waveformRawPeaks = waveformCache.get(cacheKey);
        drawWaveform(0);
        return;
    }

    waveformRawPeaks = null;
    drawWaveform(0);

    try {
        const res = await fetch(url);
        if (!res.ok) return;
        const arrayBuf = await res.arrayBuffer();
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        if (!waveformAudioCtx) waveformAudioCtx = new AudioCtx();

        const audioBuf = await waveformAudioCtx.decodeAudioData(arrayBuf.slice(0));
        const channel = audioBuf.getChannelData(0);
        const samples = Math.min(RAW_PEAK_RESOLUTION, Math.max(256, channel.length));
        const blockSize = Math.max(1, Math.floor(channel.length / samples));
        const raw = new Float32Array(samples);
        let maxPeak = 0.001;

        for (let i = 0; i < samples; i++) {
            const start = i * blockSize;
            let sumSq = 0;
            for (let j = 0; j < blockSize; j++) {
                const v = channel[start + j] || 0;
                sumSq += v * v;
            }
            const rms = Math.sqrt(sumSq / blockSize);
            raw[i] = rms;
            if (rms > maxPeak) maxPeak = rms;
        }

        for (let i = 0; i < samples; i++) {
            raw[i] = Math.min(1, Math.max(0.08, raw[i] / maxPeak));
        }

        waveformCache.set(cacheKey, raw);
        if (activeWaveformKey === cacheKey) {
            waveformRawPeaks = raw;
            const pct = audio.duration ? (audio.currentTime / audio.duration) : 0;
            drawWaveform(pct);
        }
    } catch (_) {
        // Fallback placeholder bars remain visible
    }
}

function setupWaveformInteractions() {
    const scrubber = document.getElementById('player-progress-bar');
    if (!scrubber) return;

    let dragging = false;
    const seekFromEvent = (e) => {
        const rect = scrubber.getBoundingClientRect();
        const pct = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
        if (audio.duration) {
            audio.currentTime = pct * audio.duration;
            drawWaveform(pct);
        }
    };

    scrubber.addEventListener('mousedown', (e) => {
        dragging = true;
        seekFromEvent(e);
    });
    window.addEventListener('mousemove', (e) => {
        if (dragging) seekFromEvent(e);
    });
    window.addEventListener('mouseup', () => {
        dragging = false;
    });

    scrubber.addEventListener('mousemove', (e) => {
        const rect = scrubber.getBoundingClientRect();
        waveformHoverPct = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
        drawWaveform(waveformProgress);
    });
    scrubber.addEventListener('mouseleave', () => {
        waveformHoverPct = null;
        drawWaveform(waveformProgress);
    });

    if (typeof ResizeObserver !== 'undefined') {
        const ro = new ResizeObserver(() => drawWaveform(waveformProgress));
        ro.observe(scrubber);
    }
    window.addEventListener('resize', () => drawWaveform(waveformProgress));
    drawWaveform(0);
}
