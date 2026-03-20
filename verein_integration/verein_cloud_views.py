"""
verein_cloud_views.py
═════════════════════
Zusätzliche Views für dein Vereinsprojekt.
Füge diese URLs in deine verein/urls.py ein:

    from .verein_cloud_views import (
        cloud_datei_hochladen,
        cloud_dateien_liste,
        cloud_datei_loeschen,
        cloud_status,
    )

    path('cloud/upload/',            cloud_datei_hochladen,  name='cloud_upload'),
    path('cloud/dateien/',           cloud_dateien_liste,    name='cloud_dateien'),
    path('cloud/loeschen/<int:cid>/',cloud_datei_loeschen,   name='cloud_loeschen'),
    path('cloud/status/',            cloud_status,           name='cloud_status'),
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .jds_cloud_client import (
    upload_datei, get_dateien, delete_datei, get_info,
    upload_vereins_satzung, upload_kontoposten_beleg, upload_protokoll_datei,
)


# ── Allgemeiner Datei-Upload ──────────────────────────────────────────────────
@login_required
@require_POST
def cloud_datei_hochladen(request):
    """
    POST /cloud/upload/
    Lädt eine oder mehrere Dateien mit optionalem Kontext in die JDS-Cloud.

    Formularfelder:
        files      – Dateien (multiple)
        kontext    – z.B. 'satzung', 'beleg', 'protokoll'
        ref_id     – PK des zugehörigen Objekts (optional)
        folder     – Zielordner (optional)
        is_public  – checkbox (optional)
        redirect_to – URL für Weiterleitung nach Upload
    """
    try:
        from .views import _get_verein
        verein = _get_verein(request)
    except Exception:
        verein = None

    files      = request.FILES.getlist('files')
    kontext    = request.POST.get('kontext', '').strip()
    ref_id     = request.POST.get('ref_id') or None
    folder     = request.POST.get('folder', '').strip()
    is_public  = request.POST.get('is_public') == 'on'
    redirect_to = request.POST.get('redirect_to', '/')

    if not files:
        messages.error(request, 'Keine Dateien ausgewählt.')
        return redirect(redirect_to)

    uploaded = 0
    errors   = []

    for f in files:
        try:
            result = upload_datei(
                f,
                verein=verein,
                kontext=kontext,
                ref_id=ref_id,
                folder_name=folder or kontext or 'verein',
                is_public=is_public,
            )
            if result:
                uploaded += 1
        except Exception as e:
            errors.append(f'{f.name}: {e}')

    if uploaded:
        messages.success(request, f'✓ {uploaded} Datei(en) in JDS-Cloud hochgeladen.')
    for err in errors:
        messages.error(request, f'Fehler: {err}')

    return redirect(redirect_to)


# ── Datei-Liste ───────────────────────────────────────────────────────────────
@login_required
def cloud_dateien_liste(request):
    """
    GET /cloud/dateien/
    Zeigt alle Cloud-Dateien des Vereins an (nach Kontext filterbar).
    """
    try:
        from .views import _get_verein
        verein = _get_verein(request)
        verein_id = verein.pk if verein else None
    except Exception:
        verein_id = None

    kontext = request.GET.get('kontext', '')
    search  = request.GET.get('q', '')

    try:
        dateien = get_dateien(
            verein_id=verein_id,
            kontext=kontext or None,
            search=search or None,
        )
        cloud_ok = True
        cloud_error = None
    except Exception as e:
        dateien = []
        cloud_ok = False
        cloud_error = str(e)

    return render(request, 'verein/cloud_dateien.html', {
        'dateien':     dateien,
        'kontext':     kontext,
        'search':      search,
        'cloud_ok':    cloud_ok,
        'cloud_error': cloud_error,
        'verein':      verein if 'verein' in dir() else None,
        'kontexte':    ['satzung', 'beleg', 'protokoll', 'spendenquittung', 'sonstiges'],
    })


# ── Datei löschen ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def cloud_datei_loeschen(request, cid):
    """POST /cloud/loeschen/<cloud_id>/"""
    redirect_to = request.POST.get('redirect_to', '/verein/cloud/dateien/')
    try:
        delete_datei(cid)
        messages.success(request, 'Datei aus JDS-Cloud gelöscht.')
    except Exception as e:
        messages.error(request, f'Fehler beim Löschen: {e}')
    return redirect(redirect_to)


# ── Verbindungsstatus ─────────────────────────────────────────────────────────
@login_required
def cloud_status(request):
    """GET /cloud/status/ — prüft ob die Verbindung zur JDS-Cloud funktioniert."""
    try:
        info = get_info()
        return JsonResponse({'status': 'ok', **info})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=503)


# ── Spezifische Upload-Shortcuts ──────────────────────────────────────────────

@login_required
@require_POST
def cloud_satzung_hochladen(request):
    """Lädt die Vereinssatzung direkt aus dem Vereins-Modell hoch."""
    try:
        from .views import _get_verein
        verein = _get_verein(request)
        result = upload_vereins_satzung(verein)
        if result:
            messages.success(request, f'Satzung in JDS-Cloud hochgeladen: {result["name"]}')
        else:
            messages.warning(request, 'Keine Satzung zum Hochladen vorhanden.')
    except Exception as e:
        messages.error(request, f'Cloud-Fehler: {e}')
    return redirect('verein:satzung')


@login_required
@require_POST
def cloud_beleg_hochladen(request, posten_pk):
    """Lädt den Beleg eines Kontopostens hoch."""
    from django.shortcuts import get_object_or_404
    try:
        from .views import _get_verein
        from .models import Kontoposten
        verein = _get_verein(request)
        posten = get_object_or_404(Kontoposten, pk=posten_pk, verein=verein)
        result = upload_kontoposten_beleg(posten)
        if result:
            messages.success(request, f'Beleg in JDS-Cloud gesichert: {result["name"]}')
        else:
            messages.warning(request, 'Kein Beleg zum Hochladen vorhanden.')
    except Exception as e:
        messages.error(request, f'Cloud-Fehler: {e}')
    return redirect('verein:konto_uebersicht')
