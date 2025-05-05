import cv2, time
import numpy as np
from datetime import datetime, timedelta
from shapely.geometry import Point, Polygon
from django.core.management.base import BaseCommand
from parking.models import ParkingRecord
from detectors.yolo_detector import detect_plate_bbox
from detectors.alpr            import detect_and_read_plate

# ——— CONFIG ——————————————————————————————————————
SECTION_NAME    = "Section A"
SLOT_POLYGONS   = {
    "A1": [[15,400],[15,765],[324,765],[324,400]],
    "A2": [[331,400],[331,765],[636,765],[636,400]],
    "A3": [[643,400],[643,765],[948,765],[948,400]],
    "A4": [[957,400],[957,765],[1016,765],[1016,400]],
}
DETECT_DELAY    = timedelta(seconds=10)
UNMAP_DELAY     = timedelta(seconds=10)

plate_cache = {}

def run_parking_section(source):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Error: Could not open source:", source)
        return

    # Precompute slot polygons and ROIs
    slot_polys = {n: Polygon(c) for n,c in SLOT_POLYGONS.items()}
    slot_rois  = {}
    for name, coords in SLOT_POLYGONS.items():
        xs = [p[0] for p in coords]; ys = [p[1] for p in coords]
        slot_rois[name] = (min(xs), min(ys), max(xs), max(ys))

    frame_count = 0
    DETECTION_EVERY_N = 5

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        now = datetime.now()

        # Only run detection every N frames
        if frame_count % DETECTION_EVERY_N == 0:

            # For each slot...
            for slot_name, (x0, y0, x1, y1) in slot_rois.items():
                roi = frame[y0:y1, x0:x1]
                if roi.size == 0:
                    continue

                # 1) detect plate bbox in this slot ROI
                b = detect_plate_bbox(roi)
                print(f"Slot {slot_name}: detect_plate_bbox -> {b}")
                if not b:
                    continue

                bx1, by1, bx2, by2 = b
                # Map back to full frame coords
                fx1, fy1 = x0 + bx1, y0 + by1
                fx2, fy2 = x0 + bx2, y0 + by2

                # 2) OCR only on that crop
                plate_roi = frame[fy1:fy2, fx1:fx2]
                plate = detect_and_read_plate(plate_roi)
                print(f"  OCR on slot {slot_name} ROI -> {plate}")
                if not plate:
                    print("no plate")
                    continue
                plate = plate.strip().upper()

                # 3) Verify center in polygon
                cx, cy = (fx1+fx2)//2, (fy1+fy2)//2
                if not slot_polys[slot_name].contains(Point(cx, cy)):
                    continue

                # 4) Update cache & DB mapping after stable detection
                info = plate_cache.get(plate)
                if not info:
                    plate_cache[plate] = {
                        "slot": slot_name,
                        "first_seen": now,
                        "last_seen": now,
                        "mapped": False
                    }
                    info = plate_cache[plate]
                else:
                    if info["slot"] != slot_name:
                        info.update({
                            "slot": slot_name,
                            "first_seen": now,
                            "mapped": False
                        })
                    info["last_seen"] = now

                # If held for DETECT_DELAY, write to DB
                if (not info["mapped"] 
                    and now - info["first_seen"] >= DETECT_DELAY):
                    rec = ParkingRecord.objects.filter(
                        plate=plate,
                        exit_time__isnull=True,
                        slot__isnull=True
                    ).first()
                    if rec:
                        rec.section = SECTION_NAME
                        rec.slot    = slot_name
                        rec.save()
                        print(f"[MAPPED] {plate} → {slot_name}")
                        info["mapped"] = True

                # annotate
                cv2.rectangle(frame, (fx1,fy1),(fx2,fy2),(0,255,0),2)
                cv2.putText(
                    frame, f"{plate}:{slot_name}",
                    (fx1, fy1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0,255,0),2
                )

        # 5) Unmap stale plates
        for plate, info in list(plate_cache.items()):
            if info["mapped"] and now - info["last_seen"] >= UNMAP_DELAY:
                rec = ParkingRecord.objects.filter(
                    plate=plate,
                    exit_time__isnull=True,
                    slot=info["slot"]
                ).first()
                if rec:
                    rec.slot = None
                    rec.save()
                    print(f"[UNMAPPED] {plate} left {info['slot']}")
                del plate_cache[plate]

        # 6) Draw slot outlines
        occupied = {i["slot"] for i in plate_cache.values() if i["mapped"]}
        for slot_name, coords in SLOT_POLYGONS.items():
            pts   = np.array(coords, np.int32).reshape((-1,1,2))
            color = (0,255,0) if slot_name not in occupied else (0,0,255)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.putText(
                frame, slot_name, tuple(coords[0]),
                cv2.FONT_HERSHEY_SIMPLEX,0.5,color,1
            )

        # 7) Show & quit
        cv2.imshow(f"Parking {SECTION_NAME}", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# ——— DJANGO COMMAND ——————————————————————————————————————
class Command(BaseCommand):
    help = "Run parking section monitoring"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", "-s",
            help="Camera index or video file path",
            default="0"
        )

    def handle(self, *args, **options):
        src = options["source"]
        try:
            src = int(src)
        except ValueError:
            # if not int, assume file path
            pass

        self.stdout.write(self.style.SUCCESS("Starting parking section monitoring..."))
        run_parking_section(src)
        self.stdout.write(self.style.SUCCESS("Parking section monitoring completed"))
