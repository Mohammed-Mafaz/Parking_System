# cameras/parking_section.py
import cv2
import numpy as np
from datetime import datetime
from shapely.geometry import Point, Polygon
from detectors.yolo_car_detector import detect_vehicles
from detectors.alpr import detect_and_read_plate
from db import Session, ParkingRecord

# define your polygons per section
SECTION_NAME = "Section A"
SLOT_POLYGONS = {
    "SlotA": [(100,100), (200,100), (200,200), (100,200)],
    "SlotB": [(300,100), (400,100), (400,200), (300,200)],
    # …
}

def run_parking_section(source=1):
    cap = cv2.VideoCapture(source)
    session = Session()
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # detect vehicles
        dets = detect_vehicles(frame)
        for x1,y1,x2,y2,_,_ in dets:
            cx, cy = (x1+x2)//2, (y1+y2)//2
            pt = Point(cx,cy)

            for slot_name, coords in SLOT_POLYGONS.items():
                poly = Polygon(coords)
                if poly.contains(pt):
                    cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
                    cv2.putText(frame, slot_name, (x1,y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

                    # attempt a plate read
                    plate = detect_and_read_plate(frame[y1:y2, x1:x2])
                    if plate:
                        # update the first open record for this plate
                        rec = session.query(ParkingRecord)\
                            .filter_by(plate=plate, slot=None).first()
                        if rec:
                            rec.section = SECTION_NAME
                            rec.slot    = slot_name
                            session.commit()
                            print(f"[{SECTION_NAME}] {plate} → {slot_name}")
                    break

        cv2.imshow(f"Parking {SECTION_NAME}", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
