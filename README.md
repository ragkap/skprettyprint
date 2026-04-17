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
# skprettyprint
