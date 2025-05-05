# import cv2, time, re
# from collections import deque, defaultdict
# from datetime import datetime

# from django.utils import timezone
# from django.core.management.base import BaseCommand
# from parking.models import ParkingRecord

# from detectors.alpr import detect_and_read_plate
# import os
# from django.conf import settings
# # from detectors.alpr import ocr_plate_from_frame

# # --- Configuration ---
# FRAME_WINDOW = 5                     # number of consecutive frames to confirm a plate
# CACHE_EXPIRY_SECONDS = 10            # seconds before allowing a plate re-log

# # # Indian license-plate regex: 2 letters, 2 digits, 1-2 letters, 4 digits
# # PLATE_REGEX = re.compile(r"^[A-Z]{2}[ -]?[0-9]{2}[ -]?[A-Z]{1,2}[ -]?[0-9]{4}$")
# # More flexible pattern accounting for OCR errors
# PLATE_REGEX = re.compile(r"^[A-Z0-9]{2,3}[ -]?[A-Z0-9]{2,3}[ -]?[A-Z0-9]{3,5}$", re.IGNORECASE)

# # State
# plate_windows = defaultdict(lambda: deque(maxlen=FRAME_WINDOW))
# last_log_time = {}  # plate -> datetime of last DB write

# tz = datetime.now().astimezone().tzinfo  # preserve timezone info (if needed)

# class Command(BaseCommand):
#     help = "Run entrance camera loop with multi-frame confirmation and regex validation"

#     # inside your Command class, before handle()
#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--source', '-s',
#             help='Video source: camera index (int) or video file path (string)',
#             default='0'
#         )

#     def handle(self, *args, **options):
#         src = options['source']
#         # if it’s all digits, treat as camera index
#         try:
#             src = int(src)
#         except ValueError:
#             # assume it's a file in parking/videos/
#             video_dir = os.path.join(settings.BASE_DIR, 'parking', 'videos')
#             src = os.path.join(video_dir, src)

#         cap = cv2.VideoCapture(src)
#         if not cap.isOpened():
#             self.stdout.write(self.style.ERROR("Camera not accessible. {src}"))
#             return

#         self.stdout.write(self.style.SUCCESS("Starting entrance monitoring..."))

#         # cv2.namedWindow("Entrance Monitor", cv2.WINDOW_NORMAL)
#         # # Optional: to make sure window events are threaded:
#         cv2.startWindowThread()

#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 # continue
#                 break

#             # 1. Run OCR on full frame
#             raw_plate = detect_and_read_plate(frame)

#             # Show the current frame (optional)
#             # print(f"Frame shape: {frame.shape}")
#             cv2.imshow("Entrance Monitor", frame)
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break

#             if not raw_plate:
#                 # no plate detected this frame
#                 print("no plate detected this frame")
#                 continue

#             plate = raw_plate.strip().upper()

#             # 2. Validate format with regex
#             if not PLATE_REGEX.fullmatch(plate):
#                 print("plate is not in regex format")
#                 continue

#             # 3. Multi-frame confirmation
#             win = plate_windows[plate]
#             win.append(plate)
#             if len(win) < FRAME_WINDOW or len(set(win)) > 1:
#                 # Not yet stable
#                 print('Not yet stable')
#                 continue

#             # 4. Confirmed: check cache and write to DB
#             now = timezone.now()
#             last_time = last_log_time.get(plate)
#             if not last_time or (now - last_time).total_seconds() > CACHE_EXPIRY_SECONDS:
#                 existing = ParkingRecord.objects.filter(plate=plate, exit_time__isnull=True).first()
#                 if not existing:
#                     ParkingRecord.objects.create(plate=plate, entry_time=now)
#                     self.stdout.write(self.style.SUCCESS(f"Logged new entry for {plate}"))
#                 else:
#                     self.stdout.write(f"{plate} already logged. Skipping.")
#                 last_log_time[plate] = now


#             # brief pause to reduce CPU
#             time.sleep(0.05)

#         cap.release()
#         cv2.destroyAllWindows()
#         self.stdout.write(self.style.SUCCESS("Entrance monitoring stopped."))












# # ---------------------------------------------------------------



# # File: parking/management/commands/entrance_monitor.py
# # import time
# # import cv2
# # import re
# # from collections import deque, defaultdict
# # from django.utils import timezone
# # from django.core.management.base import BaseCommand
# # from parking.models import ParkingRecord

# # from detectors.alpr import detect_and_read_plate  # easyocr reader
# # # from detectors.yolo_detector import detect_plate_boxes

# # # --- Configuration ---
# # FRAME_WINDOW = 5
# # CACHE_EXPIRY_SECONDS = 10
# # # Indian plate: 2 letters, 2 digits, 1-2 letters, 4 digits
# # PLATE_PATTERN = re.compile(r"[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}")

# # # State
# # plate_windows = defaultdict(lambda: deque(maxlen=FRAME_WINDOW))
# # last_log_time = {}

# # class Command(BaseCommand):
# #     help = "Run entrance camera loop with YOLO-based cropping + OCR"

# #     def handle(self, *args, **options):
# #         cap = cv2.VideoCapture(0)
# #         if not cap.isOpened():
# #             self.stdout.write(self.style.ERROR("Camera not accessible."))
# #             return

# #         # # Create window for preview
# #         # cv2.namedWindow("Entrance Monitor", cv2.WINDOW_NORMAL)

# #         self.stdout.write(self.style.SUCCESS("Starting entrance monitoring..."))

# #         while True:
# #             ret, frame = cap.read()
# #             if not ret:
# #                 continue

# #             # inside your while True loop:

# #             # 1) Detect plate bounding boxes with YOLO
# #             plates = detect_and_read_plate(frame)
# #             # Filter out any malformed outputs
# #             valid = [b for b in plates
# #                     if isinstance(b, (list,tuple)) and len(b) >= 5]
# #             if not valid:
# #                 print(f"[WARN] Plate detector returned unexpected entries: {plates!r}")
# #                 continue

# #             # 2) Pick the box with highest confidence
# #             x1, y1, x2, y2, conf = max(valid, key=lambda b: b[4])

# #             # Draw it so you can see where it found the plate
# #             cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
# #             cv2.putText(frame, f"Conf: {conf:.2f}", (x1, y1-5),
# #                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

# #             # …then crop, OCR, debounce, write to DB, etc.…


# #             # # 1) Detect plate bounding boxes with YOLO
# #             # plates = detect_and_read_plate(frame)
# #             # if not plates:
# #             #     continue

# #             # # 2) Pick the highest-confidence box
# #             # x1, y1, x2, y2, _ = max(plates, key=lambda b: b[4])
# #             # plate_roi = frame[y1:y2, x1:x2]

# #             # Optional: crop out left portion (blue "IND" strip)
# #             h, w = plate_roi.shape[:2]
# #             crop = plate_roi[:, int(0.15 * w):]

# #             # 3) OCR on the cropped ROI
# #             gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
# #             ocr_results = reader.readtext(gray)

# #             # 4) Regex-extract the 10-character plate
# #             plate = None
# #             for _, txt, conf in sorted(ocr_results, key=lambda x: -x[2]):
# #                 if conf < 0.5:
# #                     continue
# #                 cand = txt.replace(" ", "").upper()
# #                 m = PLATE_PATTERN.search(cand)
# #                 if m:
# #                     plate = m.group(0)
# #                     break
# #             if not plate:
# #                 continue

# #             # # 5) Multi-frame confirmation
# #             # win = plate_windows[plate]
# #             # win.append(plate)
# #             # if len(win) < FRAME_WINDOW or len(set(win)) > 1:
# #             #     continue

# #             # 6) Confirmed: cache-check and DB write
# #             now = timezone.now()
# #             last_time = last_log_time.get(plate)
# #             if not last_time or (now - last_time).total_seconds() > CACHE_EXPIRY_SECONDS:
# #                 existing = ParkingRecord.objects.filter(plate=plate, exit_time__isnull=True).first()
# #                 if not existing:
# #                     ParkingRecord.objects.create(plate=plate, entry_time=now)
# #                     self.stdout.write(self.style.SUCCESS(f"Logged new entry for {plate}"))
# #                 else:
# #                     self.stdout.write(f"{plate} already logged. Skipping.")
# #                 last_log_time[plate] = now

            
# #             # 0) Always show the camera feed and handle 'q' to quit
# #             cv2.imshow("Entrance Monitor", frame)
# #             if cv2.waitKey(1) & 0xFF == ord('q'):
# #                 break

# #         cap.release()
# #         cv2.destroyAllWindows()
# #         self.stdout.write(self.style.SUCCESS("Entrance monitoring stopped."))

import cv2, time, re, os
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.conf import settings
from parking.models import ParkingRecord
from detectors.alpr import detect_and_read_plate

# ─── CONFIG ──────────────────────────────────────────────────────
OCR_INTERVAL   = 0.5      # seconds between OCR runs
DISPLAY_INTERVAL = 0.5    # seconds between UI updates
CACHE_EXPIRY   = 10       # seconds before re-logging same plate
PLATE_REGEX = re.compile(
    r"^[A-Z0-9]{2,3}[ -]?[A-Z0-9]{2,3}[ -]?[A-Z0-9]{3,5}$",
    re.IGNORECASE
)

last_log_time = {}
last_ocr = last_disp = 0.0

class Command(BaseCommand):
    help = "Entrance: OCR & display both at 0.5 s intervals"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source","-s",
            help="Camera index or video file under parking/videos/",
            default="0"
        )

    def handle(self, *args, **options):
        global last_ocr, last_disp
        last_ocr  = time.monotonic() - OCR_INTERVAL
        last_disp = time.monotonic() - DISPLAY_INTERVAL

        # Resolve source
        src = options["source"]
        try:
            src = int(src)
        except ValueError:
            video_dir = os.path.join(settings.BASE_DIR, "parking", "videos")
            src = os.path.join(video_dir, src)

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            self.stdout.write(self.style.ERROR(f"Cannot open {src}"))
            return

        self.stdout.write(self.style.SUCCESS("Starting entrance monitor..."))

        while True:
            ret, full = cap.read()
            if not ret:
                break  # end of stream

            now = time.monotonic()

            # 1) OCR every OCR_INTERVAL seconds
            if now - last_ocr >= OCR_INTERVAL:
                last_ocr = now
                raw = detect_and_read_plate(full)
                if raw:
                    plate = raw.strip().upper()
                    if PLATE_REGEX.fullmatch(plate):
                        ts = timezone.now()
                        last = last_log_time.get(plate)
                        if not last or (ts - last).total_seconds() > CACHE_EXPIRY:
                            exists = ParkingRecord.objects.filter(
                                plate=plate, exit_time__isnull=True
                            ).first()
                            if not exists:
                                ParkingRecord.objects.create(
                                    plate=plate, entry_time=ts
                                )
                                self.stdout.write(
                                    self.style.SUCCESS(f"[ENTRY] {plate} @ {ts:%H:%M:%S}")
                                )
                            else:
                                self.stdout.write(f"[ENTRY] {plate} already inside")
                            last_log_time[plate] = ts

            # 2) Update display every DISPLAY_INTERVAL seconds
            if now - last_disp >= DISPLAY_INTERVAL:
                last_disp = now
                # you could downscale here if needed; using full for clarity
                cv2.imshow("Entrance Monitor", full)
                # use a short waitKey so UI remains responsive
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        cap.release()
        cv2.destroyAllWindows()
        self.stdout.write(self.style.SUCCESS("Entrance monitor stopped."))
