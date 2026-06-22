/* ════════════════════════════════════════════════════════════
   KINDRED — Messages: matches list, chat, websocket
   ════════════════════════════════════════════════════════════ */

let currentChat = null;   // { id, other_profile, ... }
let chatSocket  = null;

// ── Avatar helper ──────────────────────────────────────────────
function avatarHtml(person) {
  const url = person?.primary_photo?.url;
  const initial = (person?.first_name || '?')[0].toUpperCase();
  return url ? `<img src="${url}" alt="${person.first_name}"/>` : initial;
}

// ── Load matches list ───────────────────────────────────────────
async function loadMatches() {
  showLoading(true);
  try {
    const matches = await Api.getMatches();
    renderMatches(matches);
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}

function renderMatches(matches) {
  const newRow  = document.getElementById('new-matches-row');
  const list    = document.getElementById('conv-list');
  const empty   = document.getElementById('matches-empty');
  newRow.innerHTML = '';
  list.innerHTML = '';

  if (matches.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  const fresh = matches.filter(m => !m.last_message_at);
  const active = matches.filter(m => m.last_message_at);

  fresh.forEach(m => {
    const el = document.createElement('div');
    el.className = 'new-match-item';
    el.innerHTML = `
      <div class="new-match-ring">
        ${m.other_profile.primary_photo?.url
          ? `<img src="${m.other_profile.primary_photo.url}" alt="${m.other_profile.first_name}"/>`
          : `<div class="ph">${m.other_profile.first_name[0].toUpperCase()}</div>`}
      </div>
      <div class="new-match-name">${m.other_profile.first_name}</div>`;
    el.addEventListener('click', () => openChat(m));
    newRow.appendChild(el);
  });

  active.sort((a, b) => new Date(b.last_message_at) - new Date(a.last_message_at));
  active.forEach(m => {
    const el = document.createElement('div');
    el.className = 'conv-item';
    el.innerHTML = `
      <div class="conv-avatar">${avatarHtml(m.other_profile)}</div>
      <div class="conv-info">
        <div class="conv-row">
          <span class="conv-name">${m.other_profile.first_name}</span>
          <span class="conv-time">${timeAgo(m.last_message_at)}</span>
        </div>
        <div class="conv-preview ${m.unread_count ? 'unread' : ''}">
          ${m.unread_count ? `${m.unread_count} new message${m.unread_count > 1 ? 's' : ''}` : 'Tap to open conversation'}
        </div>
      </div>
      ${m.unread_count ? `<div class="conv-unread-badge">${m.unread_count}</div>` : ''}`;
    el.addEventListener('click', () => openChat(m));
    list.appendChild(el);
  });
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

// ── Open chat (also called from discover.js after a match) ─────
async function openChatByMatch(match) { await openChat(match); }

async function openChat(match) {
  currentChat = match;
  const other = match.other_profile;

  document.getElementById('chat-avatar').innerHTML = avatarHtml(other);
  document.getElementById('chat-name').textContent = `${other.first_name}, ${other.age}`;
  document.getElementById('chat-status').textContent = 'Matched';
  document.getElementById('chat-input').value = '';
  document.getElementById('chat-limit-banner-wrap').innerHTML = '';
  setChatInputEnabled(true);

  go('chat');
  showLoading(true);

  try {
    const convo = await Api.getConversation(match.id);
    renderMessages(convo.messages);
    connectChatSocket(match.id);
  } catch (err) {
    if (err.status === 402) {
      renderMessages([]);
      showUpgradeLimitBanner(err.message);
      setChatInputEnabled(false);
    } else {
      showApiError(err);
    }
  } finally {
    showLoading(false);
  }
}

function showUpgradeLimitBanner(message) {
  document.getElementById('chat-limit-banner-wrap').innerHTML = `
    <div class="limit-banner">
      <span>${message || 'You\'ve reached the free message limit for this match.'}
      <a data-nav="subscription">Upgrade to Mellow</a> to keep chatting.</span>
    </div>`;
}

function setChatInputEnabled(enabled) {
  document.getElementById('chat-input').disabled = !enabled;
  document.getElementById('chat-send').disabled = !enabled;
}

// ── Render message bubbles ───────────────────────────────────────
function renderMessages(messages) {
  const container = document.getElementById('chat-messages');
  const empty = document.getElementById('chat-empty');
  container.innerHTML = '';

  if (!messages || messages.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  messages.forEach((m, i) => {
    appendBubble(m);
  });
  container.scrollTop = container.scrollHeight;
}

function appendBubble(m) {
  const container = document.getElementById('chat-messages');
  document.getElementById('chat-empty').hidden = true;
  const bubble = document.createElement('div');
  bubble.className = `bubble ${m.is_mine ? 'mine' : 'theirs'}`;
  bubble.textContent = m.content;
  container.appendChild(bubble);

  const meta = document.createElement('div');
  meta.className = `bubble-meta ${m.is_mine ? '' : 'left'}`;
  meta.textContent = formatTime(m.created_at);
  container.appendChild(meta);

  container.scrollTop = container.scrollHeight;
}

function formatTime(iso) {
  const d = new Date(iso);
  const h = d.getHours() % 12 || 12;
  const m = String(d.getMinutes()).padStart(2, '0');
  return `${h}:${m} ${d.getHours() >= 12 ? 'PM' : 'AM'}`;
}

// ── WebSocket ─────────────────────────────────────────────────────
function connectChatSocket(matchId) {
  if (chatSocket) { chatSocket.close(); chatSocket = null; }
  try {
    chatSocket = Api.connectChat(matchId);
  } catch (_) { return; }

  chatSocket.onmessage = (event) => {
    let data;
    try { data = JSON.parse(event.data); } catch (_) { return; }

    if (data.type === 'message') {
      // Avoid duplicating the optimistic bubble we already rendered
      if (data.is_mine && data._localEcho) return;
      appendBubble({ content: data.content, is_mine: data.is_mine, created_at: data.created_at });
    } else if (data.type === 'error') {
      showToast(data.message, true);
    }
  };
  chatSocket.onerror = () => { /* fall back to REST send */ };
  chatSocket.onclose = () => { chatSocket = null; };
}

// ── Send message ──────────────────────────────────────────────────
async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const content = input.value.trim();
  if (!content || !currentChat) return;
  input.value = '';

  // Optimistic render
  appendBubble({ content, is_mine: true, created_at: new Date().toISOString() });

  if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
    chatSocket.send(JSON.stringify({ type: 'message', content }));
  } else {
    try {
      await Api.sendMessage(currentChat.id, content);
    } catch (err) {
      if (err.status === 402) {
        showUpgradeLimitBanner(err.message);
        setChatInputEnabled(false);
      } else {
        showApiError(err);
      }
    }
  }
}
document.getElementById('chat-send').addEventListener('click', sendChatMessage);
document.getElementById('chat-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendChatMessage();
});

// Typing indicator (best-effort, ignored by backend if unused)
document.getElementById('chat-input').addEventListener('input', () => {
  if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
    chatSocket.send(JSON.stringify({ type: 'typing' }));
  }
});

// Close socket when leaving chat
document.querySelectorAll('#screen-chat [data-nav]').forEach(el => {
  el.addEventListener('click', () => {
    if (chatSocket) { chatSocket.close(); chatSocket = null; }
  });
});

// ── Report / Block ──────────────────────────────────────────────
let selectedReason = null;

document.getElementById('btn-chat-menu').addEventListener('click', () => {
  selectedReason = null;
  document.querySelectorAll('.reason-option').forEach(r => r.classList.remove('selected'));
  openSheet('sheet-report');
});
document.querySelectorAll('.reason-option').forEach(opt => {
  opt.addEventListener('click', () => {
    document.querySelectorAll('.reason-option').forEach(r => r.classList.remove('selected'));
    opt.classList.add('selected');
    selectedReason = opt.dataset.reason;
  });
});

// NOTE: Block/Report endpoints expect a User ID. The chat only has the
// other person's Profile ID — backend should expose a profile→user lookup,
// or accept profile_id directly. Using other_profile.id as a placeholder.
document.getElementById('btn-block-only').addEventListener('click', async () => {
  if (!currentChat) return;
  showLoading(true);
  try {
    await Api.blockUser(currentChat.other_profile.id);
    closeSheet('sheet-report');
    showToast(`${currentChat.other_profile.first_name} has been blocked`);
    go('matches');
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
});

document.getElementById('btn-submit-report').addEventListener('click', async () => {
  if (!selectedReason) { showToast('Please select a reason'); return; }
  if (!currentChat) return;
  showLoading(true);
  try {
    await Api.reportUser(currentChat.other_profile.id, selectedReason, null);
    await Api.blockUser(currentChat.other_profile.id);
    closeSheet('sheet-report');
    showToast('Report submitted — thank you for letting us know');
    go('matches');
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
});
