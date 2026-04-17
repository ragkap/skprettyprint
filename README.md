# Smartkarma Pretty Print Utility

Minimalist investment intelligence PDF generator. Three modules:

- **Pretty Print Primer** — Generate Smartkarma Primer PDF from a Bloomberg ticker or company name.
- **Pretty Print Insight** — (coming soon)
- **Pretty Print eBook** — (coming soon)

## Local dev

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in real values
```

WeasyPrint native libs (macOS):

```bash
brew install pango gdk-pixbuf libffi
```

Run:

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000.

## Deploy to Railway

1. Push this repo to GitHub.
2. On Railway: **New Project → Deploy from GitHub repo** → pick this repo. Railway auto-detects the `Dockerfile`.
3. In the service's **Variables** tab, add:
   - `DB_NAME`
   - `DB_HOST`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_PORT`
4. Under **Settings → Networking**, click **Generate Domain**.
5. Deploy. Server listens on `$PORT` (Railway injects this).

The app fails fast on startup if any `DB_*` var is missing.

## API usage (curl)

The frontend is optional — you can hit the HTTP endpoints directly.

Replace `YOUR-APP.up.railway.app` with your Railway domain (or `localhost:8000` for local dev).

### Get a Primer PDF by Bloomberg ticker

```bash
curl -L -o primer.pdf \
  "https://YOUR-APP.up.railway.app/api/primer?ticker=DBS%20SP"
```

To save with the server-provided filename (e.g. `DBS Group (DBS SP)  | Smartkarma Primer 20260417.pdf`):

```bash
curl -LOJ "https://YOUR-APP.up.railway.app/api/primer?ticker=DBS%20SP"
```

### Search by company name or ticker

```bash
curl -s "https://YOUR-APP.up.railway.app/api/search?q=DBS"
```

Returns JSON:

```json
{"results": [{"name": "DBS", "ticker": "DBS SP"}, ...]}
```

Then pass the `ticker` into `/api/primer`.

### Notes

- URL-encode spaces in tickers: `DBS SP` → `DBS%20SP` (or just wrap the URL in quotes).
- `404` if no primer exists for that ticker; `500` on generation failure. Both come back as JSON `{"detail": "..."}`.
- Expect 10–20s response time (DB query + yfinance chart + WeasyPrint render).
- No auth on endpoints — don't expose publicly without adding an API key.
