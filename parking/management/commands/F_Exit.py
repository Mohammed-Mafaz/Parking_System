import cv2
import time
import re
import math
from collections import deque, defaultdict, Counter

import numpy as np
import qrcode
from django.utils import timezone
from django.core.management.base import BaseCommand
from parking.models import ParkingRecord

from detectors.alpr import detect_and_read_plate

# --- Configuration ---
FRAME_WINDOW = 5
CACHE_EXPIRY_SECONDS = 10
DISPLAY_PAYMENT_SECONDS = 45
RATE_PER_HOUR = 20
PLATE_REGEX = re.compile(r"^[A-Z0-9]{2,3}[ -]?[A-Z0-9]{2,3}[ -]?[A-Z0-9]{3,5}$", re.IGNORECASE)

# State
plate_windows = defaultdict(lambda: deque(maxlen=FRAME_WINDOW))
last_log_time = {}

class Command(BaseCommand):
    help = "Monitor exit camera and process exits with payment QR display"

    def handle(self, *args, **kwargs):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stdout.write(self.style.ERROR("Camera not accessible."))
            return

        try:
            self.stdout.write(self.style.SUCCESS("Starting exit camera monitoring..."))
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

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

                # Frame consensus check
                win = plate_windows[plate]
                win.append(plate)
                
                if len(win) >= FRAME_WINDOW:
                    counts = Counter(win)
                    most_common = counts.most_common(1)[0]
                    if most_common[1] >= 3:  # Majority vote
                        self._process_valid_plate(plate, frame)

                time.sleep(0.05)
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.stdout.write(self.style.SUCCESS("Exit camera monitoring stopped."))

    def _process_valid_plate(self, plate, frame):
        now = timezone.now()
        last_time = last_log_time.get(plate)
        
        if not last_time or (now - last_time).total_seconds() > CACHE_EXPIRY_SECONDS:
            self.stdout.write(self.style.WARNING(f"Processing exit for plate: {plate}"))
            rec = ParkingRecord.objects.filter(
                plate=plate, 
                exit_time__isnull=True
            ).order_by("-entry_time").first()

            if not rec:
                self.stdout.write(self.style.ERROR(f"No open record found for {plate}"))
                return

            # Calculate parking fee
            duration = now - rec.entry_time
            hours = duration.total_seconds() / 3600
            amount = math.ceil(hours * RATE_PER_HOUR)
            self.stdout.write(f"Calculated fee: ₹{amount} for {hours:.2f} hours")

            # Update database record
            rec.exit_time = now
            rec.save()
            self.stdout.write(self.style.SUCCESS(f"Exit recorded for {plate} at {now}"))

            # Payment handling
            payment_marked = False
            end_time = time.time() + DISPLAY_PAYMENT_SECONDS
            
            while time.time() < end_time and not payment_marked:
                tv_frame, guard_frame = self._generate_payment_frames(frame, amount, end_time)
                
                cv2.imshow("Payment TV", tv_frame)
                cv2.imshow("Guard Panel", guard_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    self.stdout.write("Early exit from payment window")
                    break
                elif key == ord('c'):
                    rec.paid = True
                    rec.save()
                    payment_marked = True
                    self.stdout.write(self.style.SUCCESS(f"Cash payment confirmed for {plate}"))

            # Handle timeout
            if not payment_marked:
                self.stdout.write(self.style.WARNING(f"Payment window closed for {plate} without confirmation"))

            cv2.destroyWindow("Payment TV")
            cv2.destroyWindow("Guard Panel")
            last_log_time[plate] = now

    def _generate_payment_frames(self, frame, amount, end_time):
        """Helper to generate updated payment frames with countdown"""
        # Generate QR code
        upi_url = f"upi://pay?pa=demo@upi&pn=Parking&am={amount}&cu=INR&tn=Parking%20Fee"
        qr_img = qrcode.make(upi_url)
        qr_np = np.array(qr_img.convert("RGB"))
        qr_bgr = cv2.cvtColor(qr_np, cv2.COLOR_RGB2BGR)
        qr_bgr = cv2.resize(qr_bgr, (200, 200))

        # Prepare display frames
        tv_frame = frame.copy()
        fh, fw = tv_frame.shape[:2]
        x_off, y_off = fw - 220, 10
        
        # Calculate remaining time
        remaining = max(0, end_time - time.time())
        timer_text = f"Time remaining: {int(remaining)}s"
        
        tv_frame[y_off:y_off+200, x_off:x_off+200] = qr_bgr
        cv2.putText(tv_frame, f"Pay ₹{amount}", (x_off, y_off+220),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        cv2.putText(tv_frame, timer_text, (x_off-50, y_off-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        guard_frame = tv_frame.copy()
        cv2.putText(guard_frame, "Press 'C' to mark Cash Paid", (10, fh - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        return tv_frame, guard_frame

def run_exit_camera(source=0):
    Command().handle()