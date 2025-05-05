import cv2, time, re, math
from collections import deque, defaultdict
from datetime import datetime

import numpy as np
import qrcode
from django.utils import timezone
from django.core.management.base import BaseCommand
from parking.models import ParkingRecord

from detectors.alpr import detect_and_read_plate

# --- Configuration ---
FRAME_WINDOW = 5                     # number of consecutive frames to confirm a plate
CACHE_EXPIRY_SECONDS = 10            # seconds before allowing a plate re-log
DISPLAY_PAYMENT_SECONDS = 10         # seconds to display payment QR screen
RATE_PER_HOUR = 20                   # Rs. per hour parking rate

# Indian license-plate regex: 2 letters, 2 digits, 1-2 letters, 4 digits
PLATE_REGEX = re.compile(r"^[A-Z]{2}[ -]?[0-9]{2}[ -]?[A-Z]{1,2}[ -]?[0-9]{4}$")

# State tracking
plate_windows = defaultdict(lambda: deque(maxlen=FRAME_WINDOW))  # sliding window for each plate
last_log_time = {}  # plate -> datetime of last DB write

class Command(BaseCommand):
    help = 'Monitor exit camera and process exits with payment QR display'

    def handle(self, *args, **kwargs):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stdout.write(self.style.ERROR("Camera not accessible."))
            return

        self.stdout.write(self.style.SUCCESS('Starting exit camera monitoring...'))

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Show live video feed
            cv2.imshow('Exit Monitor', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # 1. OCR on full frame
            raw_plate = detect_and_read_plate(frame)
            if not raw_plate:
                time.sleep(0.05)
                continue

            plate = raw_plate.strip().upper()
            # 2. Validate format
            if not PLATE_REGEX.fullmatch(plate):
                time.sleep(0.05)
                continue

            # 3. Multi-frame confirmation
            win = plate_windows[plate]
            win.append(plate)
            if len(win) < FRAME_WINDOW or len(set(win)) > 1:
                time.sleep(0.05)
                continue

            # 4. Confirmed: throttle writes and record exit
            now = timezone.now()
            last_time = last_log_time.get(plate)
            if not last_time or (now - last_time).total_seconds() > CACHE_EXPIRY_SECONDS:
                rec = ParkingRecord.objects.filter(
                    plate=plate,
                    exit_time__isnull=True
                ).order_by('-entry_time').first()

                if rec:
                    # Compute fee
                    duration = now - rec.entry_time
                    hours = duration.total_seconds() / 3600
                    amount = math.ceil(hours * RATE_PER_HOUR)

                    # Update exit time in DB
                    rec.exit_time = now
                    rec.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"[Exit] {plate} exited at {rec.exit_time}, Fee: ₹{amount}")
                    )

                    # Generate dummy UPI QR code
                    upi_url = f"upi://pay?pa=demo@upi&pn=Parking&am={amount}&cu=INR&tn=Parking%20Fee"
                    qr_img = qrcode.make(upi_url)
                    qr_np = np.array(qr_img.convert("RGB"))
                    qr_bgr = cv2.cvtColor(qr_np, cv2.COLOR_RGB2BGR)
                    qr_bgr = cv2.resize(qr_bgr, (200, 200))

                    # Prepare the TV display frame (QR + amount)
                    tv_frame = frame.copy()
                    fh, fw = tv_frame.shape[:2]
                    x_off, y_off = fw - 220, 10
                    tv_frame[y_off:y_off+200, x_off:x_off+200] = qr_bgr
                    cv2.putText(tv_frame, f"Pay ₹{amount}", (x_off, y_off+220),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

                    # Prepare the Guard Panel frame (with cash prompt)
                    guard_frame = tv_frame.copy()
                    cv2.putText(guard_frame, "Press 'C' to mark Cash Paid", (10, fh - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    # Display payment screens
                    end_time = time.time() + DISPLAY_PAYMENT_SECONDS
                    while time.time() < end_time:
                        cv2.imshow('Payment TV', tv_frame)
                        cv2.imshow('Guard Panel', guard_frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            break
                        elif key == ord('c'):
                            rec.paid = True
                            rec.save()
                            self.stdout.write(self.style.SUCCESS(f"[Exit] {plate} marked paid in cash."))
                            break

                    # Close payment windows
                    cv2.destroyWindow('Payment TV')
                    cv2.destroyWindow('Guard Panel')

                else:
                    self.stdout.write(f"[Exit] No open record found for {plate}")

                last_log_time[plate] = now

            time.sleep(0.05)

        cap.release()
        cv2.destroyAllWindows()
        self.stdout.write(self.style.SUCCESS('Exit camera monitoring stopped.'))


def run_exit_camera(source=0):
    Command().handle()
