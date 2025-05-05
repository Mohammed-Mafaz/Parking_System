from django.db import models
from django.utils import timezone


class Camera(models.Model):
    name = models.CharField(max_length=50)        # “Entrance”, “Section A”, “Exit”
    source = models.CharField(max_length=200)     # e.g. camera index or URL
    section = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


class ParkingSlot(models.Model):
    name = models.CharField(max_length=20, unique=True)
    section = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.section}:{self.name}"

class ParkingRecord(models.Model):
    plate = models.CharField(max_length=20, db_index=True)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(blank=True, null=True)

    camera = models.ForeignKey(
        Camera, on_delete=models.SET_NULL, blank=True, null=True,
        help_text="Camera that logged this event"
    )
    slot = models.ForeignKey(
        ParkingSlot, on_delete=models.SET_NULL, blank=True, null=True,
        help_text="Assigned parking slot"
    )

    amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.00,
        help_text="Calculated parking fee"
    )
    paid = models.BooleanField(default=False)

        # Store the Razorpay payment link so webhooks can match it later
    payment_link_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Razorpay Payment Link ID"
    )

    STATUS_CHOICES = [
        ('PARKED', 'Parked'),
        ('EXITED', 'Exited'),
        ('FREE', 'Free'),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='FREE'
    )

    def duration_minutes(self):
        end = self.exit_time or timezone.now()
        return (end - self.entry_time).total_seconds() / 60

    def calculate_fee(self, rate_per_hour=10):
        mins = self.duration_minutes()
        hours = mins / 60
        return round(hours * rate_per_hour, 2)

    def __str__(self):
        return f"{self.plate} ({self.status})"


class Payment(models.Model):
    parking_record = models.OneToOneField(
        ParkingRecord, on_delete=models.CASCADE, related_name='payment'
    )
    method = models.CharField(
        max_length=10, choices=[('UPI','UPI'), ('CASH','Cash')]
    )
    status = models.CharField(
        max_length=10,
        choices=[('PENDING','Pending'), ('SUCCESS','Success'), ('FAILED','Failed')],
        default='PENDING'
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.parking_record.plate} - {self.status}"
