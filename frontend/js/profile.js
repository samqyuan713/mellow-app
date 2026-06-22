/* ════════════════════════════════════════════════════════════
   KINDRED — Profile, Edit, Subscription, Settings
   ════════════════════════════════════════════════════════════ */

// ════════════════════════════════════════════════════════════
// PROFILE SCREEN (view)
// ════════════════════════════════════════════════════════════
async function loadProfileScreen() {
  try {
    if (!State.profile) State.profile = await Api.getMyProfile();
    if (!State.subscription) State.subscription = await Api.getMySubscription();
  } catch (err) {
    showApiError(err);
    return;
  }
  const p = State.profile;

  document.getElementById('profile-avatar').innerHTML = avatarHtml(p);
  document.getElementById('profile-name').textContent = `${p.first_name}, ${p.age}`;
  document.getElementById('profile-meta').textContent =
    [p.occupation, p.location_city].filter(Boolean).join(' · ') || 'Add your details';

  const banner = document.getElementById('profile-completion-banner');
  if (p.completion_pct < 100) {
    banner.hidden = false;
    document.getElementById('pc-pct').textContent = `${p.completion_pct}%`;
  } else {
    banner.hidden = true;
  }

  const planNames = { free: 'Free plan', mellow: 'Mellow', mellow_plus: 'Mellow Plus' };
  document.getElementById('plan-name').textContent = planNames[State.subscription.plan] || 'Free plan';

  const visToggle = document.getElementById('toggle-visibility');
  visToggle.classList.toggle('on', p.is_visible);
}

document.getElementById('toggle-visibility').addEventListener('click', async (e) => {
  const btn = e.currentTarget;
  const newVal = !btn.classList.contains('on');
  btn.classList.toggle('on', newVal);
  try {
    await Api.setVisibility(newVal);
    State.profile.is_visible = newVal;
    showToast(newVal ? 'Your profile is visible in Discover' : 'Your profile is hidden from Discover');
  } catch (err) {
    btn.classList.toggle('on', !newVal);
    showApiError(err);
  }
});

document.getElementById('open-blocked-list').addEventListener('click', () => {
  showToast('Blocked users management is coming soon');
});
document.getElementById('open-data-export').addEventListener('click', () => {
  showToast('We\'ll email you a copy of your data within 24 hours');
});

// ════════════════════════════════════════════════════════════
// PROFILE EDIT SCREEN
// ════════════════════════════════════════════════════════════
const EditPhotos = { items: [], maxPhotos: 2 };

async function loadProfileEditScreen() {
  showLoading(true);
  try {
    if (!State.profile) State.profile = await Api.getMyProfile();
    if (!State.subscription) State.subscription = await Api.getMySubscription();
  } catch (err) {
    showApiError(err);
    showLoading(false);
    return;
  }
  const p = State.profile;
  EditPhotos.maxPhotos = State.subscription.is_premium ? 6 : 2;
  EditPhotos.items = [...(p.photos || [])];

  document.getElementById('edit-bio').value = p.bio || '';
  document.getElementById('edit-bio-count').textContent = `${(p.bio || '').length} / 500`;
  document.getElementById('edit-occupation').value = p.occupation || '';
  document.getElementById('edit-education').value = p.education || '';
  document.getElementById('edit-city').value = p.location_city || '';

  setChipSelection('edit-relationship_goal', p.relationship_goal);
  setChipSelection('edit-marital_history', p.marital_history);
  setChipSelection('edit-drinking', p.drinking);
  setChipSelection('edit-smoking', p.smoking);
  setChipSelection('edit-interests', p.interests || []);

  renderEditPhotoGrid();
  showLoading(false);
}

document.getElementById('edit-bio').addEventListener('input', (e) => {
  document.getElementById('edit-bio-count').textContent = `${e.target.value.length} / 500`;
});

function renderEditPhotoGrid() {
  const grid = document.getElementById('edit-photo-grid');
  grid.innerHTML = '';

  EditPhotos.items.forEach((photo, i) => {
    const slot = document.createElement('div');
    slot.className = 'photo-slot filled';
    slot.innerHTML = `
      <img src="${photo.url}" alt=""/>
      ${i === 0 ? '<span class="primary-badge">Main</span>' : ''}
      <button class="remove-btn" aria-label="Remove"><svg width="11" height="11"><use href="#i-x"/></svg></button>`;
    slot.querySelector('.remove-btn').addEventListener('click', async (e) => {
      e.stopPropagation();
      await deleteEditPhoto(photo.id);
    });
    if (i !== 0) {
      slot.addEventListener('click', () => makePhotoPrimary(photo.id));
    }
    grid.appendChild(slot);
  });

  if (EditPhotos.items.length < EditPhotos.maxPhotos) {
    const addSlot = document.createElement('div');
    addSlot.className = 'photo-slot';
    addSlot.innerHTML = `<span class="add-icon"><svg width="26" height="26"><use href="#i-plus"/></svg></span>
      <input type="file" accept="image/*" hidden/>`;
    const input = addSlot.querySelector('input');
    addSlot.addEventListener('click', () => input.click());
    input.addEventListener('change', () => uploadEditPhoto(input.files[0]));
    grid.appendChild(addSlot);
  }

  const note = document.getElementById('photo-limit-note');
  note.textContent = State.subscription?.is_premium
    ? `Up to ${EditPhotos.maxPhotos} photos with your plan.`
    : `Free plan allows up to ${EditPhotos.maxPhotos} photos. Upgrade to Mellow for up to 6.`;
}

async function uploadEditPhoto(file) {
  if (!file) return;
  showLoading(true);
  try {
    const photo = await Api.uploadPhoto(file);
    EditPhotos.items.push(photo);
    renderEditPhotoGrid();
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}

async function deleteEditPhoto(photoId) {
  showLoading(true);
  try {
    await Api.deletePhoto(photoId);
    EditPhotos.items = EditPhotos.items.filter(p => p.id !== photoId);
    renderEditPhotoGrid();
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}

async function makePhotoPrimary(photoId) {
  const ids = [photoId, ...EditPhotos.items.filter(p => p.id !== photoId).map(p => p.id)];
  showLoading(true);
  try {
    await Api.reorderPhotos(ids);
    EditPhotos.items = ids.map(id => EditPhotos.items.find(p => p.id === id));
    renderEditPhotoGrid();
    showToast('Main photo updated');
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}

document.getElementById('btn-save-profile').addEventListener('click', async () => {
  const bio = document.getElementById('edit-bio').value.trim();
  if (bio.length < 20) { showToast('Your bio should be at least 20 characters'); return; }

  const payload = {
    bio,
    occupation: document.getElementById('edit-occupation').value.trim() || null,
    education: document.getElementById('edit-education').value.trim() || null,
    location_city: document.getElementById('edit-city').value.trim() || null,
    relationship_goal: ChipState['edit-relationship_goal'],
    marital_history: ChipState['edit-marital_history'],
    drinking: ChipState['edit-drinking'],
    smoking: ChipState['edit-smoking'],
    interests: ChipState['edit-interests'] || [],
  };

  showLoading(true);
  try {
    State.profile = await Api.updateProfile(payload);
    showToast('Profile updated');
    go('profile');
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
});

// ════════════════════════════════════════════════════════════
// SUBSCRIPTION SCREEN
// ════════════════════════════════════════════════════════════
async function loadSubscriptionScreen() {
  showLoading(true);
  try {
    const [plans, sub] = await Promise.all([Api.getPlans(), Api.getMySubscription()]);
    State.subscription = sub;
    renderPlans(plans, sub);
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}

function renderPlans(plans, sub) {
  const list = document.getElementById('plans-list');
  list.innerHTML = '';

  plans.forEach(plan => {
    const isCurrent = plan.id === sub.plan;
    const card = document.createElement('div');
    card.className = 'plan-card' + (plan.id === 'mellow_plus' ? ' featured' : '') + (isCurrent ? ' current' : '');

    const f = plan.features;
    const features = [
      { label: `${f.daily_swipes === 'unlimited' ? 'Unlimited' : f.daily_swipes} swipes per day`, on: true },
      { label: `${f.messages_per_match === 'unlimited' ? 'Unlimited' : f.messages_per_match} messages per match`, on: true },
      { label: `Up to ${f.max_photos} photos`, on: true },
      { label: 'Advanced filters', on: f.advanced_filters },
      { label: 'Read receipts', on: f.read_receipts },
      { label: 'See who liked you', on: f.see_who_liked_you },
      { label: `${f.boosts_per_month} boost${f.boosts_per_month !== 1 ? 's' : ''} per month`, on: f.boosts_per_month > 0 },
      { label: 'Priority placement in Discover', on: f.priority_discovery },
    ];

    card.innerHTML = `
      ${plan.id === 'mellow_plus' ? '<span class="plan-badge">Most popular</span>' : ''}
      <div class="plan-name">${plan.name}</div>
      <div class="plan-price">$${plan.price_monthly.toFixed(2)}${plan.price_monthly > 0 ? '<span>/month</span>' : ''}</div>
      <div class="plan-features">
        ${features.map(ft => `
          <div class="plan-feature ${ft.on ? '' : 'muted'}">
            <span class="check"><svg width="14" height="14"><use href="#${ft.on ? 'i-check' : 'i-x'}"/></svg></span>
            <span>${ft.label}</span>
          </div>`).join('')}
      </div>
      ${isCurrent
        ? '<button class="btn btn-outline" disabled>Current plan</button>'
        : plan.id === 'free'
          ? ''
          : `<button class="btn ${plan.id === 'mellow_plus' ? 'btn-rose' : 'btn-primary'}" data-plan="${plan.id}">Upgrade to ${plan.name}</button>`}
    `;
    list.appendChild(card);
  });

  list.querySelectorAll('[data-plan]').forEach(btn => {
    btn.addEventListener('click', () => startCheckout(btn.dataset.plan));
  });
}

async function startCheckout(planId) {
  showLoading(true);
  try {
    const res = await Api.createCheckout(planId);
    window.location.href = res.checkout_url;
  } catch (err) {
    showApiError(err);
  } finally {
    showLoading(false);
  }
}
