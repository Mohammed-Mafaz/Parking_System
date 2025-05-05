import cv2
import time
import re
from collections import deque, defaultdict
from datetime import datetime

from django.utils import timezone
from django.core.management.base import BaseCommand
from parking.models import ParkingRecord

from detectors.alpr import detect_and_read_plate
from collections import Counter

# --- Configuration ---
FRAME_WINDOW = 5
CACHE_EXPIRY_SECONDS = 10
PLATE_REGEX = re.compile(r"^[A-Z0-9]{2,3}[ -]?[A-Z0-9]{2,3}[ -]?[A-Z0-9]{3,5}$", re.IGNORECASE)

# State
plate_windows = defaultdict(lambda: deque(maxlen=FRAME_WINDOW))
last_log_time = {}

class Command(BaseCommand):
    help = "Run entrance camera loop with full-frame OCR processing"

    def handle(self, *args, **options):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stdout.write(self.style.ERROR("Camera not accessible."))
            return

        cv2.namedWindow("Entrance Monitor", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Entrance Monitor", 800, 600)

        self.stdout.write(self.style.SUCCESS("Starting entrance monitoring..."))

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue

                # Mirror the frame for natural viewing
                frame = cv2.flip(frame, 1)
                cv2.imshow("Entrance Monitor", frame)

                # Process OCR
                raw_plate = detect_and_read_plate(frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                if not raw_plate:
                    continue

                plate = raw_plate.strip().upper()

                # Validate plate format
                if not PLATE_REGEX.fullmatch(plate):
                    continue

                # Frame consensus check
                win = plate_windows[plate]
                win.append(plate)
                
                if len(win) >= FRAME_WINDOW:
                    counts = Counter(win)
                    most_common = counts.most_common(1)[0]
                    if most_common[1] >= 3:  # Majority vote
                        self._handle_valid_plate(plate)

                time.sleep(0.05)

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.stdout.write(self.style.SUCCESS("Entrance monitoring stopped."))

    def _handle_valid_plate(self, plate):
        now = timezone.now()
        last_time = last_log_time.get(plate)
        
        if not last_time or (now - last_time).total_seconds() > CACHE_EXPIRY_SECONDS:
            existing = ParkingRecord.objects.filter(
                plate=plate, 
                exit_time__isnull=True
            ).first()
            
            if not existing:
                ParkingRecord.objects.create(plate=plate, entry_time=now)
                self.stdout.write(self.style.SUCCESS(f"Logged entry: {plate}"))
            else:
                self.stdout.write(f"Duplicate plate: {plate}")
            
            last_log_time[plate] = now