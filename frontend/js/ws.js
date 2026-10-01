let ws = null;
let reconnectTimer = null;
let currentSessionId = null;
let stateCallback = null;
let soundCallback = null;

export function connect(sessionId) {
    if (ws) ws.close();
    currentSessionId = sessionId;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    ws = new WebSocket(`${protocol}//${host}/ws/${sessionId}`);

    ws.onopen = () => {
        console.log('WS connected to session:', sessionId);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'STATE_UPDATE' && stateCallback) {
                stateCallback(data);
            } else if (data.type === 'PLAY_SOUND' && soundCallback) {
                soundCallback(data.sound);
            }
        } catch (e) {
            console.error('Error parsing WS message:', e);
        }
    };

    ws.onclose = () => {
        console.log('WS connection closed. Reconnecting in 2s...');
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => connect(currentSessionId), 2000);
    };

    ws.onerror = (error) => {
        console.error('WS error:', error);
    };
}

export function disconnect() {
    clearTimeout(reconnectTimer);
    if (ws) {
        ws.onclose = null;
        ws.close();
        ws = null;
    }
}

export function onStateUpdate(callback) {
    stateCallback = callback;
}

export function onSound(callback) {
    soundCallback = callback;
}

export function send(command) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(command));
    } else {
        console.warn('WebSocket not connected');
    }
}

export function isConnected() {
    return ws && ws.readyState === WebSocket.OPEN;
}

// Helper functions — match backend ws_manager.py command types exactly
export const setActivePlayer = (id) => send({ type: 'SET_ACTIVE_PLAYER', player_id: id });
export const setActiveWord = (id) => send({ type: 'SET_ACTIVE_WORD', word_id: id });
export const startTimer = () => send({ type: 'START_TIMER' });
export const pauseTimer = () => send({ type: 'PAUSE_TIMER' });
export const resetTimer = (duration) => send({ type: 'RESET_TIMER', duration });
export const updateTimer = (secondsRemaining) => send({ type: 'UPDATE_TIMER', seconds_remaining: secondsRemaining });
export const setTimerDuration = (duration) => send({ type: 'SET_TIMER_DURATION', duration });
export const markCorrect = () => send({ type: 'MARK_CORRECT' });
export const markIncorrect = () => send({ type: 'MARK_INCORRECT' });
export const markTimeout = () => send({ type: 'MARK_TIMEOUT' });
export const revealInfo = (type) => send({ type: 'REVEAL_INFO', info_type: type });
export const hideInfo = (type) => send({ type: 'HIDE_INFO', info_type: type });
export const clearDisplay = () => send({ type: 'CLEAR_DISPLAY' });
export const showScoreboard = () => send({ type: 'SHOW_SCOREBOARD' });
export const showPlayerIntro = () => send({ type: 'SHOW_PLAYER_INTRO' });
export const nextRound = () => send({ type: 'NEXT_ROUND' });
export const playSound = (sound) => send({ type: 'PLAY_SOUND', sound });
