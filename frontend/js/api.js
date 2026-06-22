/* ════════════════════════════════════════════════════════════
   KINDRED — API Client
   ════════════════════════════════════════════════════════════ */

const API_BASE = (window.KINDRED_API_BASE || 'http://localhost:8000') + '/api/v1';
const WS_BASE  = (window.KINDRED_WS_BASE  || 'ws://localhost:8000');

const Tokens = {
  get access()  { return localStorage.getItem('mellow_access'); },
  get refresh() { return localStorage.getItem('mellow_refresh'); },
  set(access, refresh) {
    localStorage.setItem('mellow_access', access);
    if (refresh) localStorage.setItem('mellow_refresh', refresh);
  },
  clear() {
    localStorage.removeItem('mellow_access');
    localStorage.removeItem('mellow_refresh');
  },
  get loggedIn() { return !!this.access; }
};

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function apiRequest(path, { method = 'GET', body, isForm = false, retry = true } = {}) {
  const headers = {};
  if (!isForm) headers['Content-Type'] = 'application/json';
  if (Tokens.access) headers['Authorization'] = `Bearer ${Tokens.access}`;

  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: isForm ? body : (body ? JSON.stringify(body) : undefined),
  });

  // Handle expired access token — try refresh once
  if (res.status === 401 && retry && Tokens.refresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiRequest(path, { method, body, isForm, retry: false });
    Tokens.clear();
    throw new ApiError('Session expired', 401);
  }

  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }

  if (!res.ok) {
    const message = (data && data.detail) ? data.detail : `Request failed (${res.status})`;
    throw new ApiError(typeof message === 'string' ? message : 'Something went wrong', res.status, data);
  }
  return data;
}

async function refreshAccessToken() {
  try {
    const res = await fetch(API_BASE + '/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: Tokens.refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    Tokens.set(data.access_token, data.refresh_token);
    return true;
  } catch (_) { return false; }
}

const Api = {
  // ── Auth ─────────────────────────────────────────────
  register: (email, password, first_name) =>
    apiRequest('/auth/register', { method: 'POST', body: { email, password, first_name }, retry: false }),

  login: (email, password) =>
    apiRequest('/auth/login', { method: 'POST', body: { email, password }, retry: false }),

  googleAuth: (code) =>
    apiRequest('/auth/google', { method: 'POST', body: { code }, retry: false }),

  forgotPassword: (email) =>
    apiRequest('/auth/forgot-password', { method: 'POST', body: { email }, retry: false }),

  resetPassword: (token, new_password) =>
    apiRequest('/auth/reset-password', { method: 'POST', body: { token, new_password }, retry: false }),

  verifyEmail: (token) =>
    apiRequest('/auth/verify-email', { method: 'POST', body: { token }, retry: false }),

  me: () => apiRequest('/auth/me'),
  logout: () => apiRequest('/auth/logout', { method: 'POST' }).catch(() => {}),

  // ── Profile ──────────────────────────────────────────
  getMyProfile: () => apiRequest('/profiles/me'),
  createProfile: (data) => apiRequest('/profiles/me', { method: 'POST', body: data }),
  updateProfile: (data) => apiRequest('/profiles/me', { method: 'PUT', body: data }),
  deleteAccount: () => apiRequest('/profiles/me', { method: 'DELETE' }),
  getProfile: (id) => apiRequest(`/profiles/${id}`),
  setVisibility: (is_visible) => apiRequest('/profiles/me/visibility', { method: 'PUT', body: { is_visible } }),

  uploadPhoto: (file) => {
    const form = new FormData();
    form.append('file', file);
    return apiRequest('/profiles/photos', { method: 'POST', body: form, isForm: true });
  },
  deletePhoto: (id) => apiRequest(`/profiles/photos/${id}`, { method: 'DELETE' }),
  reorderPhotos: (photo_ids) => apiRequest('/profiles/photos/reorder', { method: 'PUT', body: { photo_ids } }),

  discoverFeed: (page = 1) => apiRequest(`/profiles/discover/feed?page=${page}&limit=10`),

  // ── Matches ──────────────────────────────────────────
  swipe: (profile_id, direction) =>
    apiRequest('/matches/swipe', { method: 'POST', body: { profile_id, direction } }),
  getMatches: () => apiRequest('/matches'),
  unmatch: (matchId) => apiRequest(`/matches/${matchId}`, { method: 'DELETE' }),

  // ── Messages ─────────────────────────────────────────
  getConversation: (matchId, page = 1) => apiRequest(`/messages/${matchId}?page=${page}&limit=50`),
  sendMessage: (matchId, content) =>
    apiRequest(`/messages/${matchId}`, { method: 'POST', body: { content, message_type: 'text' } }),

  // ── Subscriptions ────────────────────────────────────
  getPlans: () => apiRequest('/subscriptions/plans'),
  getMySubscription: () => apiRequest('/subscriptions/me'),
  createCheckout: (plan_id) => apiRequest(`/subscriptions/checkout?plan_id=${plan_id}`, { method: 'POST' }),

  // ── Safety ───────────────────────────────────────────
  reportUser: (reported_user_id, reason, description) =>
    apiRequest('/safety/report', { method: 'POST', body: { reported_user_id, reason, description } }),
  blockUser: (blocked_user_id) =>
    apiRequest('/safety/block', { method: 'POST', body: { blocked_user_id } }),
  unblockUser: (userId) => apiRequest(`/safety/block/${userId}`, { method: 'DELETE' }),

  // ── WebSocket ────────────────────────────────────────
  connectChat(matchId) {
    return new WebSocket(`${WS_BASE}/ws/chat/${matchId}?token=${Tokens.access}`);
  },
};
