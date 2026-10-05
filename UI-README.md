# The Reading Room interface

The Django interface uses a cream-and-forest palette, serif editorial headings,
large book covers, responsive cards, keyboard-accessible controls, and light/dark
themes. Backend workflows use permission-checked forms, MySQL migrations,
environment-based settings, and transactional circulation services.
See `README.md` and `docs/architecture.md` for the current full-stack workflow.

## Run locally

Configure MySQL and `.env` using `README.md` first. Then use Python 3.12 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## Edit the styles

The generated `library/static/css/style.css` is included so a Python deployment
does not need Node or a runtime Tailwind CDN. Edit `assets/input.css` and rebuild when
templates, utility classes, or theme styles change:

```powershell
npm ci
npm run build:css
```

`npm run watch:css` rebuilds during development. The build follows the
[official Tailwind CLI workflow](https://tailwindcss.com/docs/installation/tailwind-cli).

## Interface behavior

- The shared header shows a page breadcrumb and reader name. Account actions live
  in a keyboard-accessible profile dropdown; Escape closes it and returns focus.
  Small screens use an avatar-only trigger and keep the menu within the viewport.
- Book and reader searches, filters, sorting, and pagination run on the server,
  so they work across the entire collection and preserve query parameters.
- The theme follows the system preference until manually changed. A manual
  preference is saved locally; storage-blocked browsers still support toggling.
- Covers use Open Library's ISBN cover endpoint with no referrer. Missing or
  failed images leave a locally styled title-and-author cover in place.
- Contact opens a draft in the user's email application. There is no new email
  service or submission endpoint.
- Issue/return links open librarian-only forms; state changes require POST and CSRF.
  Student pages show only that student's loans and reservations.

## Verification

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test library
npm run build:css
node --check library/static/js/theme.js
node --check library/static/js/script.js
```
