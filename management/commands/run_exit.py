# cameras/exit.py
import cv2, time
from datetime import datetime
from detectors.alpr import detect_and_read_plate
from db import Session, ParkingRecord

def run_exit_camera(source=2):
    cap = cv2.VideoCapture(source)
    session = Session()
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        plate = detect_and_read_plate(frame)
        if plate:
            rec = session.query(ParkingRecord)\
                .filter_by(plate=plate, exit_time=None).order_by(ParkingRecord.entry_time.desc())\
                .first()
            if rec:
                rec.exit_time = datetime.utcnow()
                session.commit()
                print(f"[Exit] {plate} exited at {rec.exit_time}")
            time.sleep(1)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
