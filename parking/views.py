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


# @csrf_exempt
# def payment_callback(request):
#     if request.method == 'POST':
#         try:
#             # Verify signature
#             body = request.body.decode('utf-8')
#             received_signature = request.headers.get('X-Razorpay-Signature', '')
            
#             client.utility.verify_webhook_signature(
#                 body,
#                 received_signature,
#                 settings.RAZORPAY_WEBHOOK_SECRET
#             )
            
#             data = json.loads(body)
#             if data['event'] == 'payment.captured':
#                 order_id = data['payload']['payment']['entity']['order_id']
#                 # Update your database here
#                 return HttpResponse(status=200)
                
#         except Exception as e:
#             print(f"Payment callback error: {str(e)}")
#             return HttpResponse(status=400)
    
#     return HttpResponse(status=405)




    # def exit_kiosk(request, record_id):
#     rec = get_object_or_404(ParkingRecord, pk=record_id, exit_time__isnull=True)
#     rec.exit_time = timezone.now()
#     rec.save()
#     amount = int(rec.amount_due() * 100)  # in paise

#     # create or get Payment
#     payment, created = Payment.objects.get_or_create(
#        parking_record=rec,
#        defaults={"amount": rec.amount_due(), "method": "UPI"}
#     )

#     razorpay_order = client.order.create({
#         "amount": amount,
#         "currency": "INR",
#         "receipt": f"recpt_{rec.id}",
#         "payment_capture": 1
#     })
#     payment.razorpay_order_id = razorpay_order['id']
#     payment.save()

#     # Generate UPI QR code
#     upi_link = f"upi://pay?pa={settings.UPI_ID}&pn=MyParkingLot&am={rec.amount_due()}&tn=Parking+Fee"
#     img = qrcode.make(upi_link)
#     img.save(f"/tmp/upi_{rec.id}.png")

#     return render(request, "exit_kiosk.html", {
#         "record": rec,
#         "order": razorpay_order,
#         "qr_url": f"/static/upi_{rec.id}.png",
#     })



@csrf_exempt
def payment_callback(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    # 1) Verify signature
    body = request.body.decode("utf-8")
    signature = request.headers.get("X-Razorpay-Signature", "")
    try:
        client.utility.verify_webhook_signature(
            body, signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        return HttpResponse(status=400)

    # 2) Parse the event
    event = json.loads(body)
    if event.get("event") != "payment_link.paid":
        return HttpResponse(status=200)  # ignore other events

    payload = event["payload"]["payment_link"]["entity"]
    link_id = payload["id"]

    # 3) Mark the corresponding ParkingRecord as paid & set exit_time
    try:
        rec = ParkingRecord.objects.get(payment_link_id=link_id)
        rec.paid = True
        rec.exit_time = rec.exit_time or timezone.now()
        rec.save()
    except ParkingRecord.DoesNotExist:
        # optionally log: no record found for this link_id
        pass

    return HttpResponse(status=200)