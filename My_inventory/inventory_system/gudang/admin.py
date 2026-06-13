from django.contrib import admin
from .models import Product, Transaction

# Buat nampilin tabel Product (Cara Standar)
admin.site.register(Product)

# Buat nampilin tabel Transaction (Surat Jalan) biar rapi (Cara Modern)
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('sdr_no', 'project_name', 'recipient', 'request_date', 'created_at')
    search_fields = ('sdr_no', 'project_name', 'recipient')