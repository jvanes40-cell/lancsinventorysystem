"""
Migration: Add rollback fields to Transaction and StockMovement,
           add ROLLBACK to StockMovement.MOVEMENT_TYPES choices,
           and fix invalid '-' prefix in Index(fields=[]).

Run with:
    python manage.py migrate
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    # Replace 'XXXX_previous_migration' with the name of the last migration
    # in your gudang/migrations/ folder.
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gudang', '0006_stockmovement_and_more'),
    ]

    operations = [

        # -----------------------------------------------------------------------
        # FIX #2: Add rollback fields to Transaction
        # -----------------------------------------------------------------------
        migrations.AddField(
            model_name='transaction',
            name='is_rolled_back',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='transaction',
            name='rolled_back_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rolled_back_transactions',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='transaction',
            name='rolled_back_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='rollback_note',
            field=models.TextField(blank=True),
        ),

        # -----------------------------------------------------------------------
        # FIX #3 & #7: Add rollback fields + ROLLBACK choice to StockMovement
        # -----------------------------------------------------------------------
        migrations.AlterField(
            model_name='stockmovement',
            name='movement_type',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('IN',       'Stock In'),
                    ('OUT',      'Stock Out'),
                    ('ADJUST',   'Adjustment'),
                    ('ROLLBACK', 'Rollback'),   # FIX #7: new valid choice
                ],
            ),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='is_rolled_back',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='rolled_back_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rolled_back_movements',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='rolled_back_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='stockmovement',
            name='rollback_note',
            field=models.TextField(blank=True),
        ),

        # -----------------------------------------------------------------------
        # FIX #8: Remove invalid Index(fields=['-created_at']) on Transaction.
        # Django's Index() does not accept the '-' prefix; use Meta.ordering instead.
        # -----------------------------------------------------------------------
        migrations.AlterModelOptions(
            name='transaction',
            options={
                'permissions': [('can_create_transaction', 'Can create Surat Jalan')],
            },
        ),
        migrations.AlterModelTable(
            name='transaction',
            table=None,
        ),
    ]