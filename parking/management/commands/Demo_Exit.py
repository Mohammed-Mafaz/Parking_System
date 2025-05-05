# cameras/exit.py
import cv2, time, re, math
from collections import deque, defaultdict, Counter
import numpy as np
import qrcode
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.conf import settings
from parking.models import ParkingRecord, Payment
from detectors.alpr import detect_and_read_plate
import razorpay

# ——— Razorpay setup (use Test keys) ———
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# ——— Configuration ———
FRAME_WINDOW            = 5
CACHE_EXPIRY_SECONDS    = 10
DISPLAY_PAYMENT_SECONDS = 60
RATE_PER_HOUR           = 20
FRAME_SKIP              = 3

# Indian plate regex
PLATE_REGEX = re.compile(
    r"^[A-Z0-9]{2,3}[ -]?[A-Z0-9]{2,3}[ -]?[A-Z0-9]{3,5}$",
    re.IGNORECASE
)

# ANSI color codes
GREEN  = '\033[92m'
YELLOW = '\033[93m'
RED    = '\033[91m'
RESET  = '\033[0m'

# State
plate_windows = defaultdict(lambda: deque(maxlen=FRAME_WINDOW))
last_log_time = {}

class Command(BaseCommand):
    help = "Monitor exit camera, generate QR, and process payments"

    def handle(self, *args, **kwargs):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stderr.write(f"{RED}[ERROR]{RESET} Exit camera not accessible.")
            return

        self.stdout.write(f"{GREEN}[INFO]{RESET} Starting exit monitoring...")
        frame_count = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                frame_count += 1

                # live feed & quit
                cv2.imshow("Exit Monitor", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                # skip frames
                if frame_count % FRAME_SKIP != 0:
                    time.sleep(0.01)
                    continue

                raw_plate = detect_and_read_plate(frame)
                if not raw_plate:
                    self.stdout.write(f"{YELLOW}[DEBUG]{RESET} No plate detected.")
                    time.sleep(0.05)
                    continue

                plate = raw_plate.strip().upper()
                if not PLATE_REGEX.fullmatch(plate):
                    self.stdout.write(f"{YELLOW}[WARN]{RESET} Invalid plate: {plate}")
                    time.sleep(0.05)
                    continue

                # debounce: need majority in window
                win = plate_windows[plate]
                win.append(plate)
                if len(win) >= FRAME_WINDOW:
                    most_common, count = Counter(win).most_common(1)[0]
                    if count >= (FRAME_WINDOW // 2 + 1):
                        self._process_valid_plate(plate, frame)
                time.sleep(0.05)
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.stdout.write(f"{GREEN}[INFO]{RESET} Exit monitoring stopped.")

    def _process_valid_plate(self, plate, frame):
        now = timezone.now()
        last_time = last_log_time.get(plate)
        if last_time and (now - last_time).total_seconds() < CACHE_EXPIRY_SECONDS:
            return

        self.stdout.write(f"{GREEN}[EXIT]{RESET} Processing exit for {plate} at {now.strftime('%H:%M:%S')}")
        rec = ParkingRecord.objects.filter(
            plate=plate, exit_time__isnull=True
        ).order_by('-entry_time').first()
        if not rec:
            self.stderr.write(f"{RED}[ERROR]{RESET} No active record for {plate}.")
            last_log_time[plate] = now
            return

        # compute fee
        duration = (now - rec.entry_time).total_seconds() / 3600
        amount = math.ceil(duration * RATE_PER_HOUR)
        rec.amount = amount
        rec.status = 'EXITED'
        rec.exit_time = now
        rec.save()
        self.stdout.write(f"{GREEN}[EXIT]{RESET} Duration: {duration*60:.0f} min, Fee: ₹{amount}")

        # create payment link
        link = self._create_payment_link(amount*100, plate)
        if not link:
            self.stderr.write(f"{RED}[ERROR]{RESET} Failed to create payment link.")
            last_log_time[plate] = now
            return

        rec.payment_link_id = link['id']
        rec.save()
        payment = Payment.objects.create(
            parking_record=rec,
            method='UPI', status='PENDING', amount=amount
        )
        payment_url = link['short_url']
        self.stdout.write(f"{GREEN}[PAY]{RESET} Scan to pay: {payment_url}")

        # display QR & poll
        end_time = time.time() + DISPLAY_PAYMENT_SECONDS
        while time.time() < end_time:
            tv, guard = self._generate_payment_frames(frame, amount, payment_url)
            cv2.imshow("Payment TV", tv)
            cv2.imshow("Guard Panel", guard)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                payment.method = 'CASH'
                payment.status = 'SUCCESS'
                payment.save()
                rec.paid = True
                rec.save()
                self.stdout.write(f"{GREEN}[PAY]{RESET} Cash payment confirmed for {plate}")
                break

            # check payment status every 2s
            if int(time.time()) % 2 == 0:
                if self._check_payment_status(link['id']):
                    rec.paid = True
                    rec.save()
                    payment.status = 'SUCCESS'
                    payment.save()
                    self.stdout.write(f"{GREEN}[PAY]{RESET} Payment confirmed for {plate}")
                    break

        cv2.destroyWindow("Payment TV")
        cv2.destroyWindow("Guard Panel")
        last_log_time[plate] = now

    def _create_payment_link(self, amount_paise, plate):
        try:
            return client.payment_link.create({
                "amount": amount_paise,
                "currency": "INR",
                "description": f"Parking Fee for {plate}",
                "customer": {"name": plate},
                "notify": {"sms": False, "email": False},
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
            self.stdout.write(self.style.WARNING(f"Payment check error: {e}"))
            return False

    def _generate_payment_frames(self, frame, amount, payment_url):
        qr_img = qrcode.make(payment_url)
        qr_np = np.array(qr_img.convert("RGB"))
        qr_bgr = cv2.cvtColor(qr_np, cv2.COLOR_RGB2BGR)
        qr_bgr = cv2.resize(qr_bgr, (300, 300))

        tv_frame = frame.copy()
        h, w = tv_frame.shape[:2]
        x_off, y_off = w - 320, 10
        tv_frame[y_off:y_off+300, x_off:x_off+300] = qr_bgr
        cv2.putText(
            tv_frame, f"Scan to Pay ₹{amount}",
            (x_off, y_off+320),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2
        )
        guard_frame = tv_frame.copy()
        return tv_frame, guard_frame


def run_exit_camera(source=0):
    Command().handle()
