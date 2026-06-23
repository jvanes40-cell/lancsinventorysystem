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

    # --- PRODUCTS ---
    path('api/products/',        views.get_products,      name='get_products'),
    path('api/add-product/',     views.add_product,       name='add_product'),
    path('api/edit-product/',    views.edit_product,      name='edit_product'),
    path('api/delete-product/',  views.delete_product,    name='delete_product'),
    path('api/bulk-add/',        views.bulk_add_products, name='bulk_add_products'),

    # --- TRANSACTIONS ---
    path('api/transactions/',    views.get_transactions,  name='get_transactions'),
    path('api/add-transaction/', views.add_transaction,   name='add_transaction'),
    path('api/edit-transaction/', views.edit_transaction, name='edit_transaction'),

    # --- LOGS ---
    path('api/activity-logs/', views.get_activity_logs, name='get_activity_logs'),

    # --- STOCK MOVEMENTS ---
    path('api/stock-movements/',
         views.get_stock_movements,
         name='get_stock_movements'),
    path('api/stock-movements/<str:serial_number>/',
         views.get_product_movement_summary,
         name='get_product_movement_summary'),
    path('api/stock-adjust/',
         views.adjust_stock,
         name='adjust_stock'),

    # FIX #4: Removed duplicate rollback URL registrations — each route appears exactly once.
    # FIX #1: Added print_surat_jalan URL for the restored PDF view.
    path('api/rollback-transaction/<str:sdr_no>/',
         views.rollback_transaction,
         name='rollback_transaction'),
    path('api/rollback-movement/<int:movement_id>/',
         views.rollback_movement,
         name='rollback_movement'),
    path('api/print-surat-jalan/<str:sdr_no>/',
         views.print_surat_jalan,
         name='print_surat_jalan'),
     path('api/export-pdf/<str:sdr_no>/',
          views.print_surat_jalan,
          name='export_pdf'),
]