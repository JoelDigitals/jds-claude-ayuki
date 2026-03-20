"""
jds_cloud_client.py
═══════════════════
API-Client für die Verbindung zwischen JDS-Verein und JDS-Cloud.

Einbindung in dein Vereinsprojekt:
  1. Diese Datei in dein Projekt kopieren (z.B. verein/jds_cloud_client.py)
  2. In settings.py eintragen:
       JDS_CLOUD_URL   = 'http://localhost:8001'   # URL der jds-cloud
       JDS_CLOUD_TOKEN = 'dein-token-hier'          # Token aus /tokens/
  3. Fertig – alle Funktionen unten nutzen.
"""

import os
import requests
from django.conf import settings


def _client():
    """Gibt eine requests.Session mit gesetztem Bearer-Token zurück."""
    s = requests.Session()
    token = getattr(settings, 'JDS_CLOUD_TOKEN', '')
    if not token:
        raise ValueError(
            'JDS_CLOUD_TOKEN ist nicht in settings.py gesetzt!\n'
            'Füge JDS_CLOUD_TOKEN = "dein-token" in settings.py ein.'
        )
    s.headers['Authorization'] = f'Bearer {token}'
    return s


def _base():
    url = getattr(settings, 'JDS_CLOUD_URL', '').rstrip('/')
    if not url:
        raise ValueError(
            'JDS_CLOUD_URL ist nicht in settings.py gesetzt!\n'
            'Füge JDS_CLOUD_URL = "http://localhost:8001" in settings.py ein.'
        )
    return url


# ──────────────────────────────────────────────────────────────────────────────
# Datei hochladen
# ──────────────────────────────────────────────────────────────────────────────

def upload_datei(datei_pfad, *, verein=None, kontext='', ref_id=None,
                 folder_name='', is_public=False):
    """
    Lädt eine einzelne Datei in die JDS-Cloud hoch.

    Parameter:
        datei_pfad   – absoluter Pfad zur Datei ODER Django FieldFile / InMemoryUploadedFile
        verein       – Verein-Objekt (optional, für Kontext)
        kontext      – z.B. 'satzung', 'beleg', 'protokoll', 'spendenquittung'
        ref_id       – PK des zugehörigen Objekts (optional)
        folder_name  – Zielordner in der Cloud (wird auto-erstellt)
        is_public    – True = öffentlicher Download-Link

    Rückgabe:
        dict mit 'id', 'name', 'size_human', 'download_url', ggf. 'public_url'
    """
    session = _client()
    base    = _base()

    # Datei öffnen
    if isinstance(datei_pfad, str):
        f = open(datei_pfad, 'rb')
        fname = os.path.basename(datei_pfad)
        close_after = True
    else:
        # Django FieldFile oder InMemoryUploadedFile
        datei_pfad.seek(0)
        f = datei_pfad
        fname = getattr(datei_pfad, 'name', 'datei')
        fname = os.path.basename(fname)
        close_after = False

    payload = {
        'kontext':    kontext,
        'folder_name': folder_name or kontext or 'verein',
        'is_public':  'true' if is_public else 'false',
    }
    if verein:
        payload['verein_id']   = str(verein.pk)
        payload['verein_name'] = verein.name
    if ref_id:
        payload['ref_id'] = str(ref_id)

    try:
        r = session.post(
            f'{base}/api/v1/upload/',
            files={'files': (fname, f)},
            data=payload,
            timeout=60,
        )
        r.raise_for_status()
        result = r.json()
        return result['uploaded'][0] if result.get('uploaded') else {}
    finally:
        if close_after:
            f.close()


def upload_django_field(field_file, *, verein=None, kontext='', ref_id=None,
                         folder_name='', is_public=False):
    """
    Lädt ein Django-FileField direkt hoch.
    Beispiel: upload_django_field(verein.satzung, verein=verein, kontext='satzung')
    """
    if not field_file:
        return None
    return upload_datei(field_file, verein=verein, kontext=kontext,
                        ref_id=ref_id, folder_name=folder_name, is_public=is_public)


# ──────────────────────────────────────────────────────────────────────────────
# Dateien abfragen
# ──────────────────────────────────────────────────────────────────────────────

def get_dateien(*, verein_id=None, kontext=None, ref_id=None, search=None):
    """
    Gibt eine Liste von Dateien aus der Cloud zurück.

    Parameter:
        verein_id – nur Dateien dieses Vereins
        kontext   – nur Dateien mit diesem Kontext (z.B. 'beleg')
        ref_id    – nur Dateien mit dieser Quell-PK
        search    – Suche im Dateinamen
    """
    session = _client()
    params  = {}
    if verein_id: params['verein_id'] = verein_id
    if kontext:   params['kontext']   = kontext
    if ref_id:    params['ref_id']    = ref_id
    if search:    params['search']    = search

    r = session.get(f'{_base()}/api/v1/files/', params=params, timeout=15)
    r.raise_for_status()
    return r.json().get('files', [])


def get_dateien_fuer_objekt(ref_id, kontext):
    """Alle Cloud-Dateien für ein bestimmtes Objekt (z.B. einen Kontoposten)."""
    return get_dateien(ref_id=ref_id, kontext=kontext)


# ──────────────────────────────────────────────────────────────────────────────
# Datei löschen
# ──────────────────────────────────────────────────────────────────────────────

def delete_datei(cloud_id):
    """Löscht eine Datei aus der Cloud anhand ihrer Cloud-ID."""
    session = _client()
    r = session.delete(f'{_base()}/api/v1/files/{cloud_id}/', timeout=15)
    r.raise_for_status()
    return r.json()


# ──────────────────────────────────────────────────────────────────────────────
# Statistik
# ──────────────────────────────────────────────────────────────────────────────

def get_info():
    """Gibt Token-Info und Speicherstatistik zurück."""
    session = _client()
    r = session.get(f'{_base()}/api/v1/info/', timeout=10)
    r.raise_for_status()
    return r.json()


# ──────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen speziell für Vereins-Modelle
# ──────────────────────────────────────────────────────────────────────────────

def upload_vereins_satzung(verein):
    """Lädt die Satzung eines Vereins in die Cloud hoch."""
    if not verein.satzung:
        return None
    return upload_django_field(
        verein.satzung,
        verein=verein,
        kontext='satzung',
        ref_id=verein.pk,
        folder_name=f'Verein-{verein.pk}',
    )


def upload_kontoposten_beleg(kontoposten):
    """Lädt den Beleg eines Kontopostens in die Cloud hoch."""
    if not kontoposten.beleg:
        return None
    return upload_django_field(
        kontoposten.beleg,
        verein=kontoposten.verein,
        kontext='beleg',
        ref_id=kontoposten.pk,
        folder_name=f'Belege-{kontoposten.verein.pk}',
    )


def upload_protokoll_datei(protokoll):
    """Lädt die Protokoll-Datei in die Cloud hoch."""
    if not protokoll.datei:
        return None
    return upload_django_field(
        protokoll.datei,
        verein=protokoll.verein,
        kontext='protokoll',
        ref_id=protokoll.pk,
        folder_name=f'Protokolle-{protokoll.verein.pk}',
    )


def get_belege_fuer_verein(verein_id):
    """Alle hochgeladenen Belege eines Vereins."""
    return get_dateien(verein_id=verein_id, kontext='beleg')


def get_protokolle_fuer_verein(verein_id):
    """Alle hochgeladenen Protokolle eines Vereins."""
    return get_dateien(verein_id=verein_id, kontext='protokoll')
