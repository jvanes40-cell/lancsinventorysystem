from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from gudang import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- LOGIN ---
    path('login/',  auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'),         name='logout'),

    # --- MAIN ---
    path('', views.index, name='home'),

    # --- HEALTH CHECK ---
    path('health/', views.health_check, name='health_check'),

    # --- PRODUCTS ---
    path('api/products/',        views.get_products,      name='get_products'),
    path('api/add-product/',     views.add_product,       name='add_product'),
    path('api/edit-product/',    views.edit_product,      name='edit_product'),
    path('api/delete-product/',  views.delete_product,    name='delete_product'),
    path('api/bulk-add/',        views.bulk_add_products, name='bulk_add_products'),

    # --- TRANSACTIONS ---
    path('api/transactions/',     views.get_transactions,  name='get_transactions'),
    path('api/add-transaction/',  views.add_transaction,   name='add_transaction'),
    path('api/edit-transaction/', views.edit_transaction,  name='edit_transaction'),
    path('api/transaction/<path:sdr_no>/', views.get_transaction_detail, name='get_transaction_detail'),

    # --- LOGS ---
    path('api/activity-logs/', views.get_activity_logs, name='get_activity_logs'),

    # --- STOCK MOVEMENTS ---
    path('api/stock-movements/',
         views.get_stock_movements,
         name='get_stock_movements'),
    path('api/stock-movements/<path:serial_number>/',
         views.get_product_movement_summary,
         name='get_product_movement_summary'),
    path('api/stock-adjust/',
         views.adjust_stock,
         name='adjust_stock'),

    # --- ROLLBACK ---
    path('api/rollback-transaction/<path:sdr_no>/',
         views.rollback_transaction,
         name='rollback_transaction'),
    path('api/rollback-movement/<int:movement_id>/',
         views.rollback_movement,
         name='rollback_movement'),

    # --- PDF EXPORT ---
    path('api/print-surat-jalan/<path:sdr_no>/',
         views.print_surat_jalan,
         name='print_surat_jalan'),
    path('api/export-pdf/<path:sdr_no>/',
         views.print_surat_jalan,
         name='export_pdf'),

    # --- RESERVE / RELEASE ---
    path('api/reserve-product/',  views.reserve_product,  name='reserve_product'),
    path('api/release-product/',  views.release_product,  name='release_product'),

    # --- SURAT MASUK ---
    path('api/surat-masuk/',                views.get_surat_masuk_history, name='get_surat_masuk_history'),
    path('api/surat-masuk/create/',             views.create_surat_masuk,     name='create_surat_masuk'),
    path('api/surat-masuk-pdf/<path:note_no>/', views.export_surat_masuk_pdf, name='export_surat_masuk_pdf'),
    path('api/surat-masuk-void/<path:note_no>/', views.void_surat_masuk,     name='void_surat_masuk'),
]