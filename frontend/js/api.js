const API_BASE = '/api';

async function request(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (e) {
        console.error('API Error:', e);
        throw e;
    }
}

const jsonHeaders = { 'Content-Type': 'application/json' };

// Sessions
export async function fetchSessions() { return request('/sessions/'); }
export async function createSession(data) { return request('/sessions/', { method: 'POST', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function getSession(id) { return request(`/sessions/${id}`); }
export async function updateSession(id, data) { return request(`/sessions/${id}`, { method: 'PATCH', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function deleteSession(id) { return request(`/sessions/${id}`, { method: 'DELETE' }); }
export async function resetSession(id) { return request(`/sessions/${id}/reset`, { method: 'POST' }); }

// Players
export async function fetchPlayers(sessionId) { return request(`/sessions/${sessionId}/players/`); }
export async function createPlayer(sessionId, data) { return request(`/sessions/${sessionId}/players/`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function updatePlayer(sessionId, playerId, data) { return request(`/sessions/${sessionId}/players/${playerId}`, { method: 'PATCH', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function deletePlayer(sessionId, playerId) { return request(`/sessions/${sessionId}/players/${playerId}`, { method: 'DELETE' }); }
export async function reorderPlayers(sessionId, playerIds) { return request(`/sessions/${sessionId}/players/reorder`, { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(playerIds) }); }

// Words
export async function fetchWords(sessionId, params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/sessions/${sessionId}/words/${query ? '?' + query : ''}`);
}
export async function createWord(sessionId, data) { return request(`/sessions/${sessionId}/words/`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function bulkImportWords(sessionId, words) { return request(`/sessions/${sessionId}/words/bulk`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(words) }); }
export async function updateWord(sessionId, wordId, data) { return request(`/sessions/${sessionId}/words/${wordId}`, { method: 'PATCH', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function deleteWord(sessionId, wordId) { return request(`/sessions/${sessionId}/words/${wordId}`, { method: 'DELETE' }); }

// Teams
export async function fetchTeams(sessionId) { return request(`/sessions/${sessionId}/teams/`); }
export async function createTeam(sessionId, data) { return request(`/sessions/${sessionId}/teams/`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function updateTeam(sessionId, teamId, data) { return request(`/sessions/${sessionId}/teams/${teamId}`, { method: 'PATCH', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function deleteTeam(sessionId, teamId) { return request(`/sessions/${sessionId}/teams/${teamId}`, { method: 'DELETE' }); }

// Roster (whole-session import/export, used for AI round-trips)
export async function exportSession(sessionId) { return request(`/sessions/${sessionId}/export`); }
export async function importSession(sessionId, data) { return request(`/sessions/${sessionId}/import`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(data) }); }
export async function recordTurn(sessionId, data) { return request(`/sessions/${sessionId}/turns/`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(data) }); }

// Turns
export async function fetchTurns(sessionId, params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/sessions/${sessionId}/turns/${query ? '?' + query : ''}`);
}
export async function fetchScoreboard(sessionId) { return request(`/sessions/${sessionId}/turns/scoreboard`); }
