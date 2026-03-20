# JDS-Verein ↔ JDS-Cloud Integration

Komplette Anleitung, um Dateien aus deinem **Vereinsprojekt** in die **JDS-Cloud** hochzuladen.

---

## Schritt 1 – JDS-Cloud starten

```bash
cd jds-claude
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001   # Port 8001, damit es nicht mit Vereinsprojekt kollidiert
```

---

## Schritt 2 – API-Token erstellen

1. In **jds-claude** einloggen: `http://localhost:8001`
2. Navigiere zu **API Tokens** (im linken Menü oder `http://localhost:8001/tokens/`)
3. Token erstellen:
   - Name: `JDS-Verein`
   - Verein-ID: (deine Verein-PK, z.B. `1`)
   - Vereinsname: `TSV Musterstadt`
4. Generierten Token **kopieren** (wird nur einmal angezeigt!)

---

## Schritt 3 – Vereinsprojekt konfigurieren

In deiner `settings.py`:

```python
# JDS-Cloud Integration
JDS_CLOUD_URL   = 'http://localhost:8001'   # URL der laufenden jds-cloud
JDS_CLOUD_TOKEN = 'dein-64-zeichen-token-hier'
```

---

## Schritt 4 – Dateien in dein Vereinsprojekt kopieren

```
verein_integration/
├── jds_cloud_client.py    →  verein/jds_cloud_client.py
├── verein_cloud_views.py  →  verein/verein_cloud_views.py
└── cloud_dateien.html     →  templates/verein/cloud_dateien.html
```

---

## Schritt 5 – URLs einbinden

In `verein/urls.py`:

```python
from .verein_cloud_views import (
    cloud_datei_hochladen,
    cloud_dateien_liste,
    cloud_datei_loeschen,
    cloud_status,
    cloud_satzung_hochladen,
    cloud_beleg_hochladen,
)

# In urlpatterns hinzufügen:
path('cloud/upload/',              cloud_datei_hochladen,    name='cloud_upload'),
path('cloud/dateien/',             cloud_dateien_liste,      name='cloud_dateien'),
path('cloud/loeschen/<int:cid>/',  cloud_datei_loeschen,     name='cloud_loeschen'),
path('cloud/status/',              cloud_status,             name='cloud_status'),
path('cloud/satzung/',             cloud_satzung_hochladen,  name='cloud_satzung'),
path('cloud/beleg/<int:posten_pk>/', cloud_beleg_hochladen,  name='cloud_beleg'),
```

---

## Schritt 6 – In bestehende Templates einbauen

### Satzung hochladen (z.B. in verein/satzung.html):

```html
<form method="post" action="{% url 'verein:cloud_satzung' %}">
    {% csrf_token %}
    <button type="submit" class="btn btn-outline btn-sm">☁ In Cloud sichern</button>
</form>
```

### Beleg hochladen (z.B. in konto_uebersicht.html):

```html
<form method="post" action="{% url 'verein:cloud_beleg' posten.pk %}">
    {% csrf_token %}
    <button type="submit" class="btn btn-outline btn-sm">☁ Beleg sichern</button>
</form>
```

### Allgemeiner Upload-Button (überall einsetzbar):

```html
<form method="post" action="{% url 'verein:cloud_upload' %}" enctype="multipart/form-data">
    {% csrf_token %}
    <input type="hidden" name="kontext" value="protokoll">
    <input type="hidden" name="redirect_to" value="{{ request.path }}">
    <input type="file" name="files" multiple>
    <button type="submit">☁ In Cloud hochladen</button>
</form>
```

---

## API direkt nutzen (im Python-Code)

```python
from .jds_cloud_client import upload_datei, get_dateien, get_info

# Datei hochladen
result = upload_datei(
    '/pfad/zur/datei.pdf',
    verein=mein_verein,        # Verein-Objekt
    kontext='protokoll',       # Kategorie
    ref_id=protokoll.pk,       # PK des Protokolls
)
print(result['download_url'])  # Download-Link

# Alle Protokolle eines Vereins abrufen
dateien = get_dateien(verein_id=1, kontext='protokoll')

# Speicherinfo
info = get_info()
print(info['total_human'])     # z.B. "42.3 MB"
```

---

## API-Endpunkte Referenz

| Methode | URL | Beschreibung |
|---------|-----|--------------|
| `POST` | `/api/v1/upload/` | Dateien hochladen |
| `GET` | `/api/v1/files/` | Dateien auflisten |
| `DELETE` | `/api/v1/files/<id>/` | Datei löschen |
| `GET` | `/api/v1/info/` | Token-Info + Statistik |

**Header für alle Anfragen:**
```
Authorization: Bearer <dein-token>
```

**Upload-Felder (multipart/form-data):**
```
files         – Dateien (required)
kontext       – Kategorie: satzung / beleg / protokoll / spendenquittung
verein_id     – Verein-PK (optional, wenn nicht im Token hinterlegt)
verein_name   – Vereinsname (optional)
ref_id        – PK des Quell-Objekts (optional)
folder_name   – Zielordner (optional)
is_public     – true / false (optional)
```

**Filter-Parameter für GET /api/v1/files/:**
```
verein_id     – nur Dateien dieses Vereins
kontext       – nur Dateien dieser Kategorie
ref_id        – nur Dateien dieses Objekts
search        – Suche im Dateinamen
```
