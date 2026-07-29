import csv
import io
import json

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_GET

from .models import Category, Note

MAX_PAGES = 10
CSV_NOTE_FIELDS = ['title', 'category', 'num_pages', 'created_at', 'updated_at'] + \
                   [f'content{i}' for i in range(1, MAX_PAGES + 1)]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _json_body(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return {}


def _natural_key(value):
    import re
    return [int(chunk) if chunk.isdigit() else chunk.lower()
            for chunk in re.split(r'(\d+)', value or '')]


def _note_summary(note):
    # plain-text-ish snippet from the first page for the list view
    import re
    text = re.sub('<[^<]+?>', ' ', note.content1 or '')
    text = ' '.join(text.split())
    snippet = text[:180]
    return {
        'id': note.id,
        'title': note.title,
        'snippet': snippet,
        'category': note.category,
        'num_pages': note.num_pages,
        'created_at': note.created_at.isoformat(),
        'updated_at': note.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

@ensure_csrf_cookie
def auth_view(request):
    if request.user.is_authenticated:
        return redirect('notes_list')
    return render(request, 'notes/auth.html')


@require_POST
def signup_api(request):
    data = _json_body(request)
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return JsonResponse({'ok': False, 'error': 'Username and password are required.'}, status=400)
    if len(password) < 6:
        return JsonResponse({'ok': False, 'error': 'Password must be at least 6 characters.'}, status=400)
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'ok': False, 'error': 'That username is already taken.'}, status=400)

    try:
        user = User.objects.create_user(username=username, email=email, password=password)
    except IntegrityError:
        return JsonResponse({'ok': False, 'error': 'Could not create account.'}, status=400)

    return JsonResponse({'ok': True, 'username': user.username})


@require_POST
def login_api(request):
    data = _json_body(request)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    remember = bool(data.get('remember'))

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'ok': False, 'error': 'Invalid username or password.'}, status=400)

    login(request, user)
    if remember:
        # Persistent cookie: survives closing the browser, expires after
        # SESSION_COOKIE_AGE (see settings.py).
        request.session.set_expiry(None)
    else:
        # Browser-session cookie: Django/the browser discards it when the
        # browser closes, so the user has to log in again next time.
        request.session.set_expiry(0)
    return JsonResponse({'ok': True, 'username': user.username, 'token': request.session.session_key})


def logout_view(request):
    logout(request)
    return redirect('auth')


def session_check_api(request):
    # Deliberately not @login_required: that decorator redirects on failure,
    # which the login page can't use to safely decide whether to redirect
    # itself. This always answers with plain JSON instead.
    if request.user.is_authenticated:
        return JsonResponse({'ok': True, 'username': request.user.username})
    return JsonResponse({'ok': False}, status=401)


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

@login_required(login_url='/')
def notes_list_view(request):
    return render(request, 'notes/notes_list.html')


@login_required(login_url='/')
def note_create_view(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'notes/note_create.html', {'categories': categories})


@login_required(login_url='/')
def note_detail_view(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    categories = Category.objects.filter(user=request.user)
    pages = []
    for i in range(1, note.num_pages + 1):
        pages.append({'number': i, 'content': note.get_page_content(i)})
    context = {
        'note': note,
        'pages': pages,
        'categories': categories,
        'max_pages': MAX_PAGES,
    }
    return render(request, 'notes/note_detail.html', context)


@login_required(login_url='/')
def settings_view(request):
    return render(request, 'notes/settings.html')


# ---------------------------------------------------------------------------
# notes fetch (search + category filter + sort) -- single view
# ---------------------------------------------------------------------------

SORT_MAP = {
    'created_asc': ['created_at'],
    'created_desc': ['-created_at'],
    'updated_asc': ['updated_at'],
    'updated_desc': ['-updated_at'],
}


@login_required(login_url='/')
@require_GET
def notes_fetch_api(request):
    q = (request.GET.get('q') or '').strip()
    category = (request.GET.get('category') or '').strip()
    sort = (request.GET.get('sort') or 'title_asc').strip()

    qs = Note.objects.filter(user=request.user)

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(content1__icontains=q)
            | Q(content2__icontains=q)
            | Q(content3__icontains=q)
            | Q(content4__icontains=q)
            | Q(content5__icontains=q)
            | Q(content6__icontains=q)
            | Q(content7__icontains=q)
            | Q(content8__icontains=q)
            | Q(content9__icontains=q)
            | Q(content10__icontains=q)
        )

    if category:
        qs = qs.filter(category=category)

    if sort in ('title_asc', 'title_desc'):
        # natural sort (so "Note 2" comes before "Note 10"), done in Python
        # since sqlite has no built-in natural ordering.
        notes_list = list(qs)
        notes_list.sort(key=lambda n: _natural_key(n.title), reverse=(sort == 'title_desc'))
    else:
        order_fields = SORT_MAP.get(sort, ['title'])
        notes_list = list(qs.order_by(*order_fields))

    notes = [_note_summary(n) for n in notes_list]
    return JsonResponse({'ok': True, 'notes': notes, 'count': len(notes)})


# ---------------------------------------------------------------------------
# note CRUD api
# ---------------------------------------------------------------------------

@login_required(login_url='/')
@require_POST
def note_create_api(request):
    data = _json_body(request)
    title = (data.get('title') or '').strip() or 'Untitled Note'
    category = (data.get('category') or '').strip()
    content = data.get('content') or ''

    note = Note.objects.create(
        user=request.user,
        title=title,
        content1=content,
        category=category,
        num_pages=1,
    )
    return JsonResponse({'ok': True, 'id': note.id})


@login_required(login_url='/')
@require_POST
def note_delete_api(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    note.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/')
@require_POST
def note_update_title_api(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    data = _json_body(request)
    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'ok': False, 'error': 'Title cannot be empty.'}, status=400)
    note.title = title
    note.save(update_fields=['title', 'updated_at'])
    return JsonResponse({'ok': True, 'title': note.title})


@login_required(login_url='/')
@require_POST
def note_update_category_api(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    data = _json_body(request)
    category = (data.get('category') or '').strip()
    note.category = category
    note.save(update_fields=['category', 'updated_at'])
    return JsonResponse({'ok': True, 'category': note.category})


@login_required(login_url='/')
@require_POST
def note_page_update_api(request, note_id, page_number):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if page_number < 1 or page_number > note.num_pages:
        return JsonResponse({'ok': False, 'error': 'Invalid page.'}, status=400)
    data = _json_body(request)
    content = data.get('content', '')
    note.set_page_content(page_number, content)
    note.save()
    return JsonResponse({'ok': True, 'updated_at': note.updated_at.isoformat()})


@login_required(login_url='/')
@require_POST
def note_page_add_api(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if note.num_pages >= MAX_PAGES:
        return JsonResponse({'ok': False, 'error': f'Maximum of {MAX_PAGES} pages reached.'}, status=400)
    note.num_pages += 1
    note.set_page_content(note.num_pages, '')
    note.save()
    return JsonResponse({'ok': True, 'page_number': note.num_pages, 'num_pages': note.num_pages})


@login_required(login_url='/')
@require_POST
def note_page_delete_api(request, note_id, page_number):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if note.num_pages <= 1:
        return JsonResponse({'ok': False, 'error': 'A note must have at least one page.'}, status=400)
    if page_number < 1 or page_number > note.num_pages:
        return JsonResponse({'ok': False, 'error': 'Invalid page.'}, status=400)

    # shift subsequent page contents down to fill the gap
    contents = [note.get_page_content(i) for i in range(1, note.num_pages + 1)]
    del contents[page_number - 1]
    contents.append('')

    for i in range(1, MAX_PAGES + 1):
        note.set_page_content(i, contents[i - 1] if i - 1 < len(contents) else '')

    note.num_pages -= 1
    note.save()
    return JsonResponse({'ok': True, 'num_pages': note.num_pages})


# ---------------------------------------------------------------------------
# categories api
# ---------------------------------------------------------------------------

@login_required(login_url='/')
def categories_api(request):
    if request.method == 'GET':
        cats = list(Category.objects.filter(user=request.user).values('id', 'name'))
        return JsonResponse({'ok': True, 'categories': cats})

    if request.method == 'POST':
        data = _json_body(request)
        name = (data.get('name') or '').strip()
        if not name:
            return JsonResponse({'ok': False, 'error': 'Category name cannot be empty.'}, status=400)
        if len(name) > 100:
            return JsonResponse({'ok': False, 'error': 'Category name is too long.'}, status=400)
        cat, created = Category.objects.get_or_create(user=request.user, name=name)
        if not created:
            return JsonResponse({'ok': False, 'error': 'Category already exists.'}, status=400)
        return JsonResponse({'ok': True, 'category': {'id': cat.id, 'name': cat.name}})

    return HttpResponseNotAllowed(['GET', 'POST'])


@login_required(login_url='/')
@require_POST
def category_delete_api(request, category_id):
    cat = get_object_or_404(Category, id=category_id, user=request.user)
    name = cat.name
    cat.delete()
    # Notes keep their category text (plain text field) even after the
    # category record is removed, by design.
    return JsonResponse({'ok': True, 'name': name})


# ---------------------------------------------------------------------------
# account management (settings page)
# ---------------------------------------------------------------------------

@login_required(login_url='/')
@require_POST
def change_password_api(request):
    data = _json_body(request)
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''
    confirm_password = data.get('confirm_password') or ''

    if not request.user.check_password(current_password):
        return JsonResponse({'ok': False, 'error': 'Current password is incorrect.'}, status=400)
    if len(new_password) < 6:
        return JsonResponse({'ok': False, 'error': 'Password must be at least 6 characters.'}, status=400)
    if new_password != confirm_password:
        return JsonResponse({'ok': False, 'error': 'Passwords do not match.'}, status=400)

    request.user.set_password(new_password)
    request.user.save()
    # Keep the current session valid after the password hash changes.
    update_session_auth_hash(request, request.user)
    return JsonResponse({'ok': True})


@login_required(login_url='/')
@require_GET
def export_notes_api(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="notex_export.csv"'

    writer = csv.writer(response)

    category_names = list(
        Category.objects.filter(user=request.user).order_by('name').values_list('name', flat=True)
    )
    writer.writerow(category_names)
    writer.writerow([])
    writer.writerow(CSV_NOTE_FIELDS)

    for note in Note.objects.filter(user=request.user).order_by('id'):
        row = [note.title, note.category, note.num_pages,
               note.created_at.isoformat(), note.updated_at.isoformat()]
        row += [note.get_page_content(i) for i in range(1, MAX_PAGES + 1)]
        writer.writerow(row)

    return response


def _parse_csv_datetime(value):
    value = (value or '').strip()
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt


@login_required(login_url='/')
@require_POST
def import_notes_api(request):
    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'ok': False, 'error': 'No file was uploaded.'}, status=400)

    keep_original_dates = (request.POST.get('import_original_dates') or '').lower() in ('true', '1', 'on')

    try:
        text = upload.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return JsonResponse({'ok': False, 'error': 'Could not read the file. Please upload a UTF-8 CSV.'}, status=400)

    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 3:
        return JsonResponse({'ok': False, 'error': 'This does not look like a NoteX export file.'}, status=400)

    category_row = rows[0]
    note_rows = rows[3:]  # row 1 = categories, row 2 = blank, row 3 = header

    categories_imported = 0
    for name in category_row:
        name = name.strip()
        if not name:
            continue
        _, created = Category.objects.get_or_create(user=request.user, name=name)
        if created:
            categories_imported += 1

    notes_imported = 0
    for row in note_rows:
        if len(row) < 5:
            continue  # skip malformed / short rows

        title = (row[0] or 'Untitled Note').strip() or 'Untitled Note'
        category = (row[1] or '').strip()
        try:
            num_pages = max(1, min(MAX_PAGES, int(row[2])))
        except (ValueError, IndexError):
            num_pages = 1

        contents = row[5:5 + MAX_PAGES]
        contents += [''] * (MAX_PAGES - len(contents))

        note = Note.objects.create(
            user=request.user,
            title=title,
            category=category,
            num_pages=num_pages,
            **{f'content{i}': contents[i - 1] for i in range(1, MAX_PAGES + 1)},
        )

        if keep_original_dates:
            created_at = _parse_csv_datetime(row[3] if len(row) > 3 else '') or timezone.now()
            updated_at = _parse_csv_datetime(row[4] if len(row) > 4 else '') or created_at
            # auto_now_add/auto_now always override on save(), so force the
            # original timestamps with a direct update() afterwards.
            Note.objects.filter(pk=note.pk).update(created_at=created_at, updated_at=updated_at)

        notes_imported += 1

    return JsonResponse({'ok': True, 'notes_imported': notes_imported, 'categories_imported': categories_imported})


@login_required(login_url='/')
@require_POST
def delete_all_notes_api(request):
    data = _json_body(request)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user_check = authenticate(request, username=username, password=password)
    if user_check is None or user_check.pk != request.user.pk:
        return JsonResponse({'ok': False, 'error': 'Username or password is incorrect.'}, status=400)

    Note.objects.filter(user=request.user).delete()
    Category.objects.filter(user=request.user).delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/')
@require_POST
def delete_account_api(request):
    data = _json_body(request)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    user_check = authenticate(request, username=username, password=password)
    if user_check is None or user_check.pk != request.user.pk:
        return JsonResponse({'ok': False, 'error': 'Username or password is incorrect.'}, status=400)

    user = request.user
    logout(request)
    user.delete()  # cascades to Notes and Categories via on_delete=CASCADE
    return JsonResponse({'ok': True})