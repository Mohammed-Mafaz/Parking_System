from django.shortcuts import render
# parking/views.py
import razorpay, qrcode
from django.shortcuts import render, get_object_or_404
from .models import ParkingRecord, Payment
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse

client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

def exit_kiosk(request, record_id):
    rec = get_object_or_404(ParkingRecord, pk=record_id, exit_time__isnull=True)
    rec.exit_time = timezone.now()
    rec.save()
    amount = int(rec.amount_due() * 100)  # in paise

    # create or get Payment
    payment, created = Payment.objects.get_or_create(
       parking_record=rec,
       defaults={"amount": rec.amount_due(), "method": "UPI"}
    )

    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": f"recpt_{rec.id}",
        "payment_capture": 1
    })
    payment.razorpay_order_id = razorpay_order['id']
    payment.save()

    # Generate UPI QR code
    upi_link = f"upi://pay?pa={settings.UPI_ID}&pn=MyParkingLot&am={rec.amount_due()}&tn=Parking+Fee"
    img = qrcode.make(upi_link)
    img.save(f"/tmp/upi_{rec.id}.png")

    return render(request, "exit_kiosk.html", {
        "record": rec,
        "order": razorpay_order,
        "qr_url": f"/static/upi_{rec.id}.png",
    })

