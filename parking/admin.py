# parking/admin.py
from django.contrib import admin
from .models import ParkingRecord, Payment, Camera

admin.site.register(ParkingRecord)
# admin.site.register(Payment)
admin.site.register(Camera)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("parking_record", "method", "status", "amount")
    actions = ["mark_success"]

    def mark_success(self, request, queryset):
        for obj in queryset:
            obj.status = 'SUCCESS'
            obj.parking_record.paid = True
            obj.parking_record.save()
            obj.save()
    mark_success.short_description = "Mark selected payments as SUCCESS"

