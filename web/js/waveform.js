// Interactive HTML5 Canvas audio waveform decoder & renderer

const waveformCache = new Map();
let waveformPeaks = [];
let waveformProgress = 0;
let waveformHoverPct = null;
let waveformAudioCtx = null;
let activeWaveformKey = null;

function _defaultPlaceholderPeaks(count = 110) {
    const arr = [];
    for (let i = 0; i < count; i++) {
        arr.push(0.22 + 0.14 * Math.abs(Math.sin(i * 0.25)));
    }
    return arr;
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
    const muted = (styles.getPropertyValue('--waveform-muted') || 'rgba(148,163,184,0.28)').trim();

    const peaks = waveformPeaks.length > 0 ? waveformPeaks : _defaultPlaceholderPeaks();
    const barCount = peaks.length;
    const step = rect.width / barCount;
    const barWidth = Math.max(1.5, step * 0.65);
    const midY = rect.height / 2;
    const maxHalf = rect.height * 0.45;
    const playedX = waveformProgress * rect.width;

    for (let i = 0; i < barCount; i++) {
        const x = i * step + (step - barWidth) / 2;
        const amp = Math.max(0.1, peaks[i]);
        const halfH = amp * maxHalf;
        ctx.fillStyle = (x + barWidth / 2 <= playedX) ? accent : muted;
        ctx.fillRect(x, midY - halfH, barWidth, halfH * 2);
    }

    // Hover indicator
    if (waveformHoverPct !== null) {
        const hx = waveformHoverPct * rect.width;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
        ctx.fillRect(hx - 0.75, 0, 1.5, rect.height);
    }

    // Playhead cursor
    if (waveformProgress > 0) {
        ctx.fillStyle = accent;
        ctx.fillRect(playedX - 1, 0, 2, rect.height);
    }
}

async function loadWaveformForUrl(url, cacheKey) {
    activeWaveformKey = cacheKey;
    waveformProgress = 0;

    if (waveformCache.has(cacheKey)) {
        waveformPeaks = waveformCache.get(cacheKey);
        drawWaveform(0);
        return;
    }

    waveformPeaks = _defaultPlaceholderPeaks();
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
        const samples = 130;
        const blockSize = Math.max(1, Math.floor(channel.length / samples));
        const raw = [];
        let maxPeak = 0.001;

        for (let i = 0; i < samples; i++) {
            const start = i * blockSize;
            let sumSq = 0;
            for (let j = 0; j < blockSize; j++) {
                const v = channel[start + j] || 0;
                sumSq += v * v;
            }
            const rms = Math.sqrt(sumSq / blockSize);
            raw.push(rms);
            if (rms > maxPeak) maxPeak = rms;
        }

        const normalized = raw.map(v => Math.min(1, Math.max(0.08, v / maxPeak)));
        waveformCache.set(cacheKey, normalized);

        if (activeWaveformKey === cacheKey) {
            waveformPeaks = normalized;
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

    window.addEventListener('resize', () => drawWaveform(waveformProgress));
    drawWaveform(0);
}
