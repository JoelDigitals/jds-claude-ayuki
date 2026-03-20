# JDS Cloud ☁

Ein vollständiges Django-Projekt für eine persönliche Online-Cloud.  
Eigene Templates, eigenes CSS/JS — **kein Django REST Framework**.

---

## 🚀 Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, für /admin/
python manage.py runserver
```

Öffne: **http://127.0.0.1:8000**

---

## Was enthalten ist

- **Landing Page** (`/`) – Einstiegsseite für nicht eingeloggte Nutzer
- **Registrierung & Login** – eigene Auth-Templates
- **Dashboard** – Ordner + Dateien als Grid, Drag & Drop Upload
- **Ordner** – beliebig verschachtelbar, mit Breadcrumb-Navigation
- **Upload** – mehrere Dateien gleichzeitig, Drag & Drop
- **Download** – direkt aus dem Browser
- **Öffentliches Teilen** – Datei per Link teilen, jederzeit widerrufbar
- **Suche** – Dateinamen durchsuchen
- **Admin** – Django Admin unter `/admin/`

---

## JSON-API (ohne DRF, eigene Views)

Für die Einbindung in andere Django-Projekte gibt es eigene JSON-Endpunkte:

```
POST /api/upload/          Datei(en) hochladen (multipart, field: files)
GET  /api/files/           Dateiliste als JSON
GET  /api/files/?folder=<id>   Nur Dateien in Ordner
POST /api/delete/<id>/     Datei löschen
```

**Auth:** Alle API-Endpunkte nutzen Session-Auth (Django Login erforderlich).

Beispiel mit Python requests:
```python
import requests

session = requests.Session()
# Login
session.get('http://localhost:8000/login/')
token = session.cookies.get('csrftoken')
session.post('http://localhost:8000/login/', data={
    'username': 'dein-user',
    'password': 'dein-passwort',
    'csrfmiddlewaretoken': token,
})

# Datei hochladen
with open('datei.pdf', 'rb') as f:
    r = session.post('http://localhost:8000/api/upload/',
        files={'files': f},
        headers={'X-CSRFToken': session.cookies['csrftoken']})
print(r.json())
```

---

## In ein bestehendes Django-Projekt einbinden

1. Ordner `cloud/` kopieren
2. `settings.py`:
   ```python
   INSTALLED_APPS += ['cloud']
   MEDIA_URL = '/media/'
   MEDIA_ROOT = BASE_DIR / 'media'
   LOGIN_REDIRECT_URL = '/dashboard/'
   ```
3. `urls.py`:
   ```python
   from cloud import views as cloud_views
   # … die URLs aus jds_claude/urls.py übernehmen
   ```
4. `python manage.py migrate`

---

## Projektstruktur

```
jds-claude/
├── manage.py
├── requirements.txt
├── jds_claude/         # Django-Projekt-Paket
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── cloud/              # Cloud-App (wiederverwendbar)
│   ├── models.py       # CloudFile, Folder
│   ├── views.py        # Alle Views + JSON-API
│   ├── admin.py
│   └── migrations/
├── templates/
│   ├── base.html
│   ├── cloud/
│   │   ├── index.html
│   │   ├── dashboard.html
│   │   └── search.html
│   └── registration/
│       ├── login.html
│       └── register.html
└── static/
    ├── css/main.css
    └── js/main.js
```
