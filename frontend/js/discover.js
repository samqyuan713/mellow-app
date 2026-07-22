/* ════════════════════════════════════════════════════════════
   KINDRED — Discover: swipe cards, Bloom indicator, filters
   ════════════════════════════════════════════════════════════ */

let feedQueue = [];
let feedPage = 1;
let feedLoading = false;
let dragState = null;

// ── Generic sheet helpers (reused by messages.js too) ─────────
function openSheet(id) { document.getElementById(id).classList.add('show'); }
function closeSheet(id) { document.getElementById(id).classList.remove('show'); }
document.querySelectorAll('.sheet-overlay').forEach(ov => {
  ov.addEventListener('click', (e) => { if (e.target === ov) ov.classList.remove('show'); });
});

// ── Mellow Bloom SVG ──────────────────────────────────────────
function renderBloom(score) {
  const s = Math.max(0, Math.min(100, score ?? 0));
  const filled = Math.round((s / 100) * 8);
  let petals = '';
  for (let i = 0; i < 8; i++) {
    const isFilled = i < filled;
    petals += `<ellipse class="bloom-petal" cx="50" cy="26" rx="7" ry="15"
      fill="${isFilled ? 'var(--rose)' : 'transparent'}"
      stroke="${isFilled ? 'var(--rose)' : 'var(--line-strong)'}"
      stroke-width="1.5" opacity="${isFilled ? 0.92 : 1}"
      transform="rotate(${i * 45} 50 50)"/>`;
  }
  return `
    <svg viewBox="0 0 100 100">
      ${petals}
      <circle cx="50" cy="50" r="17" fill="var(--cream)"/>
    </svg>
    <div class="bloom-center">
      <div class="bloom-score">${s}%</div>
      <div class="bloom-label">match</div>
    </div>`;
}

// ── Render a single card ───────────────────────────────────────
function renderCard(profile, position) {
  const card = document.createElement('div');
  card.className = `discover-card ${position}`;
  card.dataset.id = profile.id;

  const photos = profile.photos || [];
  const photoUrl = photos[0]?.url;
  const initial = (profile.first_name || '?')[0].toUpperCase();

  card.innerHTML = `
    <div class="card-photo" data-photo-idx="0">
      ${photoUrl ? `<img src="${photoUrl}" alt="${profile.first_name}"/>` : `<div class="no-photo">${initial}</div>`}
      ${photos.length > 1 ? `<div class="card-gallery-dots">${photos.map((_, i) => `<div class="dot ${i === 0 ? 'active' : ''}"></div>`).join('')}</div>` : ''}
      <div class="bloom">${renderBloom(profile.compatibility_score)}</div>
      <div class="card-like-stamp">Yes</div>
      <div class="card-pass-stamp">Pass</div>
    </div>
    <div class="card-body">
      <div class="card-name-row">
        <span class="card-name">${profile.first_name}<span class="age">, ${profile.age}</span></span>
      </div>
      <div class="card-meta">
        ${profile.occupation ? `<span>${profile.occupation}</span>` : ''}
        ${profile.occupation && profile.location_city ? '<span class="dot-sep">·</span>' : ''}
        ${profile.location_city ? `<span>${profile.location_city}</span>` : ''}
        ${profile.marital_history ? `<span class="dot-sep">·</span><span>${capitalize(profile.marital_history)}</span>` : ''}
      </div>
      ${profile.bio ? `<p class="card-bio">${escapeHtml(profile.bio)}</p>` : ''}
      ${profile.interests?.length ? `<div class="card-tags">${profile.interests.slice(0, 4).map(t => `<span class="tag">${capitalize(t)}</span>`).join('')}</div>` : ''}
    </div>`;

  // Photo gallery tap zones
  if (photos.length > 1) {
    const photoEl = card.querySelector('.card-photo');
    photoEl.addEventListener('click', (e) => {
      const rect = photoEl.getBoundingClientRect();
      const x = e.clientX - rect.left;
      let idx = parseInt(photoEl.dataset.photoIdx);
      idx = x < rect.width / 2 ? Math.max(0, idx - 1) : Math.min(photos.length - 1, idx + 1);
      photoEl.dataset.photoIdx = idx;
      photoEl.querySelector('img').src = photos[idx].url;
      photoEl.querySelectorAll('.dot').forEach((d, i) => d.classList.toggle('active', i === idx));
    });
  }

    // Add tap on card body to open full profile
    const cardBody = card.querySelector('.card-body');
    if (cardBody) {
      cardBody.addEventListener('click', (e) => {
        e.stopPropagation();
        if (typeof openProfileDetail === 'function') {
          openProfileDetail(profile.id, false);
        }
      });
    }

  return card;
}

function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' ') : ''; }
function escapeHtml(s) {
  const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
}

// ── Render the stack (front + back) ────────────────────────────
function renderStack() {
  const stack = document.getElementById('card-stack');
  stack.querySelectorAll('.discover-card').forEach(c => c.remove());
  const empty = document.getElementById('discover-empty');

  if (feedQueue.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;

  if (feedQueue[1]) stack.appendChild(renderCard(feedQueue[1], 'back'));
  const front = renderCard(feedQueue[0], 'front');
  stack.appendChild(front);
  attachDrag(front);

  // Pre-fetch more when running low
  if (feedQueue.length <= 2 && !feedLoading) fetchMoreProfiles();
}

// ── Load feed ──────────────────────────────────────────────────
async function loadDiscoverFeed() {
  if (feedQueue.length > 0) { renderStack(); return; }
  feedPage = 1;
  showLoading(true);
  try {
    feedQueue = await Api.discoverFeed(feedPage);
  } catch (err) {
    if (err.status === 402) {
      showSwipeLimitEmpty(err.message);
    } else if (err.status === 400) {
      showToast(err.message, true);
    } else {
      showApiError(err);
    }
    feedQueue = [];
  } finally {
    showLoading(false);
    renderStack();
  }
}

async function fetchMoreProfiles() {
  feedLoading = true;
  try {
    feedPage += 1;
    const more = await Api.discoverFeed(feedPage);
    feedQueue.push(...more);
    if (feedQueue.length <= 2) renderStack();
  } catch (_) { /* silently stop prefetching */ }
  finally { feedLoading = false; }
}

function showSwipeLimitEmpty(message) {
  const empty = document.getElementById('discover-empty');
  empty.innerHTML = `
    <div class="emoji">✨</div>
    <div class="display">You've used today's swipes</div>
    <p class="body-text">${message || 'Upgrade to Mellow for unlimited swiping every day.'}</p>
    <button class="btn btn-rose" data-nav="subscription">View plans</button>`;
  empty.hidden = false;
}

// ── Drag / swipe gestures ───────────────────────────────────────
function attachDrag(card) {
  const likeStamp = card.querySelector('.card-like-stamp');
  const passStamp = card.querySelector('.card-pass-stamp');

  const onStart = (x, y) => { dragState = { startX: x, startY: y, card }; card.classList.add('swiping'); };
  const onMove = (x, y) => {
    if (!dragState) return;
    const dx = x - dragState.startX, dy = y - dragState.startY;
    card.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx * 0.06}deg)`;
    const ratio = Math.min(Math.abs(dx) / 100, 1);
    likeStamp.style.opacity = dx > 0 ? ratio : 0;
    passStamp.style.opacity = dx < 0 ? ratio : 0;
  };
  const onEnd = (x) => {
    if (!dragState) return;
    const dx = x - dragState.startX;
    card.classList.remove('swiping');
    if (dx > 90) { handleSwipe('like'); }
    else if (dx < -90) { handleSwipe('pass'); }
    else {
      card.style.transform = '';
      likeStamp.style.opacity = 0;
      passStamp.style.opacity = 0;
    }
    dragState = null;
  };

  card.addEventListener('mousedown', e => onStart(e.clientX, e.clientY));
  document.addEventListener('mousemove', e => onMove(e.clientX, e.clientY));
  document.addEventListener('mouseup', e => onEnd(e.clientX));
  card.addEventListener('touchstart', e => onStart(e.touches[0].clientX, e.touches[0].clientY), { passive: true });
  card.addEventListener('touchmove', e => onMove(e.touches[0].clientX, e.touches[0].clientY), { passive: true });
  card.addEventListener('touchend', e => onEnd(e.changedTouches[0].clientX));
}

// ── Swipe action ────────────────────────────────────────────────
let lastSwiped = null;

async function handleSwipe(direction) {
  if (feedQueue.length === 0) return;
  const profile = feedQueue[0];
  const front = document.querySelector('.discover-card.front');
  if (front) {
    front.classList.add(direction === 'pass' ? 'fly-left' : 'fly-right');
  }

  try {
    const res = await Api.swipe(profile.id, direction);
    lastSwiped = profile;
    feedQueue.shift();

    if (res.matched) {
      setTimeout(() => showMatchOverlay(profile, res.match_id), 380);
    }
  } catch (err) {
    if (err.status === 402) {
      showSwipeLimitEmpty(err.message);
    } else if (err.status === 409) {
      feedQueue.shift(); // already swiped — just move on
    } else {
      showApiError(err);
      if (front) { front.classList.remove('fly-left', 'fly-right'); front.style.transform = ''; }
      return;
    }
  }

  setTimeout(() => renderStack(), 380);
}

document.getElementById('btn-like').addEventListener('click', () => handleSwipe('like'));
document.getElementById('btn-pass').addEventListener('click', () => handleSwipe('pass'));
document.getElementById('btn-superlike').addEventListener('click', () => handleSwipe('superlike'));
document.getElementById('btn-rewind').addEventListener('click', () => {
  showToast('Rewind is a Mellow Plus feature');
});

// ── Match overlay ───────────────────────────────────────────────
let pendingMatch = null;

function showMatchOverlay(profile, matchId) {
  pendingMatch = { matchId, profile };
  document.getElementById('match-text').textContent =
    `You and ${profile.first_name} both said yes.`;

  const meAv = document.getElementById('match-av-me');
  const themAv = document.getElementById('match-av-them');
  const myPhoto = State.profile?.photos?.[0]?.url;
  meAv.innerHTML = myPhoto ? `<img src="${myPhoto}" alt="You"/>` : '';
  themAv.innerHTML = profile.photos?.[0]?.url ? `<img src="${profile.photos[0].url}" alt="${profile.first_name}"/>` : '';

  document.getElementById('match-overlay').classList.add('show');
}
document.getElementById('match-keep-going').addEventListener('click', () => {
  document.getElementById('match-overlay').classList.remove('show');
});
document.getElementById('match-send-msg').addEventListener('click', () => {
  document.getElementById('match-overlay').classList.remove('show');
  if (pendingMatch && typeof openChatByMatch === 'function') {
    openChatByMatch({
      id: pendingMatch.matchId,
      other_profile: {
        id: pendingMatch.profile.id,
        first_name: pendingMatch.profile.first_name,
        age: pendingMatch.profile.age,
        primary_photo: pendingMatch.profile.photos?.[0] || null,
      },
    });
  } else {
    go('matches');
  }
});

// ── Filters sheet ───────────────────────────────────────────────
const ageMin = document.getElementById('filter-age-min');
const ageMax = document.getElementById('filter-age-max');
const distSlider = document.getElementById('filter-distance');

ageMin.addEventListener('input', () => {
  document.getElementById('filter-age-min-val').textContent = ageMin.value;
});
ageMax.addEventListener('input', () => {
  document.getElementById('filter-age-max-val').textContent = ageMax.value;
});
distSlider.addEventListener('input', () => {
  document.getElementById('filter-distance-val').textContent = `${distSlider.value} km`;
});

function openFiltersSheet() {
  // Load from State.profile if available
  const minAge = State.profile?.pref_age_min || 35;
  const maxAge = State.profile?.pref_age_max || 65;
  const dist   = State.profile?.pref_distance_km || 50;

  ageMin.value  = minAge;
  ageMax.value  = maxAge;
  distSlider.value = dist;

  document.getElementById('filter-age-min-val').textContent  = minAge;
  document.getElementById('filter-age-max-val').textContent  = maxAge;
  document.getElementById('filter-distance-val').textContent = `${dist} km`;

  openSheet('sheet-filters');
}
document.getElementById('btn-filters').addEventListener('click', openFiltersSheet);
document.getElementById('empty-adjust-filters').addEventListener('click', openFiltersSheet);

document.getElementById('filter-apply').addEventListener('click', async () => {
  const minV = parseInt(ageMin.value);
  const maxV = parseInt(ageMax.value);
  const dist = parseInt(distSlider.value);

  if (minV > maxV) { 
    showToast('Minimum age should be less than maximum'); 
    return; 
  }

  showLoading(true);
  try {
    // Save to State immediately for UI consistency
    if (State.profile) {
      State.profile.pref_age_min = minV;
      State.profile.pref_age_max = maxV;
      State.profile.pref_distance_km = dist;
    }

    // Save to backend
    await Api.updateProfile({
      pref_age_min: minV,
      pref_age_max: maxV,
      pref_distance_km: dist,
    });

    closeSheet('sheet-filters');
    feedQueue = [];
    feedPage = 1;
    await loadDiscoverFeed();
    showToast('Preferences updated');
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
});

async function handleSwipeById(profileId, direction) {
  try {
    const res = await Api.swipe(profileId, direction);
    if (res.matched) {
      showMatchOverlay({ id: profileId, first_name: 'them', photos: [] }, res.match_id);
    }
    showToast(direction === 'like' ? '💜 Liked!' : 'Passed');
    // Reload matches to reflect new match
    if (res.matched) go('matches');
  } catch (err) {
    showApiError(err);
  }
}


