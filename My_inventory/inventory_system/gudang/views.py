import json
import csv
from django.db import transaction as db_transaction
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Product, Transaction, ActivityLog, StockMovement
from .decorators import staff_required, manager_or_staff_required
from django.template.loader import get_template
from xhtml2pdf import pisa


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def log_action(user, action, details):
    """Mencatat aktivitas user ke dalam database ActivityLog."""
    if user.is_authenticated:
        ActivityLog.objects.create(user=user, action=action, details=details)


# FIX #5: record_movement now requires qty_before to be passed explicitly,
# instead of calculating it backwards from the already-saved product.quantity.
def record_movement(product, movement_type, quantity, qty_before, performed_by, reference='', note=''):
    StockMovement.objects.create(
        product       = product,
        movement_type = movement_type,
        quantity      = abs(quantity),
        qty_before    = qty_before,
        qty_after     = product.quantity,  # product.quantity is already updated by caller
        reference     = reference,
        note          = note,
        performed_by  = performed_by,
    )


def _get_changed_fields(old_obj, new_data):
    field_map = {
        'preOrderNumber': ('pre_order_number', 'Pre-Order No'),
        'partNumber':     ('part_number',       'Part Number'),
        'productCode':    ('product_code',       'Product Code'),
        'awb':            ('awb',                'AWB'),
        'description':    ('description',        'Description'),
        'quantity':       ('quantity',           'Quantity'),
        'category':       ('category',           'Category'),
        'platform':       ('platform',           'Platform'),
        'location':       ('location',           'Location'),
    }
    changes = []
    for json_key, (model_field, label) in field_map.items():
        new_val = new_data.get(json_key)
        if new_val is None:
            continue
        old_val = getattr(old_obj, model_field, None)
        if model_field == 'quantity':
            try:
                new_val = int(new_val)
            except (ValueError, TypeError):
                continue
        else:
            new_val = str(new_val).strip()
            old_val = str(old_val).strip() if old_val is not None else ''
        if str(old_val) != str(new_val):
            changes.append(f"{label}: '{old_val}' → '{new_val}'")
    return ' | '.join(changes) if changes else 'No changes detected'


def _get_csrf_cookie(request):
    from django.middleware.csrf import get_token
    return get_token(request)


# ---------------------------------------------------------------------------
# MAIN VIEW
# ---------------------------------------------------------------------------

@login_required
def index(request):
    profile = getattr(request.user, 'profile', None)
    context = {
        'user_role':              profile.role                   if profile else 'staff',
        'can_edit_stock':         profile.can_edit_stock         if profile else False,
        'can_delete_stock':       profile.can_delete_stock       if profile else False,
        'can_create_surat_jalan': profile.can_create_surat_jalan if profile else False,
        'can_bulk_import':        profile.can_bulk_import        if profile else False,
    }
    return render(request, 'index.html', context)


# ---------------------------------------------------------------------------
# API: READ DATA
# ---------------------------------------------------------------------------

@login_required
@manager_or_staff_required
def get_products(request):
    products = list(Product.objects.values(
        'id', 'pre_order_number', 'part_number', 'serial_number',
        'product_code', 'description', 'quantity', 'category',
        'platform', 'location', 'awb', 'date_added',
    ).order_by('part_number'))
    return JsonResponse(products, safe=False)


@login_required
@manager_or_staff_required
def get_transactions(request):
    # FIX #2: Added the rollback fields that now exist on the Transaction model
    qs = Transaction.objects.values(
        'sdr_no', 'project_name', 'recipient', 'created_at',
        'items_json', 'request_date', 'requestor', 'telephone',
        'pic_at_site', 'pic_mobile', 'subsystem', 'site_name',
        'transport_mode', 'address', 'is_rolled_back',
        'rolled_back_at', 'rollback_note',
    ).order_by('-created_at')

    data = []
    for trx in qs:
        trx['created_at'] = trx['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        for field in ('request_date', 'requestor', 'telephone', 'pic_at_site',
                      'pic_mobile', 'subsystem', 'site_name', 'transport_mode', 'address'):
            trx[field] = trx[field] or ''
        if trx.get('rolled_back_at'):
            trx['rolled_back_at'] = trx['rolled_back_at'].strftime('%Y-%m-%d %H:%M:%S')
        data.append(trx)
    return JsonResponse(data, safe=False)


@login_required
@manager_or_staff_required
def get_activity_logs(request):
    try:
        limit = min(int(request.GET.get('limit', 200)), 1000)
    except (ValueError, TypeError):
        limit = 200

    logs = ActivityLog.objects.select_related('user').order_by('-timestamp')[:limit]
    data = [
        {
            'user':      log.user.username if log.user else 'Unknown',
            'action':    log.action,
            'details':   log.details,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for log in logs
    ]
    return JsonResponse(data, safe=False)


# ---------------------------------------------------------------------------
# API: STOCK MOVEMENT HISTORY
# ---------------------------------------------------------------------------

@login_required
@manager_or_staff_required
def get_stock_movements(request):
    try:
        limit = min(int(request.GET.get('limit', 200)), 1000)
    except (ValueError, TypeError):
        limit = 200

    qs = StockMovement.objects.select_related('product', 'performed_by').order_by('-timestamp')

    serial = request.GET.get('serial', '').strip()
    if serial:
        qs = qs.filter(product__serial_number=serial)

    move_type = request.GET.get('type', '').strip().upper()
    # FIX #7: Added 'ROLLBACK' as a valid filter option
    if move_type in ('IN', 'OUT', 'ADJUST', 'ROLLBACK'):
        qs = qs.filter(movement_type=move_type)

    qs = qs[:limit]

    data = [
        {
            'id':             m.id,
            'serial_number':  m.product.serial_number,
            'part_number':    m.product.part_number,
            'movement_type':  m.movement_type,
            'movement_label': m.get_movement_type_display(),
            'quantity':       m.quantity,
            'qty_before':     m.qty_before,
            'qty_after':      m.qty_after,
            'reference':      m.reference,
            'note':           m.note,
            'performed_by':   m.performed_by.username if m.performed_by else 'System',
            'timestamp':      m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'serial_number':  m.product.serial_number,   # ← ADD THIS
            'part_number':    m.product.part_number,     # ← ADD THIS
        }
        for m in qs
    ]
    return JsonResponse(data, safe=False)


@login_required
@manager_or_staff_required
def get_product_movement_summary(request, serial_number):
    product   = get_object_or_404(Product, serial_number=serial_number)
    movements = StockMovement.objects.filter(product=product).order_by('-timestamp')

    total_in     = sum(m.quantity for m in movements if m.movement_type == 'IN')
    total_out    = sum(m.quantity for m in movements if m.movement_type == 'OUT')
    total_adjust = sum(m.quantity for m in movements if m.movement_type == 'ADJUST')

    history = [
        {
            'id':             m.id,
            'serial_number':  m.product.serial_number,   # ← FIX: was missing
            'part_number':    m.product.part_number,     # ← FIX: was missing
            'movement_type':  m.movement_type,
            'movement_label': m.get_movement_type_display(),
            'quantity':       m.quantity,
            'qty_before':     m.qty_before,
            'qty_after':      m.qty_after,
            'reference':      m.reference,
            'note':           m.note,
            'is_rolled_back': getattr(m, 'is_rolled_back', False),  # ← FIX: needed for undo button
            'performed_by':   m.performed_by.username if m.performed_by else 'System',
            'timestamp':      m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for m in movements
    ]

    return JsonResponse({
        'product': {
            'serial_number': product.serial_number,
            'part_number':   product.part_number,
            'description':   product.description,
            'current_qty':   product.quantity,
            'location':      product.location,
        },
        'summary': {
            'total_in':     total_in,
            'total_out':    total_out,
            'total_adjust': total_adjust,
        },
        'history': history,
    })


# ---------------------------------------------------------------------------
# API: MANUAL STOCK ADJUSTMENT
# ---------------------------------------------------------------------------

@csrf_exempt
@login_required
@staff_required
def adjust_stock(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data       = json.loads(request.body)
        serial     = data.get('serialNumber', '').strip()
        adjustment = data.get('adjustment')
        note       = data.get('note', '').strip()

        if not serial:
            return JsonResponse({'status': 'error', 'message': 'Serial Number wajib diisi.'})
        if adjustment is None:
            return JsonResponse({'status': 'error', 'message': 'Field "adjustment" wajib diisi.'})

        try:
            adjustment = int(adjustment)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Adjustment harus berupa angka.'})

        if adjustment == 0:
            return JsonResponse({'status': 'error', 'message': 'Adjustment tidak boleh 0.'})

        product    = Product.objects.get(serial_number=serial)
        qty_before = product.quantity
        new_qty    = qty_before + adjustment

        if new_qty < 0:
            return JsonResponse({
                'status':  'error',
                'message': f'Stok tidak boleh negatif. Stok sekarang: {qty_before}, adjustment: {adjustment}.',
            })

        product.quantity = new_qty
        product.save()

        StockMovement.objects.create(
            product       = product,
            movement_type = 'ADJUST',
            quantity      = adjustment,
            qty_before    = qty_before,
            qty_after     = new_qty,
            reference     = 'Manual Adjustment',
            note          = note or 'No reason provided',
            performed_by  = request.user,
        )

        direction = f"+{adjustment}" if adjustment > 0 else str(adjustment)
        log_action(
            request.user, 'ADJUST',
            f"Stock Adjustment | SN: {serial} | {product.part_number} | "
            f"Delta: {direction} | {qty_before} → {new_qty} | Reason: {note or 'N/A'}",
        )

        return JsonResponse({
            'status':     'success',
            'message':    f'Stok diperbarui: {qty_before} → {new_qty}',
            'qty_before': qty_before,
            'qty_after':  new_qty,
        })

    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Produk tidak ditemukan.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ---------------------------------------------------------------------------
# API: WRITE DATA
# ---------------------------------------------------------------------------

@csrf_exempt
@login_required
@staff_required
def add_product(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data   = json.loads(request.body)
        serial = data.get('serialNumber', '').strip()
        part   = data.get('partNumber',   '').strip()

        if not serial or not part:
            return JsonResponse({'status': 'error', 'message': 'Part Number dan Serial Number wajib diisi.'})

        if Product.objects.filter(serial_number=serial).exists():
            return JsonResponse({'status': 'error', 'message': f'Serial Number "{serial}" sudah ada!'})

        qty_raw = data.get('quantity')
        qty_val = int(qty_raw) if qty_raw not in [None, ''] else 0

        product = Product.objects.create(
            pre_order_number = data.get('preOrderNumber', ''),
            part_number      = part,
            serial_number    = serial,
            product_code     = data.get('productCode', ''),
            awb              = data.get('awb', ''),
            description      = data.get('description', ''),
            quantity         = qty_val,
            category         = data.get('category', ''),
            platform         = data.get('platform', ''),
            location         = data.get('location', ''),
        )

        if qty_val > 0:
            StockMovement.objects.create(
                product       = product,
                movement_type = 'IN',
                quantity      = qty_val,
                qty_before    = 0,
                qty_after     = qty_val,
                reference     = 'Initial Stock',
                note          = 'Product added to inventory',
                performed_by  = request.user,
            )

        log_action(
            request.user, 'ADD',
            f"Added Product: {part} | SN: {serial} | "
            f"Qty: {qty_val} | Location: {data.get('location', '-') or '-'} | "
            f"Category: {data.get('category', '-') or '-'}",
        )
        return JsonResponse({'status': 'success', 'message': 'Produk berhasil disimpan!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@login_required
@staff_required
def edit_product(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data    = json.loads(request.body)
        serial  = data.get('serialNumber', '').strip()
        product = Product.objects.get(serial_number=serial)
        changes = _get_changed_fields(product, data)
        old_qty = product.quantity

        product.pre_order_number = data.get('preOrderNumber', product.pre_order_number)
        product.part_number      = data.get('partNumber',     product.part_number)
        product.product_code     = data.get('productCode',    product.product_code)
        product.awb              = data.get('awb',            product.awb)
        product.description      = data.get('description',    product.description)
        product.category         = data.get('category',       product.category)
        product.platform         = data.get('platform',       product.platform)
        product.location         = data.get('location',       product.location)

        qty_raw = data.get('quantity')
        if qty_raw not in [None, '']:
            product.quantity = int(qty_raw)

        new_qty = product.quantity

        # FIX #9: Wrap product save + StockMovement creation in atomic block
        # so both succeed or both fail together.
        with db_transaction.atomic():
            product.save()

            if new_qty != old_qty:
                delta = new_qty - old_qty
                StockMovement.objects.create(
                    product       = product,
                    movement_type = 'ADJUST',
                    quantity      = delta,
                    qty_before    = old_qty,
                    qty_after     = new_qty,
                    reference     = 'Edit Product',
                    note          = f'Quantity changed via product edit ({old_qty} → {new_qty})',
                    performed_by  = request.user,
                )

        log_action(request.user, 'EDIT', f"Edited Product SN: {serial} | Changes: {changes}")
        return JsonResponse({'status': 'success', 'message': 'Produk berhasil diupdate!'})

    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Produk tidak ditemukan.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@login_required
@staff_required
def delete_product(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data   = json.loads(request.body)
        serial = data.get('serialNumber', '').strip()

        try:
            product  = Product.objects.get(serial_number=serial)
            part     = product.part_number
            qty      = product.quantity
            location = product.location or '-'
        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Produk tidak ditemukan.'})

        product.delete()

        log_action(
            request.user, 'DELETE',
            f"Deleted Product: {part} | SN: {serial} | "
            f"Last Qty: {qty} | Last Location: {location}",
        )
        return JsonResponse({'status': 'success', 'message': 'Produk dihapus.'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@login_required
@staff_required
def add_transaction(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data  = json.loads(request.body)
        items = data.get('items', [])

        if not items:
            return JsonResponse({'status': 'error', 'message': 'Tidak ada item yang dipilih.'})

        sdr_no       = data.get('sdrNo', '-')
        project_name = data.get('projectName', '-')

        # FIX #6: Use select_for_update() inside the atomic block to prevent
        # race conditions between the stock check and the deduction.
        with db_transaction.atomic():
            serials  = [item.get('serialNumber', '') for item in items]
            products = {
                p.serial_number: p
                for p in Product.objects.select_for_update().filter(serial_number__in=serials)
            }

            # Validate all stock levels before making any changes
            for item in items:
                serial     = item.get('serialNumber', '')
                qty_keluar = int(item.get('quantity', 0))
                product    = products.get(serial)

                if not product:
                    return JsonResponse({'status': 'error', 'message': f'Barang SN: {serial} tidak ditemukan!'})

                if product.quantity < qty_keluar:
                    return JsonResponse({
                        'status':  'error',
                        'message': (
                            f'Gagal! Stok {product.part_number} (SN: {serial}) '
                            f'hanya sisa {product.quantity}, tapi ditarik {qty_keluar}.'
                        ),
                    })

            Transaction.objects.create(
                sdr_no         = sdr_no,
                project_name   = project_name,
                recipient      = data.get('recipient', ''),
                items_json     = json.dumps(items),
                request_date   = data.get('requestDate', ''),
                requestor      = data.get('requestor', ''),
                telephone      = data.get('telephone', ''),
                pic_at_site    = data.get('picAtSite', ''),
                pic_mobile     = data.get('picMobile', ''),
                subsystem      = data.get('subsystem', ''),
                site_name      = data.get('siteName', ''),
                transport_mode = data.get('transportMode', ''),
                address        = data.get('address', ''),
            )

            for item in items:
                serial     = item.get('serialNumber', '')
                qty_keluar = int(item.get('quantity', 0))
                product    = products[serial]
                qty_before = product.quantity

                product.quantity -= qty_keluar
                product.save()

                StockMovement.objects.create(
                    product       = product,
                    movement_type = 'OUT',
                    quantity      = qty_keluar,
                    qty_before    = qty_before,
                    qty_after     = product.quantity,
                    reference     = sdr_no,
                    note          = f"Surat Jalan {sdr_no} | Project: {project_name}",
                    performed_by  = request.user,
                )

                log_action(
                    request.user, 'WITHDRAW',
                    f"Surat Jalan {sdr_no} | Project: {project_name} | "
                    f"Item: {product.part_number} (SN: {serial}) | "
                    f"Qty Withdrawn: {qty_keluar} | Stock: {qty_before} → {product.quantity}",
                )

        log_action(
            request.user, 'WITHDRAW_SUMMARY',
            f"Surat Jalan {sdr_no} created for '{project_name}' | "
            f"Recipient: {data.get('recipient', '-')} | "
            f"Site: {data.get('siteName', '-')} | Total Items: {len(items)}",
        )
        return JsonResponse({'status': 'success', 'message': 'Surat Jalan berhasil dibuat!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ---------------------------------------------------------------------------
# CRITICAL FIX (#2 in review): edit_transaction previously only had
# @login_required, allowing ANY authenticated user (including Manager-role
# accounts, which are meant to be view + export PDF only) to edit a Surat
# Jalan and trigger stock corrections via ADJUST movements.
#
# This view mutates Product.quantity and creates StockMovement rows, so it
# is now gated the same way as add_transaction / adjust_stock: staff only
# (superusers always pass via role_required).
# ---------------------------------------------------------------------------
@csrf_exempt
@login_required
@staff_required
def edit_transaction(request):
    """
    Full edit of a Surat Jalan.
    Reverses old stock deductions, validates new ones, applies corrections atomically.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data      = json.loads(request.body)
        sdr_no    = data.get('sdrNo', '').strip()
        new_items = data.get('items', [])

        if not sdr_no:
            return JsonResponse({'status': 'error', 'message': 'SDR No wajib diisi.'})
        if not new_items:
            return JsonResponse({'status': 'error', 'message': 'Minimal satu item harus ada.'})

        try:
            trx = Transaction.objects.get(sdr_no=sdr_no)
        except Transaction.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Surat Jalan {sdr_no} tidak ditemukan.'})

        old_items = json.loads(trx.items_json)

        old_qty_map = {}
        for item in old_items:
            sn = item.get('serialNumber', '')
            old_qty_map[sn] = old_qty_map.get(sn, 0) + int(item.get('quantity', 0))

        new_qty_map = {}
        for item in new_items:
            sn = item.get('serialNumber', '')
            new_qty_map[sn] = new_qty_map.get(sn, 0) + int(item.get('quantity', 0))

        all_serials = set(old_qty_map) | set(new_qty_map)
        products    = {p.serial_number: p for p in Product.objects.filter(serial_number__in=all_serials)}

        net_delta = {}
        for sn in all_serials:
            net_delta[sn] = old_qty_map.get(sn, 0) - new_qty_map.get(sn, 0)

        for sn, delta in net_delta.items():
            if delta >= 0:
                continue
            product = products.get(sn)
            if not product:
                return JsonResponse({'status': 'error', 'message': f'Produk SN: {sn} tidak ditemukan.'})
            extra_needed = abs(delta)
            if product.quantity < extra_needed:
                return JsonResponse({
                    'status':  'error',
                    'message': (
                        f'Stok tidak cukup untuk {product.part_number} (SN: {sn}). '
                        f'Tersedia: {product.quantity}, butuh tambahan: {extra_needed}.'
                    ),
                })

        project_name = data.get('projectName', trx.project_name)

        with db_transaction.atomic():
            for sn, delta in net_delta.items():
                if delta == 0:
                    continue
                product    = products[sn]
                qty_before = product.quantity
                product.quantity += delta
                product.save()

                StockMovement.objects.create(
                    product       = product,
                    movement_type = 'ADJUST',
                    quantity      = delta,
                    qty_before    = qty_before,
                    qty_after     = product.quantity,
                    reference     = sdr_no,
                    note          = f"Edit Surat Jalan {sdr_no} — stock correction",
                    performed_by  = request.user,
                )

                direction = f"+{delta}" if delta > 0 else str(delta)
                log_action(
                    request.user, 'SJ_EDIT_STOCK',
                    f"Stock corrected for SN: {sn} ({product.part_number}) | "
                    f"Delta: {direction} | {qty_before} → {product.quantity} | SJ: {sdr_no}",
                )

            trx.sdr_no         = data.get('newSdrNo', sdr_no)
            trx.project_name   = project_name
            trx.recipient      = data.get('recipient',     trx.recipient)
            trx.items_json     = json.dumps(new_items)
            trx.request_date   = data.get('requestDate',   trx.request_date)
            trx.requestor      = data.get('requestor',     trx.requestor)
            trx.telephone      = data.get('telephone',     trx.telephone)
            trx.pic_at_site    = data.get('picAtSite',     trx.pic_at_site)
            trx.pic_mobile     = data.get('picMobile',     trx.pic_mobile)
            trx.subsystem      = data.get('subsystem',     trx.subsystem)
            trx.site_name      = data.get('siteName',      trx.site_name)
            trx.transport_mode = data.get('transportMode', trx.transport_mode)
            trx.address        = data.get('address',       trx.address)
            trx.save()

        log_action(
            request.user, 'EDIT_SJ',
            f"Edited Surat Jalan {sdr_no} | Project: {project_name} | "
            f"Items changed: {len(old_items)} → {len(new_items)} | "
            f"Editor: {request.user.username}",
        )
        return JsonResponse({'status': 'success', 'message': f'Surat Jalan {sdr_no} berhasil diupdate!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@login_required
@staff_required
def bulk_add_products(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'status': 'error', 'message': 'File harus format .csv!'})

        try:
            decoded_file  = csv_file.read().decode('utf-8').splitlines()
            reader        = csv.DictReader(decoded_file)
            added_count   = 0
            updated_count = 0

            for row in reader:
                if not row.get('partNumber') or not row.get('serialNumber'):
                    continue

                qty_raw = row.get('quantity', '')
                qty_val = int(qty_raw) if qty_raw.strip().isdigit() else 0
                serial  = row.get('serialNumber', '').strip()

                old_qty = 0
                try:
                    existing = Product.objects.get(serial_number=serial)
                    old_qty  = existing.quantity
                except Product.DoesNotExist:
                    pass

                obj, created = Product.objects.update_or_create(
                    serial_number=serial,
                    defaults={
                        'pre_order_number': row.get('preOrderNumber', ''),
                        'part_number':      row.get('partNumber', ''),
                        'product_code':     row.get('productCode', ''),
                        'awb':              row.get('awb', ''),
                        'description':      row.get('description', ''),
                        'quantity':         qty_val,
                        'category':         row.get('category', ''),
                        'platform':         row.get('platform', ''),
                        'location':         row.get('location', ''),
                    },
                )

                # FIX #10: Use abs() for quantity so StockMovement.quantity is
                # always a positive number; the movement_type conveys direction.
                qty_delta = qty_val - old_qty
                movement_type = 'IN' if created else 'ADJUST'
                note = (
                    f"CSV Import: {csv_file.name}"
                    if created
                    else f"CSV Import update: {csv_file.name} ({old_qty} → {qty_val})"
                )

                if created or old_qty != qty_val:
                    StockMovement.objects.create(
                        product       = obj,
                        movement_type = movement_type,
                        quantity      = abs(qty_delta) if not created else qty_val,
                        qty_before    = 0 if created else old_qty,
                        qty_after     = qty_val,
                        reference     = csv_file.name,
                        note          = note,
                        performed_by  = request.user,
                    )

                if created:
                    added_count += 1
                else:
                    updated_count += 1

            log_action(
                request.user, 'BULK_ADD',
                f"CSV Import: {added_count} new product(s) added, "
                f"{updated_count} existing product(s) updated | File: {csv_file.name}",
            )
            return JsonResponse({
                'status':  'success',
                'message': f'{added_count} ditambahkan, {updated_count} diperbarui!',
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Permintaan tidak valid.'})


# ---------------------------------------------------------------------------
# CRITICAL FIX (#3 in review): rollback_transaction previously only had
# @login_required, allowing ANY authenticated user (including Manager-role
# accounts) to roll back a Surat Jalan and modify stock quantities.
#
# Now gated with @staff_required, consistent with add_transaction,
# adjust_stock, and edit_transaction.
# ---------------------------------------------------------------------------
@csrf_exempt
@login_required
@staff_required
def rollback_transaction(request, sdr_no):
    """
    Rolls back an entire Surat Jalan:
    - Returns all withdrawn quantities back to stock
    - Marks the Transaction as is_rolled_back=True
    - Creates a ROLLBACK StockMovement for every item
    - Cannot be undone if already rolled back
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data = json.loads(request.body) if request.body else {}
        note = data.get('note', '').strip() or 'No reason provided'

        try:
            trx = Transaction.objects.get(sdr_no=sdr_no)
        except Transaction.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Surat Jalan {sdr_no} tidak ditemukan.'})

        if trx.is_rolled_back:
            return JsonResponse({
                'status':  'error',
                'message': f'Surat Jalan {sdr_no} sudah di-rollback sebelumnya.',
            })

        items = json.loads(trx.items_json)
        if not items:
            return JsonResponse({'status': 'error', 'message': 'Surat Jalan ini tidak memiliki item.'})

        serials  = [i.get('serialNumber', '') for i in items]
        products = {p.serial_number: p for p in Product.objects.filter(serial_number__in=serials)}

        from django.utils import timezone

        with db_transaction.atomic():
            for item in items:
                serial     = item.get('serialNumber', '')
                qty_return = int(item.get('quantity', 0))
                product    = products.get(serial)

                if not product:
                    log_action(
                        request.user, 'ROLLBACK_WARN',
                        f"Rollback SJ {sdr_no}: product SN {serial} not found, skipped.",
                    )
                    continue

                qty_before       = product.quantity
                product.quantity += qty_return
                product.save()

                # FIX #7: 'ROLLBACK' is now a valid choice in StockMovement.MOVEMENT_TYPES
                StockMovement.objects.create(
                    product       = product,
                    movement_type = 'ROLLBACK',
                    quantity      = qty_return,
                    qty_before    = qty_before,
                    qty_after     = product.quantity,
                    reference     = f'ROLLBACK:{sdr_no}',
                    note          = f"Rollback Surat Jalan {sdr_no} | Reason: {note}",
                    performed_by  = request.user,
                )

            # FIX #2: These fields now exist on the Transaction model
            trx.is_rolled_back = True
            trx.rolled_back_by = request.user
            trx.rolled_back_at = timezone.now()
            trx.rollback_note  = note
            trx.save()

        log_action(
            request.user, 'ROLLBACK_SJ',
            f"Rolled back Surat Jalan {sdr_no} | Project: {trx.project_name} | "
            f"{len(items)} item(s) returned to stock | Reason: {note}",
        )
        return JsonResponse({
            'status':  'success',
            'message': f'Surat Jalan {sdr_no} berhasil di-rollback. {len(items)} item dikembalikan ke stok.',
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ---------------------------------------------------------------------------
# CRITICAL FIX (#3 in review): rollback_movement previously only had
# @login_required, allowing ANY authenticated user (including Manager-role
# accounts) to roll back an individual stock movement and modify stock
# quantities directly.
#
# Now gated with @staff_required, consistent with the other stock-mutating
# views.
# ---------------------------------------------------------------------------
@csrf_exempt
@login_required
@staff_required
def rollback_movement(request, movement_id):
    """
    Rolls back a single StockMovement entry:
    - Reverses the quantity change on the product
    - Marks the original movement as is_rolled_back=True
    - Creates a new ROLLBACK StockMovement as the reverse entry
    - Validates stock won't go negative
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method invalid'})

    try:
        data = json.loads(request.body) if request.body else {}
        note = data.get('note', '').strip() or 'No reason provided'

        try:
            movement = StockMovement.objects.select_related('product').get(id=movement_id)
        except StockMovement.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Movement ID {movement_id} tidak ditemukan.'})

        # FIX #3: These fields now exist on StockMovement model
        if movement.is_rolled_back:
            return JsonResponse({
                'status':  'error',
                'message': 'Movement ini sudah di-rollback sebelumnya.',
            })

        if movement.movement_type == 'ROLLBACK':
            return JsonResponse({
                'status':  'error',
                'message': 'Tidak bisa rollback sebuah rollback entry.',
            })

        product = movement.product

        qty    = movement.quantity
        m_type = movement.movement_type

        if m_type == 'IN':
            reverse_delta = -abs(qty)
        elif m_type == 'OUT':
            reverse_delta = abs(qty)
        else:   # ADJUST
            reverse_delta = -qty

        new_qty = product.quantity + reverse_delta
        if new_qty < 0:
            return JsonResponse({
                'status':  'error',
                'message': (
                    f'Rollback tidak bisa dilakukan — stok {product.part_number} akan menjadi negatif '
                    f'({product.quantity} + ({reverse_delta}) = {new_qty}).'
                ),
            })

        from django.utils import timezone

        with db_transaction.atomic():
            qty_before       = product.quantity
            product.quantity = new_qty
            product.save()

            StockMovement.objects.create(
                product       = product,
                movement_type = 'ROLLBACK',
                quantity      = reverse_delta,
                qty_before    = qty_before,
                qty_after     = new_qty,
                reference     = f'ROLLBACK:MVT#{movement_id}',
                note          = (
                    f"Rollback of movement #{movement_id} "
                    f"({movement.get_movement_type_display()}, qty={qty}) | "
                    f"Reason: {note}"
                ),
                performed_by  = request.user,
            )

            # FIX #3: These fields now exist on StockMovement model
            movement.is_rolled_back = True
            movement.rolled_back_by = request.user
            movement.rolled_back_at = timezone.now()
            movement.rollback_note  = note
            movement.save()

        log_action(
            request.user, 'ROLLBACK_MVT',
            f"Rolled back movement #{movement_id} | "
            f"Product: {product.part_number} (SN: {product.serial_number}) | "
            f"Type: {m_type} | Qty reversed: {reverse_delta:+d} | "
            f"{qty_before} → {new_qty} | Reason: {note}",
        )
        return JsonResponse({
            'status':  'success',
            'message': (
                f'Movement #{movement_id} berhasil di-rollback. '
                f'Stok {product.part_number}: {qty_before} → {new_qty}.'
            ),
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ---------------------------------------------------------------------------
# FIX #1: Restored the orphaned PDF view that was floating outside any function
# ---------------------------------------------------------------------------

@login_required
def print_surat_jalan(request, sdr_no):
    """Generate and serve the PDF for a given Surat Jalan."""
    trx   = get_object_or_404(Transaction, sdr_no=sdr_no)
    items = json.loads(trx.items_json)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="SJ_{sdr_no}.pdf"'

    template    = get_template('surat_jalan_pdf.html')
    html        = template.render({'transaction': trx, 'items': items})
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Ada error pas bikin PDF!', status=400)

    log_action(
        request.user, 'PRINT_PDF',
        f"Printed PDF: Surat Jalan {sdr_no} | "
        f"Project: {trx.project_name} | Recipient: {trx.recipient}",
    )
    return response