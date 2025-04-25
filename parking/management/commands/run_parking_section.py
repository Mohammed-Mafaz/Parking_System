import cv2
import numpy as np
from datetime import datetime
from shapely.geometry import Point, Polygon
from django.core.management.base import BaseCommand
from detectors.yolo_detector import detect_vehicles
from detectors.alpr import detect_and_read_plate
from parking.models import ParkingRecord
from datetime import datetime, timedelta

# Cache to remember plate-slot assignments
plate_cache = {}
CACHE_EXPIRY_SECONDS = 10  # Cache refresh time

# Define your polygons per section
SECTION_NAME = "Section A"
SLOT_POLYGONS = {
    "SlotA": [(100, 100), (200, 100), (200, 200), (100, 200)],
    "SlotB": [(300, 100), (400, 100), (400, 200), (300, 200)],
    # Add more slots as needed
}

def run_parking_section(source=1):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break

        # Detect vehicles using your YOLO detector
        dets = detect_vehicles(frame)

        if not dets:
            print("No vehicles detected in this frame.")
        else:
            for x1, y1, x2, y2, _, _ in dets:
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                pt = Point(cx, cy)

                for slot_name, coords in SLOT_POLYGONS.items():
                    poly = Polygon(coords)

                    if poly.contains(pt):
                        # Visual aid: draw bounding box and label
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, slot_name, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                        plate = detect_and_read_plate(frame[y1:y2, x1:x2])
                        if plate:
                            plate = plate.strip().upper()
                            now = datetime.now()
                            last_entry = plate_cache.get(plate)

                            if (
                                not last_entry or
                                last_entry["slot"] != slot_name or
                                (now - last_entry["timestamp"]).total_seconds() > CACHE_EXPIRY_SECONDS
                            ):
                                rec = ParkingRecord.objects.filter(plate=plate, slot=None, exit_time=None).first()
                                if rec:
                                    rec.section = SECTION_NAME
                                    rec.slot = slot_name
                                    rec.save()
                                    print(f"[{SECTION_NAME}] {plate} → {slot_name}")

                                    # Update cache
                                    plate_cache[plate] = {"slot": slot_name, "timestamp": now}
                        break  # No need to check other slots once we've matched the vehicle

        # Determine occupied slots
        occupied_slots = {info["slot"] for info in plate_cache.values()}

        # Draw slot polygons (green if free, red if taken)
        for slot_name, coords in SLOT_POLYGONS.items():
            color = (0, 255, 0) if slot_name not in occupied_slots else (0, 0, 255)
            pts = np.array(coords, np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)
            cv2.putText(frame, slot_name, coords[0],
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Show the frame with bounding boxes and labels
        cv2.imshow(f"Parking {SECTION_NAME}", frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture and close all windows
    cap.release()
    cv2.destroyAllWindows()



class Command(BaseCommand):
    help = 'Run parking section monitoring'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting parking section monitoring...'))
        
        # Call the function that runs the parking section logic
        run_parking_section(source=0)  # You can change the source as needed

        self.stdout.write(self.style.SUCCESS('Parking section monitoring completed'))
