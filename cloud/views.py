import json, mimetypes, os
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum, Count
from django.http import (FileResponse, Http404, JsonResponse,
                          HttpResponseForbidden)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import CloudFile, Folder


# ── Landing page ──────────────────────────────────────────────────────────────
def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'cloud/index.html')


# ── Auth ──────────────────────────────────────────────────────────────────────
def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Willkommen, {user.username}! Dein Account wurde erstellt.')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ── Dashboard ─────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    folders = Folder.objects.filter(owner=request.user, parent=None)
    files   = CloudFile.objects.filter(owner=request.user, folder=None)
    stats   = CloudFile.objects.filter(owner=request.user).aggregate(
        total_files=Count('id'), total_bytes=Sum('size')
    )
    total_bytes = stats['total_bytes'] or 0
    return render(request, 'cloud/dashboard.html', {
        'folders':     folders,
        'files':       files,
        'total_files': stats['total_files'] or 0,
        'total_bytes': total_bytes,
        'total_human': _humanize(total_bytes),
        'current_folder': None,
    })


# ── Folder view ───────────────────────────────────────────────────────────────
@login_required
def folder_view(request, pk):
    folder  = get_object_or_404(Folder, pk=pk, owner=request.user)
    folders = Folder.objects.filter(owner=request.user, parent=folder)
    files   = CloudFile.objects.filter(owner=request.user, folder=folder)

    # Breadcrumb
    crumbs = []
    current = folder
    while current:
        crumbs.insert(0, current)
        current = current.parent

    stats = CloudFile.objects.filter(owner=request.user).aggregate(
        total_files=Count('id'), total_bytes=Sum('size')
    )
    total_bytes = stats['total_bytes'] or 0
    return render(request, 'cloud/dashboard.html', {
        'folders':        folders,
        'files':          files,
        'current_folder': folder,
        'breadcrumbs':    crumbs,
        'total_files':    stats['total_files'] or 0,
        'total_bytes':    total_bytes,
        'total_human':    _humanize(total_bytes),
    })


# ── Upload (HTML form) ────────────────────────────────────────────────────────
@login_required
@require_POST
def upload_files(request):
    uploaded = request.FILES.getlist('files')
    folder_id = request.POST.get('folder_id') or None
    folder = None
    if folder_id:
        folder = get_object_or_404(Folder, pk=folder_id, owner=request.user)

    count = 0
    for f in uploaded:
        mime, _ = mimetypes.guess_type(f.name)
        CloudFile.objects.create(
            owner=request.user,
            folder=folder,
            original_name=f.name,
            file=f,
            size=f.size,
            mime_type=mime or 'application/octet-stream',
        )
        count += 1

    messages.success(request, f'{count} Datei(en) erfolgreich hochgeladen.')
    if folder:
        return redirect('folder', pk=folder.pk)
    return redirect('dashboard')


# ── Download ──────────────────────────────────────────────────────────────────
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
import os

def download_file(request, pk):
    cf = get_object_or_404(CloudFile, pk=pk)

    if not os.path.isfile(cf.file.path):
        raise Http404

    resp = FileResponse(open(cf.file.path, 'rb'),
                        content_type=cf.mime_type or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{cf.original_name}"'
    return resp


# ── Public download (shared link) ─────────────────────────────────────────────
def public_download(request, token):
    cf = get_object_or_404(CloudFile, public_token=token, is_public=True)
    if not os.path.isfile(cf.file.path):
        raise Http404
    resp = FileResponse(open(cf.file.path, 'rb'),
                        content_type=cf.mime_type or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{cf.original_name}"'
    return resp


# ── Delete file ───────────────────────────────────────────────────────────────
@login_required
@require_POST
def delete_file(request, pk):
    cf = get_object_or_404(CloudFile, pk=pk, owner=request.user)
    folder_pk = cf.folder_id
    cf.delete()
    messages.success(request, 'Datei gelöscht.')
    if folder_pk:
        return redirect('folder', pk=folder_pk)
    return redirect('dashboard')


# ── Create folder ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def create_folder(request):
    name      = request.POST.get('name', '').strip()
    parent_id = request.POST.get('parent_id') or None
    parent    = None
    if parent_id:
        parent = get_object_or_404(Folder, pk=parent_id, owner=request.user)
    if name:
        Folder.objects.get_or_create(owner=request.user, parent=parent, name=name)
        messages.success(request, f'Ordner „{name}" erstellt.')
    if parent:
        return redirect('folder', pk=parent.pk)
    return redirect('dashboard')


# ── Delete folder ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def delete_folder(request, pk):
    folder = get_object_or_404(Folder, pk=pk, owner=request.user)
    parent_pk = folder.parent_id
    folder.delete()
    messages.success(request, 'Ordner gelöscht.')
    if parent_pk:
        return redirect('folder', pk=parent_pk)
    return redirect('dashboard')


# ── Toggle share ──────────────────────────────────────────────────────────────
@login_required
@require_POST
def toggle_share(request, pk):
    cf = get_object_or_404(CloudFile, pk=pk, owner=request.user)
    cf.is_public = not cf.is_public
    cf.save()
    status = 'öffentlich' if cf.is_public else 'privat'
    messages.success(request, f'Datei ist jetzt {status}.')
    if cf.folder_id:
        return redirect('folder', pk=cf.folder_id)
    return redirect('dashboard')


# ── Search ────────────────────────────────────────────────────────────────────
@login_required
def search(request):
    q = request.GET.get('q', '').strip()
    files = []
    if q:
        files = CloudFile.objects.filter(owner=request.user, original_name__icontains=q)
    return render(request, 'cloud/search.html', {'files': files, 'query': q})


# ── JSON API (ohne DRF) ───────────────────────────────────────────────────────

@login_required
@require_POST
def api_upload(request):
    """POST /api/upload/  — multipart, field name: files"""
    uploaded = request.FILES.getlist('files')
    if not uploaded:
        return JsonResponse({'error': 'Keine Dateien übermittelt.'}, status=400)

    folder_id = request.POST.get('folder_id') or None
    folder = None
    if folder_id:
        try:
            folder = Folder.objects.get(pk=folder_id, owner=request.user)
        except Folder.DoesNotExist:
            return JsonResponse({'error': 'Ordner nicht gefunden.'}, status=404)

    result = []
    for f in uploaded:
        mime, _ = mimetypes.guess_type(f.name)
        cf = CloudFile.objects.create(
            owner=request.user, folder=folder,
            original_name=f.name, file=f, size=f.size,
            mime_type=mime or 'application/octet-stream',
        )
        result.append({
            'id': cf.pk,
            'name': cf.original_name,
            'size': cf.size,
            'size_human': cf.size_human,
            'mime_type': cf.mime_type,
            'download_url': f'/download/{cf.pk}/',
            'uploaded_at': cf.uploaded_at.isoformat(),
        })
    return JsonResponse({'uploaded': result}, status=201)


@login_required
@require_GET
def api_files(request):
    """GET /api/files/?folder=<id>  — JSON Dateiliste"""
    folder_id = request.GET.get('folder') or None
    qs = CloudFile.objects.filter(owner=request.user)
    if folder_id == 'root':
        qs = qs.filter(folder=None)
    elif folder_id:
        qs = qs.filter(folder_id=folder_id)
    data = [{
        'id': cf.pk,
        'name': cf.original_name,
        'size_human': cf.size_human,
        'mime_type': cf.mime_type,
        'is_public': cf.is_public,
        'download_url': f'/download/{cf.pk}/',
        'uploaded_at': cf.uploaded_at.isoformat(),
    } for cf in qs]
    return JsonResponse({'files': data})


@login_required
@require_POST
def api_delete(request, pk):
    """POST /api/delete/<id>/"""
    cf = get_object_or_404(CloudFile, pk=pk, owner=request.user)
    cf.delete()
    return JsonResponse({'deleted': True})


# ── Helper ────────────────────────────────────────────────────────────────────
def _humanize(n):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ════════════════════════════════════════════════════════════════════════════
# TOKEN-GESCHÜTZTE API  (für externe Projekte wie JDS-Verein)
# ════════════════════════════════════════════════════════════════════════════
from django.utils import timezone as tz
from django.views.decorators.csrf import csrf_exempt
from .models import ApiToken


def _auth_token(request):
    """
    Liest den Bearer-Token aus dem Authorization-Header.
    Gibt (ApiToken, None) oder (None, JsonResponse-Fehler) zurück.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return None, JsonResponse({'error': 'Authorization-Header fehlt. Format: Bearer <token>'}, status=401)
    raw = auth[7:].strip()
    try:
        token_obj = ApiToken.objects.select_related('user').get(token=raw, aktiv=True)
        token_obj.last_used = tz.now()
        token_obj.save(update_fields=['last_used'])
        return token_obj, None
    except ApiToken.DoesNotExist:
        return None, JsonResponse({'error': 'Ungültiger oder deaktivierter Token.'}, status=403)


@csrf_exempt
def api_token_upload(request):
    """
    POST /api/v1/upload/
    Token-geschützter Datei-Upload für externe Apps (z.B. JDS-Verein).

    Header:
        Authorization: Bearer <token>
        Content-Type:  multipart/form-data

    Felder:
        files          – eine oder mehrere Dateien (required)
        folder_name    – Ordnername (optional, wird auto-erstellt)
        verein_id      – Verein-PK aus dem Quell-Projekt (optional)
        verein_name    – Vereinsname (optional)
        kontext        – z.B. "satzung", "beleg", "protokoll" (optional)
        ref_id         – PK des Quell-Objekts (optional)
        is_public      – "true" / "false" (optional, default false)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Nur POST erlaubt.'}, status=405)

    token_obj, err = _auth_token(request)
    if err:
        return err

    owner = token_obj.user
    files = request.FILES.getlist('files') or ([request.FILES['file']] if 'file' in request.FILES else [])

    if not files:
        return JsonResponse({'error': 'Keine Dateien übermittelt. Feld: files'}, status=400)

    # Optionale Metadaten
    folder_name    = request.POST.get('folder_name', '').strip()
    verein_id      = request.POST.get('verein_id') or token_obj.verein_id
    verein_name    = request.POST.get('verein_name', '') or token_obj.verein_name
    kontext        = request.POST.get('kontext', '').strip()
    ref_id         = request.POST.get('ref_id') or None
    is_public      = request.POST.get('is_public', 'false').lower() == 'true'

    # Ordner anlegen/finden
    folder = None
    if folder_name:
        folder, _ = Folder.objects.get_or_create(
            owner=owner, parent=None, name=folder_name
        )

    uploaded = []
    for f in files:
        mime, _ = mimetypes.guess_type(f.name)
        cf = CloudFile.objects.create(
            owner=owner,
            folder=folder,
            original_name=f.name,
            file=f,
            size=f.size,
            mime_type=mime or 'application/octet-stream',
            is_public=is_public,
            source_app='jds-verein',
            source_verein_id=int(verein_id) if verein_id else None,
            source_verein_name=verein_name,
            source_kontext=kontext,
            source_ref_id=int(ref_id) if ref_id else None,
        )
        result = {
            'id':           cf.pk,
            'name':         cf.original_name,
            'size':         cf.size,
            'size_human':   cf.size_human,
            'mime_type':    cf.mime_type,
            'kontext':      cf.source_kontext,
            'uploaded_at':  cf.uploaded_at.isoformat(),
            'download_url': request.build_absolute_uri(f'/download/{cf.pk}/'),
        }
        if is_public:
            result['public_url'] = request.build_absolute_uri(f'/public/{cf.public_token}/')
        uploaded.append(result)

    return JsonResponse({'uploaded': uploaded, 'count': len(uploaded)}, status=201)


@csrf_exempt
def api_token_files(request):
    """
    GET /api/v1/files/
    Dateien eines Tokens auflisten (nur eigene).

    Header:
        Authorization: Bearer <token>

    Query-Parameter:
        verein_id  – Nur Dateien dieses Vereins
        kontext    – Nur Dateien dieses Kontexts (z.B. "beleg")
        ref_id     – Nur Dateien dieses Quell-Objekts
        folder     – Ordner-PK oder "root"
        search     – Suche im Dateinamen
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Nur GET erlaubt.'}, status=405)

    token_obj, err = _auth_token(request)
    if err:
        return err

    qs = CloudFile.objects.filter(owner=token_obj.user)

    # Filter
    vid = request.GET.get('verein_id')
    if vid:
        qs = qs.filter(source_verein_id=vid)

    kontext = request.GET.get('kontext')
    if kontext:
        qs = qs.filter(source_kontext=kontext)

    ref_id = request.GET.get('ref_id')
    if ref_id:
        qs = qs.filter(source_ref_id=ref_id)

    folder = request.GET.get('folder')
    if folder == 'root':
        qs = qs.filter(folder=None)
    elif folder:
        qs = qs.filter(folder_id=folder)

    search = request.GET.get('search', '')
    if search:
        qs = qs.filter(original_name__icontains=search)

    data = []
    for cf in qs:
        item = {
            'id':           cf.pk,
            'name':         cf.original_name,
            'size_human':   cf.size_human,
            'mime_type':    cf.mime_type,
            'kontext':      cf.source_kontext,
            'ref_id':       cf.source_ref_id,
            'verein_id':    cf.source_verein_id,
            'verein_name':  cf.source_verein_name,
            'is_public':    cf.is_public,
            'uploaded_at':  cf.uploaded_at.isoformat(),
            'download_url': request.build_absolute_uri(f'/download/{cf.pk}/'),
        }
        if cf.is_public:
            item['public_url'] = request.build_absolute_uri(f'/public/{cf.public_token}/')
        data.append(item)

    return JsonResponse({'files': data, 'count': len(data)})


@csrf_exempt
def api_token_delete(request, pk):
    """
    DELETE /api/v1/files/<pk>/
    Datei löschen (nur eigene Dateien).
    """
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Nur DELETE erlaubt.'}, status=405)

    token_obj, err = _auth_token(request)
    if err:
        return err

    cf = get_object_or_404(CloudFile, pk=pk, owner=token_obj.user)
    name = cf.original_name
    cf.delete()
    return JsonResponse({'deleted': True, 'name': name})


@csrf_exempt
def api_token_info(request):
    """
    GET /api/v1/info/
    Token-Infos + Speicherstatistik.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Nur GET erlaubt.'}, status=405)

    token_obj, err = _auth_token(request)
    if err:
        return err

    from django.db.models import Sum, Count
    stats = CloudFile.objects.filter(owner=token_obj.user).aggregate(
        total_files=Count('id'), total_bytes=Sum('size')
    )
    return JsonResponse({
        'token_name':   token_obj.name,
        'username':     token_obj.user.username,
        'verein_id':    token_obj.verein_id,
        'verein_name':  token_obj.verein_name,
        'total_files':  stats['total_files'] or 0,
        'total_bytes':  stats['total_bytes'] or 0,
        'total_human':  _humanize(stats['total_bytes'] or 0),
    })


# ── Token-Verwaltung (Dashboard) ──────────────────────────────────────────────
@login_required
def token_verwaltung(request):
    """Eigene API-Tokens anlegen und verwalten."""
    if request.method == 'POST':
        aktion = request.POST.get('aktion')

        if aktion == 'erstellen':
            name = request.POST.get('name', '').strip()
            verein_id   = request.POST.get('verein_id') or None
            verein_name = request.POST.get('verein_name', '').strip()
            if name:
                t = ApiToken.objects.create(
                    user=request.user,
                    name=name,
                    verein_id=int(verein_id) if verein_id else None,
                    verein_name=verein_name,
                )
                messages.success(request, f'Token „{name}" erstellt: {t.token}')
            else:
                messages.error(request, 'Name ist erforderlich.')

        elif aktion == 'deaktivieren':
            pk = request.POST.get('pk')
            ApiToken.objects.filter(pk=pk, user=request.user).update(aktiv=False)
            messages.success(request, 'Token deaktiviert.')

        elif aktion == 'loeschen':
            pk = request.POST.get('pk')
            ApiToken.objects.filter(pk=pk, user=request.user).delete()
            messages.success(request, 'Token gelöscht.')

        return redirect('token_verwaltung')

    tokens = ApiToken.objects.filter(user=request.user)
    return render(request, 'cloud/token_verwaltung.html', {'tokens': tokens})
