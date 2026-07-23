/* ════════════════════════════════════════════════════════════
   KINDRED — Messages: matches list, chat, websocket
   ════════════════════════════════════════════════════════════ */

let currentChat = null;   // { id, other_profile, ... }
let chatSocket  = null;

// ── Avatar helper ──────────────────────────────────────────────
function avatarHtml(person) {
  // Handle both profile object (has photos array) and match object (has primary_photo)
  const url = person?.primary_photo?.url ||
              person?.photos?.find(p => p.is_primary)?.url ||
              person?.photos?.[0]?.url;
  const initial = (person?.first_name || '?')[0].toUpperCase();
  return url
    ? `<img src="${url}" alt="${person.first_name}" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;"/>`
    : initial;
}

// ── Load matches list ───────────────────────────────────────────
async function loadMatches() {
  showLoading(true);
  try {
    const [matches] = await Promise.all([
      Api.getMatches(),
      loadWhoLikedMe()   // ← add this
    ]);
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

async function loadWhoLikedMe() {
  try {
    const likers = await Api.getLikedMe();
    if (!Array.isArray(likers)) {
      console.warn('liked-me response is not array:', likers);
      return;
    }

    const section = document.getElementById('who-liked-section');
    const row = document.getElementById('who-liked-row');
    const count = document.getElementById('liked-count');

    if (!likers || likers.length === 0) {
      section.hidden = true;
      return;
    }

    section.hidden = false;
    count.textContent = `${likers.length} people`;
    row.innerHTML = '';

    likers.forEach(p => {
      const el = document.createElement('div');
      el.className = 'new-match-item';
      const photoUrl = p.photos?.[0]?.url;
      el.innerHTML = `
        <div class="new-match-ring" style="position:relative">
          ${photoUrl
            ? `<img src="${photoUrl}" alt="${p.first_name}"/>`
            : `<div class="ph">${p.first_name[0].toUpperCase()}</div>`}
          ${p.swiped_direction === 'superlike'
            ? '<div style="position:absolute;bottom:0;right:0;font-size:12px">⭐</div>'
            : ''}
        </div>
        <div class="new-match-name">${p.first_name}, ${p.age}</div>`;

      // ← Add click handler to open full profile
      el.addEventListener('click', () => openProfileDetail(p.id, true));
      row.appendChild(el);
    });

  } catch (err) {
    console.warn('Could not load who liked me:', err);
  }
}

async function openProfileDetail(profileId, showActions = false, matchId = null) {
  showLoading(true);
  try {
    const response = await fetch(
      `${window.KINDRED_API_BASE}/api/v1/profiles/${profileId}`,
      { headers: { 'Authorization': `Bearer ${Tokens.access}` } }
    );
    const profile = await response.json();

    const content = document.getElementById('profile-detail-content');
    const actions = document.getElementById('profile-detail-actions');

    const photos = profile.photos || [];
    const photoUrl = photos[0]?.url;
    const initial = (profile.first_name || '?')[0].toUpperCase();

    content.innerHTML = `
      <div style="width:100%;height:240px;border-radius:16px;overflow:hidden;
                  background:var(--cream-deep);margin-bottom:16px;position:relative">
        ${photoUrl
          ? `<img src="${photoUrl}" style="width:100%;height:100%;object-fit:cover"/>`
          : `<div style="width:100%;height:100%;display:flex;align-items:center;
                         justify-content:center;font-family:'Fraunces',serif;
                         font-size:64px;color:var(--rose-light);background:var(--plum)">
               ${initial}
             </div>`}
        ${photos.length > 1 ? `
          <div style="position:absolute;bottom:10px;left:50%;transform:translateX(-50%);
                      display:flex;gap:5px">
            ${photos.map((_, i) => `
              <div style="width:6px;height:6px;border-radius:50%;
                          background:${i===0?'#fff':'rgba(255,255,255,.5)'}"></div>
            `).join('')}
          </div>` : ''}
      </div>
      <div style="font-family:'Fraunces',serif;font-size:24px;color:var(--plum);margin-bottom:4px">
        ${profile.first_name}, ${profile.age}
      </div>
      <div style="font-size:13px;color:var(--ink-soft);margin-bottom:12px">
        ${[profile.occupation, profile.location_city].filter(Boolean).join(' · ')}
      </div>
      ${profile.bio ? `
        <p style="font-size:14px;color:var(--ink-soft);line-height:1.6;margin-bottom:14px">
          ${profile.bio}
        </p>` : ''}
      ${profile.relationship_goal ? `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:12px;font-weight:600;color:var(--plum)">Looking for:</span>
          <span style="font-size:12px;color:var(--ink-soft)">${profile.relationship_goal}</span>
        </div>` : ''}
      ${profile.marital_history ? `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <span style="font-size:12px;font-weight:600;color:var(--plum)">History:</span>
          <span style="font-size:12px;color:var(--ink-soft)">${profile.marital_history}</span>
        </div>` : ''}
      ${profile.interests?.length ? `
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:12px">
          ${profile.interests.map(i => `
            <span style="font-size:11px;padding:4px 10px;border-radius:20px;
                         background:var(--cream-deep);color:var(--ink-soft)">
              ${i}
            </span>`).join('')}
        </div>` : ''}
    `;

    // Action buttons
    actions.innerHTML = '';
    if (showActions && !matchId) {
      // Like button for "who liked me" profiles
      actions.innerHTML = `
        <button class="btn btn-outline" style="flex:1"
          onclick="closeSheet('sheet-profile-detail');handleSwipeById('${profileId}','pass')">
          Pass
        </button>
        <button class="btn btn-rose" style="flex:1"
          onclick="closeSheet('sheet-profile-detail');handleSwipeById('${profileId}','like')">
          💜 Like back
        </button>`;
    } else if (matchId) {
      actions.innerHTML = `
        <button class="btn btn-primary" style="flex:1"
          onclick="closeSheet('sheet-profile-detail')">
          Close
        </button>`;
    }

    openSheet('sheet-profile-detail');
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}



