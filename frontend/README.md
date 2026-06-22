# 💜 Kindred — Frontend (Phase 2)

A warm, editorial-style mobile web app (PWA) for the Kindred dating experience —
built in vanilla HTML/CSS/JS, no build step required.

---

## Quick Start

### 1 — Configure the API connection

Open `index.html` and add this **before** the script tags at the bottom
(or create a small `config.js` and link it first):

```html
<script>
  window.KINDRED_API_BASE = 'http://localhost:8000';   // your FastAPI backend
  window.KINDRED_WS_BASE  = 'ws://localhost:8000';     // websocket base
  window.KINDRED_GOOGLE_CLIENT_ID = '';                // optional, for Google sign-in
</script>
```

In production, point these at your deployed Railway URL, e.g.
`https://kindred-api.up.railway.app` and `wss://kindred-api.up.railway.app`.

### 2 — Update backend CORS

Make sure your backend `.env` includes the URL you're serving this frontend from:

```
ALLOWED_ORIGINS=http://localhost:5500,https://yourdomain.com
```

### 3 — Serve the frontend

Any static server works. From `frontend/`:

```bash
# Python
python -m http.server 5500

# Node
npx serve -p 5500
```

Open `http://localhost:5500` — on a phone, use your computer's local IP
(e.g. `http://192.168.1.20:5500`) while on the same Wi-Fi network.

### 4 — Install as an app (PWA)

On Android Chrome: **⋮ menu → Add to Home screen**.
The app runs full-screen with its own icon — no browser bar.

---

## File Structure

```
frontend/
├── index.html          # App shell — all screens
├── manifest.json        # PWA config
├── css/
│   ├── main.css         # Design tokens, buttons, forms, nav
│   ├── auth.css          # Welcome, login, register, onboarding
│   ├── discover.css      # Swipe cards, Kindred Bloom, filters
│   └── messages.css       # Matches, chat, profile, subscription
└── js/
    ├── api.js            # API client + token management
    ├── app.js             # Navigation, auth, onboarding
    ├── discover.js         # Swipe logic, compatibility bloom
    ├── messages.js          # Matches list, chat, WebSocket
    └── profile.js            # Profile edit, photos, subscription
```

---

## Design System

| Token | Value | Use |
|---|---|---|
| `--plum` | `#3D2645` | Headers, primary text, dark surfaces |
| `--rose` | `#C9705E` | Primary actions, like/CTA |
| `--gold` | `#CFA052` | Premium accents, Kindred Plus |
| `--sage` | `#87966F` | Positive states, online status |
| `--cream` | `#FBF6EF` | App background |

**Typography:** Fraunces (display/serif) + Inter (UI/body)

**Signature element — the Kindred Bloom:** an 8-petal radial compatibility
indicator shown on each discovery card (`renderBloom(score)` in `discover.js`).

---

## Screens Implemented

- Welcome / Login / Register / Forgot password
- 4-step onboarding (basics → life stage → about → photos)
- Discover (swipe cards, filters, match celebration)
- Messages (new matches row, conversation list)
- Chat (real-time via WebSocket, free-tier limit banner)
- Profile (view, completion meter, settings)
- Profile edit (bio, lifestyle, interests, photo management)
- Subscription (3-tier plan comparison, Stripe checkout redirect)
- Report / block sheet

---

## Known Follow-ups (noted for backend alignment)

1. **Block/Report target ID** — `messages.js` currently passes the other
   person's *Profile ID* to `/safety/block` and `/safety/report`, but those
   endpoints expect a *User ID*. Either add a `profile_id → user_id` lookup
   endpoint, or adjust the schemas to accept profile IDs.
2. **Blocked users list** — no `GET /safety/blocked` endpoint exists yet;
   the "Blocked users" settings row currently shows a placeholder toast.
3. **Data export** — no backend endpoint yet; shows a placeholder toast.
4. **Google OAuth** — requires `GOOGLE_CLIENT_ID` to be set on both frontend
   (`window.KINDRED_GOOGLE_CLIENT_ID`) and backend `.env`.
5. **Rewind** — intentionally disabled (shows upsell toast); add an
   "undo last swipe" endpoint if this should be a real Kindred Plus perk.

---

*Kindred Frontend v1.0 — Phase 2*
*"Designed for people who know what they want — and what they don't."*
