/* ════════════════════════════════════════════════════════════
   KINDRED — App Core: navigation, auth, onboarding
   ════════════════════════════════════════════════════════════ */

const State = {
  user: null,
  profile: null,
  subscription: null,
  history: [],
};

// ── Navigation ──────────────────────────────────────────────
function go(name, opts = {}) {
  const target = document.getElementById('screen-' + name);
  if (!target) return;
  const current = document.querySelector('.screen.active');
  if (current && current !== target && !opts.skipHistory) {
    State.history.push(current.id.replace('screen-', ''));
  }
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  target.classList.add('active');

  // Lazy-load screen data
  const loaders = {
    discover: () => typeof loadDiscoverFeed === 'function' && loadDiscoverFeed(),
    matches:  () => typeof loadMatches === 'function' && loadMatches(),
    profile:  () => typeof loadProfileScreen === 'function' && loadProfileScreen(),
    'profile-edit': () => typeof loadProfileEditScreen === 'function' && loadProfileEditScreen(),
    subscription:   () => typeof loadSubscriptionScreen === 'function' && loadSubscriptionScreen(),
  };
  if (loaders[name]) loaders[name]();
}

// ── Toast & Loading ─────────────────────────────────────────
let toastTimer;
function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.toggle('error', isError);
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
}
function showLoading(on) {
  document.getElementById('loading-overlay').classList.toggle('show', on);
}
function showApiError(err) {
  showToast(err.message || 'Something went wrong. Please try again.', true);
}

// ── Clock ───────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  const t = `${now.getHours() % 12 || 12}:${String(now.getMinutes()).padStart(2, '0')}`;
  document.querySelectorAll('[id^="clock-"]').forEach(el => el.textContent = t);
}
tickClock();
setInterval(tickClock, 30000);

// ── Generic click delegation for data-nav ─────────────────────
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-nav]');
  if (el) go(el.dataset.nav);
});

// ── Field error helper ──────────────────────────────────────
function setFieldError(input, hasError) {
  input.closest('.field').classList.toggle('has-error', hasError);
}

// ════════════════════════════════════════════════════════════
// CHIP GROUPS  (single / multi select)
// ════════════════════════════════════════════════════════════
const ChipState = {};

function initChipGroups(root = document) {
  root.querySelectorAll('[data-chips]').forEach(group => {
    const key  = group.dataset.chips;
    const mode = group.dataset.mode;
    const max  = parseInt(group.dataset.max || '0');
    if (!(key in ChipState)) ChipState[key] = mode === 'multi' ? [] : null;

    group.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const val = chip.dataset.value;
        if (mode === 'single') {
          group.querySelectorAll('.chip').forEach(c => c.classList.remove('selected'));
          chip.classList.add('selected');
          ChipState[key] = val;
        } else {
          const arr = ChipState[key];
          const idx = arr.indexOf(val);
          if (idx > -1) {
            arr.splice(idx, 1);
            chip.classList.remove('selected');
          } else {
            if (max && arr.length >= max) {
              showToast(`You can select up to ${max}`);
              return;
            }
            arr.push(val);
            chip.classList.add('selected');
          }
          updateInterestCounters(key, arr.length, max);
        }
      });
    });
  });
}
function updateInterestCounters(key, count, max) {
  const el1 = document.getElementById('interest-count');
  const el2 = document.getElementById('edit-interest-count');
  if (key === 'interests' && el1) el1.textContent = count;
  if (key === 'edit-interests' && el2) el2.textContent = count;
}
function setChipSelection(key, values) {
  const group = document.querySelector(`[data-chips="${key}"]`);
  if (!group) return;
  const arr = Array.isArray(values) ? values : (values ? [values] : []);
  ChipState[key] = group.dataset.mode === 'multi' ? [...arr] : (arr[0] || null);
  group.querySelectorAll('.chip').forEach(chip => {
    chip.classList.toggle('selected', arr.includes(chip.dataset.value));
  });
  updateInterestCounters(key, arr.length, parseInt(group.dataset.max || '0'));
}

// ════════════════════════════════════════════════════════════
// OPTION CARDS (onboarding step 2)
// ════════════════════════════════════════════════════════════
// const OnboardData = { gender: null, seeking: null, marital_history: null, has_children: null, relationship_goal: null };

function initOptionCards(root = document) {
  root.querySelectorAll('.option-card').forEach(card => {
    card.addEventListener('click', () => {
      const group = card.dataset.group;
      // Deselect all in same group
      root.querySelectorAll(`.option-card[data-group="${group}"]`)
        .forEach(c => c.classList.remove('selected'));
      // Select clicked card
      card.classList.add('selected');
      // Store in ChipState instead of OnboardData
      ChipState[group] = card.dataset.value;
    });
  });
}

// ════════════════════════════════════════════════════════════
// AUTH — Login
// ════════════════════════════════════════════════════════════
document.getElementById('form-login').addEventListener('submit', async (e) => {
  e.preventDefault();
  const emailEl = document.getElementById('login-email');
  const passEl  = document.getElementById('login-password');
  setFieldError(emailEl, false);
  setFieldError(passEl, false);

  showLoading(true);
  try {
    const data = await Api.login(emailEl.value.trim(), passEl.value);
    Tokens.set(data.tokens.access_token, data.tokens.refresh_token);
    State.user = data.user;
    showToast(`Welcome back, ${data.user.email.split('@')[0]}!`);
    await routeAfterAuth();
  } catch (err) {
    if (err.status === 401) {
      setFieldError(emailEl, true);
      setFieldError(passEl, true);
    } else {
      showApiError(err);
    }
  } finally {
    showLoading(false);
  }
});

// ════════════════════════════════════════════════════════════
// AUTH — Register
// ════════════════════════════════════════════════════════════
document.getElementById('form-register').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameEl  = document.getElementById('reg-name');
  const emailEl = document.getElementById('reg-email');
  const passEl  = document.getElementById('reg-password');

  let valid = true;
  if (nameEl.value.trim().length < 2) { setFieldError(nameEl, true); valid = false; } else setFieldError(nameEl, false);
  if (!/^\S+@\S+\.\S+$/.test(emailEl.value)) { setFieldError(emailEl, true); valid = false; } else setFieldError(emailEl, false);
  const pw = passEl.value;
  const pwOk = pw.length >= 8 && /[A-Z]/.test(pw) && /[0-9]/.test(pw);
  if (!pwOk) { setFieldError(passEl, true); valid = false; } else setFieldError(passEl, false);
  if (!valid) return;

  showLoading(true);
  try {
    const data = await Api.register(emailEl.value.trim(), pw, nameEl.value.trim());
    Tokens.set(data.tokens.access_token, data.tokens.refresh_token);
    State.user = data.user;
    showToast('Account created — let\'s set up your profile');
    go('onboard');
  } catch (err) {
    if (err.status === 409) {
      setFieldError(emailEl, true);
      document.querySelector('#reg-email').closest('.field').querySelector('.field-error').textContent =
        'An account with this email already exists.';
    } else {
      showApiError(err);
    }
  } finally {
    showLoading(false);
  }
});

// ════════════════════════════════════════════════════════════
// AUTH — Forgot Password
// ════════════════════════════════════════════════════════════
document.getElementById('form-forgot').addEventListener('submit', async (e) => {
  e.preventDefault();
  const emailEl = document.getElementById('forgot-email');
  showLoading(true);
  try {
    await Api.forgotPassword(emailEl.value.trim());
    showToast('If that email exists, a reset link is on its way');
    go('login');
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
});

// ════════════════════════════════════════════════════════════
// AUTH — Google (placeholder redirect flow)
// ════════════════════════════════════════════════════════════
function startGoogleAuth() {
  const clientId = window.KINDRED_GOOGLE_CLIENT_ID || '';
  if (!clientId) {
    showToast('Google sign-in isn\'t configured yet');
    return;
  }
  const redirect = encodeURIComponent(window.location.origin + window.location.pathname);
  const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirect}&response_type=code&scope=email%20profile&prompt=select_account`;
  window.location.href = url;
}
document.getElementById('btn-google-login').addEventListener('click', startGoogleAuth);
document.getElementById('btn-google-register').addEventListener('click', startGoogleAuth);

async function handleGoogleRedirect() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  if (!code) return false;
  showLoading(true);
  try {
    const data = await Api.googleAuth(code);
    Tokens.set(data.tokens.access_token, data.tokens.refresh_token);
    State.user = data.user;
    window.history.replaceState({}, '', window.location.pathname);
    showToast(data.message || 'Welcome!');
    await routeAfterAuth();
    return true;
  } catch (err) {
    showApiError(err);
    return false;
  } finally {
    showLoading(false);
  }
}

// ════════════════════════════════════════════════════════════
// ONBOARDING
// ════════════════════════════════════════════════════════════
let obStep = 1;
const OB_TOTAL = 4;
const OnboardPhotos = [null, null];

function showObStep(n) {
  document.querySelectorAll('.onboard-step').forEach(s => s.hidden = (parseInt(s.dataset.step) !== n));
  document.querySelectorAll('.onboard-progress .seg').forEach(seg => {
    const i = parseInt(seg.dataset.seg);
    seg.classList.toggle('done', i < n);
    seg.classList.toggle('active', i === n);
  });
  document.getElementById('ob-back').style.display = n === 1 ? 'none' : 'flex';
  document.getElementById('ob-next').textContent = n === OB_TOTAL ? 'Complete profile' : 'Continue';
  obStep = n;
}

function validateObStep(n) {
    if (n === 1) {
      const age = parseInt(document.getElementById('ob-age').value);
      const city = document.getElementById('ob-city').value.trim();
      if (!age || age < 30 || age > 80) { showToast('Please enter an age between 30 and 80'); return false; }
      if (!city) { showToast('Please tell us your city'); return false; }
      if (!ChipState['gender']) { showToast('Please select your gender'); return false; }
      if (!ChipState['seeking']) { showToast('Please select who you\'d like to meet'); return false; }
      return true;
    }
    if (n === 2) {
      if (!ChipState['marital_history']) { showToast('Please select your marital history'); return false; }
      if (!ChipState['has_children']) { showToast('Please let us know about children'); return false; }
      if (!ChipState['relationship_goal']) { showToast('Please select what you\'re looking for'); return false; }
      return true;
    }
  if (n === 3) {
    const bio = document.getElementById('ob-bio').value.trim();
    if (bio.length < 20) { showToast('Tell us a little more — at least 20 characters'); return false; }
    return true;
  }
  if (n === 4) {
 //   if (!OnboardPhotos[0]) { showToast('Please add at least one photo'); return false; }
    // Photo is optional — skip validation
    return true;
  }
  return true;
}

document.getElementById('ob-next').addEventListener('click', async () => {
  if (!validateObStep(obStep)) return;
  if (obStep < OB_TOTAL) {
    showObStep(obStep + 1);
  } else {
    await completeOnboarding();
  }
});
document.getElementById('ob-back').addEventListener('click', () => {
  if (obStep > 1) showObStep(obStep - 1);
});

// Bio counter
const obBio = document.getElementById('ob-bio');
obBio.addEventListener('input', () => {
  document.getElementById('ob-bio-count').textContent = `${obBio.value.length} / 500`;
});

// Photo slots
function initOnboardPhotoSlots() {
  document.querySelectorAll('#onboard-photo-grid .photo-slot').forEach(slot => {
    const input = slot.querySelector('input[type="file"]');
    slot.addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
      const file = input.files[0];
      if (!file) return;
      OnboardPhotos[parseInt(slot.dataset.slot)] = file;
      const reader = new FileReader();
      reader.onload = (ev) => {
        slot.innerHTML = `<img src="${ev.target.result}" alt=""/>` +
          (slot.dataset.slot === '0' ? '<span class="primary-badge">Main</span>' : '');
        slot.classList.add('filled');
      };
      reader.readAsDataURL(file);
    });
  });
}
initOnboardPhotoSlots();

async function completeOnboarding() {
  showLoading(true);
  try {
    const payload = {
      first_name: State.user.email.split('@')[0],
      age: parseInt(document.getElementById('ob-age').value),
      gender: ChipState['gender'],
      seeking: ChipState['seeking'],
      location_city: document.getElementById('ob-city').value.trim(),
      bio: document.getElementById('ob-bio').value.trim(),
      occupation: document.getElementById('ob-occupation').value.trim() || null,
      marital_history: ChipState['marital_history'],
      has_children: ChipState['has_children'],
      relationship_goal: ChipState['relationship_goal'],
      interests: ChipState['interests'] || [],
    };

    try {
      State.profile = await Api.createProfile(payload);
    } catch (createErr) {
      if (createErr.status === 409) {
        // Profile already exists — try to update it instead
        State.profile = await Api.updateProfile(payload);
      } else {
        throw createErr;
      }
    }

    // Upload photos
    for (const file of OnboardPhotos) {
      if (file) {
        try { await Api.uploadPhoto(file); } catch (e) {
          console.warn('Photo upload failed', e);
        }
      }
    }

    try {
      State.profile = await Api.getMyProfile();
    } catch (e) {
      console.warn('Could not reload profile', e);
    }

    showToast('Profile created — welcome to Mellow 🌿');
    go('discover');

  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}

// ════════════════════════════════════════════════════════════
// LOGOUT / DELETE ACCOUNT
// ════════════════════════════════════════════════════════════
document.getElementById('btn-logout').addEventListener('click', async () => {
  await Api.logout();
  Tokens.clear();
  State.user = null;
  State.profile = null;
  resetOnboardingForm();
  go('welcome', { skipHistory: true });
});

document.getElementById('btn-delete-account').addEventListener('click', async () => {
  if (!confirm('This will permanently delete your account and profile. Continue?')) return;
  showLoading(true);
  try {
    await Api.deleteAccount();
    Tokens.clear();
    showToast('Your account has been deleted');
    go('welcome', { skipHistory: true });
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
});

function resetOnboardingForm() {
  obStep = 1;
  showObStep(1);
  document.getElementById('form-login').reset();
  document.getElementById('form-register').reset();
}

// ════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════
async function routeAfterAuth() {
  try {
    const me = await Api.me();
    State.user = me;
    if (me.has_profile) {
      State.profile = await Api.getMyProfile();
      go('discover', { skipHistory: true });
    } else {
      go('onboard', { skipHistory: true });
    }
  } catch (err) {
    Tokens.clear();
    go('welcome', { skipHistory: true });
  }
}

(async function init() {
  initChipGroups();
  initOptionCards();
  showObStep(1);

  const handledRedirect = await handleGoogleRedirect();
  if (handledRedirect) return;

  if (Tokens.loggedIn) {
    showLoading(true);
    await routeAfterAuth();
    showLoading(false);
  } else {
    go('welcome', { skipHistory: true });
  }
})();
