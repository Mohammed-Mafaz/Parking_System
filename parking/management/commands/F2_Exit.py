# cameras/exit.py
import os
import cv2
import time
import re
import math
from collections import deque, defaultdict, Counter

import numpy as np
import qrcode
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.conf import settings
from parking.models import ParkingRecord
from detectors.alpr import detect_and_read_plate

import razorpay
from parking.models import Payment
from parking.models import ParkingRecord

# ——— Razorpay setup (use Test keys from your Dashboard) ———
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# ——— Configuration ———
FRAME_WINDOW            = 5
CACHE_EXPIRY_SECONDS    = 10
DISPLAY_PAYMENT_SECONDS = 60
RATE_PER_HOUR           = 20

# Indian plate regex (strict 10-char format)
PLATE_REGEX = re.compile(
    r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$", re.IGNORECASE
)

# State
plate_windows = defaultdict(lambda: deque(maxlen=FRAME_WINDOW))
last_log_time = {}

class Command(BaseCommand):
    help = "Monitor exit camera, generate QR, and process payments"

    def handle(self, *args, **kwargs):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stdout.write(self.style.ERROR("Camera not accessible."))
            return

        self.stdout.write(self.style.SUCCESS("Starting exit monitoring..."))
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

                # Always show live feed & allow quitting
                cv2.imshow("Exit Monitor", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                raw_plate = detect_and_read_plate(frame)
                if not raw_plate:
                    time.sleep(0.05)
                    continue

                plate = raw_plate.strip().upper()
                if not PLATE_REGEX.fullmatch(plate):
                    time.sleep(0.05)
                    continue

                # Debounce: need ≥3 identical reads in last 5 frames
                win = plate_windows[plate]
                win.append(plate)
                if len(win) >= FRAME_WINDOW:
                    most_common, count = Counter(win).most_common(1)[0]
                    if count >= 3:
                        self._process_valid_plate(plate, frame)

                time.sleep(0.05)
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.stdout.write(self.style.SUCCESS("Exit monitoring stopped."))

    def _process_valid_plate(self, plate, frame):
        now = timezone.now()
        last_time = last_log_time.get(plate)

        # Throttle so we only process once per CACHE_EXPIRY
        if last_time and (now - last_time).total_seconds() < CACHE_EXPIRY_SECONDS:
            return

        self.stdout.write(self.style.WARNING(f"Processing exit for {plate}"))
        rec = ParkingRecord.objects.filter(
            plate=plate, exit_time__isnull=True
        ).order_by("-entry_time").first()

        if not rec:
            self.stdout.write(self.style.ERROR(f"No active record for {plate}"))
            return

        # Compute fee
        duration = now - rec.entry_time
        hours   = duration.total_seconds() / 3600
        amount  = math.ceil(hours * RATE_PER_HOUR)
        amt_p   = amount * 100  # paise
        rec.amount = amount
        rec.status = 'EXITED'
        rec.exit_time = now
        rec.save()

        # Create a Razorpay Payment Link (returns short_url + id) :contentReference[oaicite:0]{index=0}
        link = self._create_payment_link(amt_p, plate)
        if not link:
            self.stdout.write(self.style.ERROR("Failed to init payment link"))
            return

        # 3) Store link ID & initialize a Payment record
        rec.payment_link_id = link["id"]
        rec.save()
        payment = Payment.objects.create(
            parking_record=rec,
            method='UPI',
            status='PENDING',
            amount=amount
        )


        payment_url = link["short_url"]
        link_id     = link["id"]
        self.stdout.write(f"Scan to pay: {payment_url}")

        # Show payment for a window of time
        end_time = time.time() + DISPLAY_PAYMENT_SECONDS
        paid     = False

        while time.time() < end_time and not paid:
            # Poll every 2s for link status
            if int(time.time()) % 2 == 0:
                # if self._check_payment_status(link_id):
                if self._check_payment_status(link["id"]):
                    rec.paid = True
                    rec.exit_time = now
                    rec.save()
                    payment.status = 'SUCCESS'
                    payment.save()
                    paid = True
                    self.stdout.write(
                        self.style.SUCCESS(f"Payment confirmed for {plate}")
                    )
                    break

            # Render QR on two displays
            tv, guard = self._generate_payment_frames(frame, amount, payment_url)
            cv2.imshow("Payment TV",       tv)
            cv2.imshow("Guard Panel", guard)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):  # Cash confirmed
                payment.method = 'CASH'
                payment.status = 'SUCCESS'
                payment.save()
                rec.paid = True
                rec.exit_time = now
                rec.save()
                paid = True
                self.stdout.write(
                    self.style.SUCCESS(f"Cash payment confirmed for {plate}")
                )
                break

        # Clean up and record timestamp
        cv2.destroyWindow("Payment TV")
        cv2.destroyWindow("Guard Panel")
        last_log_time[plate] = now

    def _create_payment_link(self, amount_paise, plate):
        try:
            return client.payment_link.create({
                "amount":      amount_paise,
                "currency":    "INR",
                "description": f"Parking Fee for {plate}",
                "customer":    {"name": plate},
                "notify":      {"sms": False, "email": False},
                "reminder_enable": True,
            })
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Link create failed: {e}"))
            return None

    def _check_payment_status(self, link_id):
        try:
            link = client.payment_link.fetch(link_id)
            return link.get("status") == "paid"
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Payment check error: {e}")
            )
            return False

    def _generate_payment_frames(self, frame, amount, payment_url):
        qr_img = qrcode.make(payment_url)
        qr_np  = np.array(qr_img.convert("RGB"))
        qr_bgr = cv2.cvtColor(qr_np, cv2.COLOR_RGB2BGR)
        qr_bgr = cv2.resize(qr_bgr, (300, 300))

        tv_frame    = frame.copy()
        fh, fw      = tv_frame.shape[:2]
        x_off, y_off = fw - 320, 10

        tv_frame[y_off:y_off+300, x_off:x_off+300] = qr_bgr
        cv2.putText(
            tv_frame, f"Scan to Pay ₹{amount}",
            (x_off, y_off+320),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2
        )
        # Guard panel could show extra info; for now clone TV
        guard_frame = tv_frame.copy()
        return tv_frame, guard_frame

def run_exit_camera(source=0):
    Command().handle()
