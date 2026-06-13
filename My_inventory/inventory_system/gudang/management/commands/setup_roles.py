"""
Management command to create the Manager and Staff permission groups.

Run once after migrating:
    python manage.py setup_roles

Re-running is safe — it uses get_or_create throughout.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from gudang.models import Product, Transaction


class Command(BaseCommand):
    help = 'Creates Manager and Staff permission groups for RBAC.'

    def handle(self, *args, **options):
        product_ct     = ContentType.objects.get_for_model(Product)
        transaction_ct = ContentType.objects.get_for_model(Transaction)

        # --- Resolve permissions ---
        can_add_product        = Permission.objects.get(codename='can_add_product',    content_type=product_ct)
        can_edit_product       = Permission.objects.get(codename='can_edit_product',   content_type=product_ct)
        can_delete_product     = Permission.objects.get(codename='can_delete_product', content_type=product_ct)
        can_bulk_import        = Permission.objects.get(codename='can_bulk_import',    content_type=product_ct)
        can_create_transaction = Permission.objects.get(codename='can_create_transaction', content_type=transaction_ct)

        # ----------------------------------------------------------------
        # MANAGER GROUP — view + export PDF only
        # ----------------------------------------------------------------
        manager_group, created = Group.objects.get_or_create(name='Manager')
        manager_group.permissions.set([])   # Managers rely on role check, no write perms
        manager_group.save()
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} group: Manager"
        ))

        # ----------------------------------------------------------------
        # STAFF GROUP — full write access except delete
        # ----------------------------------------------------------------
        staff_group, created = Group.objects.get_or_create(name='Staff')
        staff_group.permissions.set([
            can_add_product,
            can_edit_product,
            can_bulk_import,
            can_create_transaction,
        ])
        staff_group.save()
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} group: Staff"
        ))

        self.stdout.write(self.style.SUCCESS('\nRoles setup complete!'))
        self.stdout.write(
            'Assign users via Django admin → Users → choose a user → Groups.\n'
            'Then set their UserProfile.role to match (manager / staff).'
        )