// TV sound effects.
//
// Every sound is synthesized once, at page load, into a short WAV clip (OfflineAudioContext needs
// no user gesture) and played through an <audio> element. Media elements are more reliable than a
// live AudioContext: Safari's auto-play settings and the iPhone/iPad silent switch can leave a live
// AudioContext silent even after a click, while unlocked <audio> elements still play (like speech).
// initAudio(), called from a click, unlocks every clip; a live AudioContext is kept as a fallback.

const SAMPLE_RATE = 44100;
const MAX_BEEPS = 10;

// --- Sound designs: draw(ctx, t) schedules the sound on any (live or offline) audio context ---

function bell(ctx, t) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, t);
    osc.frequency.exponentialRampToValueAtTime(300, t + 1.5);
    gain.gain.setValueAtTime(1, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 1.5);
    osc.start(t); osc.stop(t + 1.5);
}

function correct(ctx, t) {
    const note = (freq, start, duration) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = 'triangle';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(0.5, start + 0.05);
        gain.gain.exponentialRampToValueAtTime(0.01, start + duration);
        osc.start(start); osc.stop(start + duration);
    };
    note(523.25, t, 0.4);         // C5
    note(659.25, t + 0.15, 0.6);  // E5
}

function tick(ctx, t) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = 'square';
    osc.frequency.setValueAtTime(1000, t);
    osc.frequency.exponentialRampToValueAtTime(100, t + 0.02);
    gain.gain.setValueAtTime(0.3, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.02);
    osc.start(t); osc.stop(t + 0.02);
}

function countdown(ctx, t) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(400, t);
    osc.frequency.exponentialRampToValueAtTime(100, t + 0.05);
    gain.gain.setValueAtTime(0.5, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);
    osc.start(t); osc.stop(t + 0.05);
}

// `count` short, clear beeps (time-left markers: one beep per 30 seconds remaining)
function beeps(count) {
    return (ctx, t) => {
        for (let i = 0; i < count; i++) {
            const start = t + i * 0.35;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, start);
            gain.gain.setValueAtTime(0, start);
            gain.gain.linearRampToValueAtTime(0.6, start + 0.01);
            gain.gain.setValueAtTime(0.6, start + 0.15);
            gain.gain.exponentialRampToValueAtTime(0.01, start + 0.2);
            osc.start(start); osc.stop(start + 0.21);
        }
    };
}

// name -> [draw, seconds]
const SOUNDS = { bell: [bell, 1.6], correct: [correct, 0.8], tick: [tick, 0.05], countdown: [countdown, 0.08] };
for (let n = 1; n <= MAX_BEEPS; n++) SOUNDS[`beeps${n}`] = [beeps(n), n * 0.35 + 0.1];

// --- Pre-rendered clips ---

const clips = {};        // name -> HTMLAudioElement
let mediaUnlocked = false;
let audioCtx = null;     // live fallback

function toWav(buffer) {
    const data = buffer.getChannelData(0);
    const view = new DataView(new ArrayBuffer(44 + data.length * 2));
    const str = (o, s) => [...s].forEach((c, i) => view.setUint8(o + i, c.charCodeAt(0)));
    str(0, 'RIFF'); view.setUint32(4, 36 + data.length * 2, true); str(8, 'WAVE');
    str(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, buffer.sampleRate, true); view.setUint32(28, buffer.sampleRate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    str(36, 'data'); view.setUint32(40, data.length * 2, true);
    data.forEach((v, i) => view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, v)) * 0x7fff, true));
    return new Blob([view], { type: 'audio/wav' });
}

const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext;
const clipsReady = Promise.all(Object.entries(SOUNDS).map(async ([name, [draw, seconds]]) => {
    if (!Offline) return;
    const ctx = new Offline(1, Math.ceil(seconds * SAMPLE_RATE), SAMPLE_RATE);
    draw(ctx, 0);
    const audio = new Audio(URL.createObjectURL(toWav(await ctx.startRendering())));
    audio.preload = 'auto';
    clips[name] = audio;
})).catch(e => console.warn('Could not pre-render sounds:', e));

function play(name) {
    const clip = clips[name];
    if (clip && mediaUnlocked) {
        clip.currentTime = 0;
        clip.play().catch(() => playLive(name));
    } else {
        playLive(name);
    }
}

function playLive(name) {
    if (audioCtx && audioCtx.state === 'running') SOUNDS[name][0](audioCtx, audioCtx.currentTime);
}

// Must be called from a click/tap: browsers keep audio blocked until the user interacts with the page.
// Returns a promise that settles once the clips are unlocked (or have failed to).
export function initAudio() {
    // Safari 17+: play like media, so the iPhone/iPad silent switch doesn't mute effects
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) {}

    // Unlock every clip by starting it (muted) inside this gesture
    const unlocks = Object.values(clips).map(clip => {
        clip.muted = true;
        return clip.play().then(() => {
            clip.pause();
            clip.currentTime = 0;
            clip.muted = false;
            mediaUnlocked = true;
        }).catch(() => { clip.muted = false; });
    });

    // Live fallback
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state !== 'running') audioCtx.resume();
        const src = audioCtx.createBufferSource(); // iOS needs a sound started inside the gesture
        src.buffer = audioCtx.createBuffer(1, 1, 22050);
        src.connect(audioCtx.destination);
        src.start(0);
    } catch (e) {}
    return Promise.allSettled(unlocks);
}

// 'running' when sound can play; anything else means the browser is still blocking it
export function audioState() {
    if (mediaUnlocked) return 'running';
    return audioCtx ? audioCtx.state : 'not-started';
}

export const whenReady = () => clipsReady;
export const playBell = () => play('bell');
export const playCorrect = () => play('correct');
export const playTick = () => play('tick');
export const playCountdown = () => play('countdown');
export const playBeeps = (count) => { if (count >= 1) play(`beeps${Math.min(Math.round(count), MAX_BEEPS)}`); };
