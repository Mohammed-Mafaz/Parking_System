from django.db import models
from django.utils import timezone

# Create your models here.
class ParkingRecord(models.Model):
    plate = models.CharField(max_length=20, db_index=True)
    entry_time = models.DateTimeField()
    section = models.CharField(max_length=50, blank=True, null=True)
    slot = models.CharField(max_length=20, blank=True, null=True)
    exit_time = models.DateTimeField(blank=True, null=True)
    paid = models.BooleanField(default=False)

    def duration_minutes(self):
        end = self.exit_time or timezone.now()
        return (end - self.entry_time).total_seconds() / 60

    def amount_due(self, rate_per_hour=10):
        mins = max(0, self.duration_minutes() - 5)  # free first 5 min
        hours = (mins / 60)
        return round(hours * rate_per_hour, 2)


class Payment(models.Model):
    parking_record = models.OneToOneField(
        ParkingRecord, on_delete=models.CASCADE, related_name='payment'
    )
    method = models.CharField(max_length=10, choices=[('UPI','UPI'),('CASH','Cash')])
    status = models.CharField(max_length=10, choices=[('PENDING','Pending'),
                                                      ('SUCCESS','Success'),
                                                      ('FAILED','Failed')],
                              default='PENDING')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Camera(models.Model):
    name    = models.CharField(max_length=50)        # “Entrance”, “Section A”, “Exit”
    source  = models.CharField(max_length=200)       # e.g. “0” or rtsp://...
    section = models.CharField(max_length=50, null=True, blank=True)
