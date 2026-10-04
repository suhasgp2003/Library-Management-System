# The Reading Room interface

The Django interface uses a cream-and-forest palette, serif editorial headings,
large book covers, responsive cards, keyboard-accessible controls, and light/dark
themes. Models, migrations, routes, circulation views, and database settings are
unchanged. `library/templatetags/library_ui.py` supplies read-only dashboard data.

## Run locally

Use Python 3.12 or later and the repository's requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## Edit the styles

The generated `library/static/css/style.css` is included so a Python deployment
does not need Node or a runtime Tailwind CDN. Edit `input.css` and rebuild when
templates, utility classes, or theme styles change:

```powershell
npm ci
npm run build:css
```

`npm run watch:css` rebuilds during development. The build follows the
[official Tailwind CLI workflow](https://tailwindcss.com/docs/installation/tailwind-cli).

## Interface behavior

- Book search submits the existing `q` parameter. Category, availability, and
  sorting refine the current results in the browser. Reset filters clears those
  refinements; View all books also clears the server search.
- Reader search and department filters run in the browser.
- The theme follows the system preference until manually changed. A manual
  preference is saved locally; storage-blocked browsers still support toggling.
- Covers use Open Library's ISBN cover endpoint with no referrer. Missing or
  failed images leave a locally styled title-and-author cover in place.
- Contact opens a draft in the user's email application. There is no new email
  service or submission endpoint.
- Issue/return links preserve the repository's existing behavior. The UI hides
  issuing when no copies are available.

## Verification

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test library
npm run build:css
node --check library/static/js/theme.js
node --check library/static/js/script.js
```
