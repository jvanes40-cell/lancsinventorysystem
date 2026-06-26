from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ---------------------------------------------------------------------------
# USER PROFILE
# ---------------------------------------------------------------------------

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('staff',   'Staff'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_staff_role(self):
        return self.role == 'staff'

    @property
    def can_edit_stock(self):
        return self.role in ('staff', 'manager')

    @property
    def can_delete_stock(self):
        return self.user.is_superuser

    @property
    def can_create_surat_jalan(self):
        return self.role == 'staff'

    @property
    def can_bulk_import(self):
        return self.role == 'staff'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


# ---------------------------------------------------------------------------
# PRODUCT
# ---------------------------------------------------------------------------

class Product(models.Model):
    pre_order_number = models.CharField(max_length=100, blank=True)
    part_number      = models.CharField(max_length=100)
    serial_number    = models.CharField(max_length=100)
    product_code     = models.CharField(max_length=100, blank=True)
    description      = models.TextField(blank=True)
    quantity         = models.IntegerField(default=0)
    category         = models.CharField(max_length=100, blank=True)
    platform         = models.CharField(max_length=100, blank=True)
    location         = models.CharField(max_length=100, blank=True)
    awb              = models.CharField(max_length=100, blank=True, null=True)
    date_added       = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ('can_add_product',    'Can add product'),
            ('can_edit_product',   'Can edit product'),
            ('can_delete_product', 'Can delete product'),
            ('can_bulk_import',    'Can bulk import products via CSV'),
        ]
        indexes = [
            models.Index(fields=['serial_number']),
            models.Index(fields=['part_number']),
            models.Index(fields=['category']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return f"{self.part_number} - {self.serial_number}"


# ---------------------------------------------------------------------------
# STOCK MOVEMENT
# Structured record of every IN / OUT / ADJUST / ROLLBACK event on a product.
# ---------------------------------------------------------------------------

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN',       'Stock In'),     # New stock received / added
        ('OUT',      'Stock Out'),    # Withdrawn via Surat Jalan
        ('ADJUST',   'Adjustment'),   # Manual correction (positive or negative)
        ('ROLLBACK', 'Rollback'),     # FIX #7: Added ROLLBACK as a valid choice
    ]

    product       = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity      = models.IntegerField()   # Positive for IN/OUT/ROLLBACK; signed delta for ADJUST
    qty_before    = models.IntegerField()   # Stock level before this movement
    qty_after     = models.IntegerField()   # Stock level after this movement
    reference     = models.CharField(max_length=200, blank=True)  # e.g. SDR No, CSV filename
    note          = models.TextField(blank=True)      # Free-text reason / context
    performed_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    timestamp     = models.DateTimeField(auto_now_add=True)

    # FIX #3: Rollback tracking fields (mirrors Transaction rollback fields)
    is_rolled_back  = models.BooleanField(default=False)
    rolled_back_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rolled_back_movements',
    )
    rolled_back_at  = models.DateTimeField(null=True, blank=True)
    rollback_note   = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes  = [
            models.Index(fields=['product', 'timestamp']),
            models.Index(fields=['movement_type']),
        ]

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} | "
            f"{self.product.serial_number} | "
            f"qty={self.quantity} | "
            f"{self.timestamp:%Y-%m-%d %H:%M}"
        )


# ---------------------------------------------------------------------------
# TRANSACTION
# ---------------------------------------------------------------------------

class Transaction(models.Model):
    sdr_no       = models.CharField(max_length=100, unique=True)
    project_name = models.CharField(max_length=200)
    recipient    = models.CharField(max_length=100)
    items_json   = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    request_date   = models.CharField(max_length=50,  null=True, blank=True)
    requestor      = models.CharField(max_length=100, null=True, blank=True)
    telephone      = models.CharField(max_length=50,  null=True, blank=True)
    pic_at_site    = models.CharField(max_length=100, null=True, blank=True)
    pic_mobile     = models.CharField(max_length=50,  null=True, blank=True)
    subsystem      = models.CharField(max_length=100, null=True, blank=True)
    site_name      = models.CharField(max_length=100, null=True, blank=True)
    transport_mode = models.CharField(max_length=50,  null=True, blank=True)
    address        = models.TextField(null=True, blank=True)

    # FIX #2: Rollback tracking fields — required by rollback_transaction view
    is_rolled_back = models.BooleanField(default=False)
    rolled_back_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rolled_back_transactions',
    )
    rolled_back_at = models.DateTimeField(null=True, blank=True)
    rollback_note  = models.TextField(blank=True)

    class Meta:
        permissions = [
            ('can_create_transaction', 'Can create Surat Jalan'),
        ]
        indexes = [
            models.Index(fields=['sdr_no']),        # FIX #8: removed invalid '-' prefix
            models.Index(fields=['created_at']),    # FIX #8: '-' prefix is invalid in Index(fields=[])
            models.Index(fields=['project_name']),
        ]

    def __str__(self):
        return f"{self.sdr_no} - {self.project_name}"


# ---------------------------------------------------------------------------
# ACTIVITY LOG
# ---------------------------------------------------------------------------

class ActivityLog(models.Model):
    user      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action    = models.CharField(max_length=50)
    details   = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),  # FIX #8: removed invalid '-' prefix
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"