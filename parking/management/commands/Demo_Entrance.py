import cv2, time, re
from datetime import datetime

from django.utils import timezone
from django.core.management.base import BaseCommand
from parking.models import ParkingRecord
from detectors.alpr import ocr_plate_from_frame

# ANSI color codes for logs
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

# Configuration
CACHE_EXPIRY_SECONDS = 5    # seconds before allowing re-log
FRAME_SKIP = 3              # OCR every nth frame
# Updated realistic plate regex
PLATE_REGEX = re.compile(r"^[A-Z0-9]{2,3}[ -]?[A-Z0-9]{2,3}[ -]?[A-Z0-9]{3,5}$", re.IGNORECASE)

class Command(BaseCommand):
    help = "Entrance monitor: instant logging on first valid detection"

    def handle(self, *args, **options):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stderr.write(f"{RED}[ERROR]{RESET} Entrance camera not accessible.")
            return

        self.stdout.write(f"{GREEN}[INFO]{RESET} Starting Entrance Monitor...")
        last_log_time = {}
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            frame_count += 1

            # Display feed
            cv2.imshow("Entrance", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Skip frames to reduce load
            if frame_count % FRAME_SKIP != 0:
                continue

            # # Detect plate
            # # 1) locate plate bounding box
            # bbox = detect_plate_bbox(frame)
            # if not bbox:
            #     self.stdout.write(f"{YELLOW}[DEBUG]{RESET} No plate bbox found")
            #     continue

            # x1,y1,x2,y2 = bbox
            # plate_roi = frame[y1:y2, x1:x2]

            # 2) run OCR on just the plate ROI
            plate = ocr_plate_from_frame(frame)
            if not plate:
                self.stdout.write(f"{YELLOW}[DEBUG]{RESET} OCR failed on ROI")
                continue
            if not PLATE_REGEX.fullmatch(plate):
                self.stdout.write(f"{YELLOW}[WARN]{RESET} Invalid plate format: {plate}")
                continue

            # Throttle repeated logs
            now = timezone.now()
            last = last_log_time.get(plate)
            if last and (now - last).total_seconds() < CACHE_EXPIRY_SECONDS:
                self.stdout.write(f"{YELLOW}[DEBUG]{RESET} Recently logged: {plate}")
                continue

            # Log to DB
            exists = ParkingRecord.objects.filter(plate=plate, exit_time__isnull=True).exists()
            if not exists:
                ParkingRecord.objects.create(plate=plate, entry_time=now)
                self.stdout.write(f"{GREEN}[ENTRY]{RESET} {plate} logged at {now.strftime('%H:%M:%S')}")
            else:
                self.stdout.write(f"{YELLOW}[ENTRY]{RESET} {plate} already inside. Skipping.")

            last_log_time[plate] = now
            time.sleep(0.1)

        cap.release()
        cv2.destroyAllWindows()
        self.stdout.write(f"{GREEN}[INFO]{RESET} Entrance Monitor stopped.")