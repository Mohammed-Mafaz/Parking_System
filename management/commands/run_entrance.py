from django.core.management.base import BaseCommand
from parking.models import ParkingRecord
from detectors.alpr import detect_and_read_plate
from datetime import datetime
import cv2, time

class Command(BaseCommand):
    help = "Run entrance camera loop"

    def handle(self, *args, **options):
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            plate = detect_and_read_plate(frame)
            if plate:
                ParkingRecord.objects.create(
                  plate=plate,
                  entry_time=datetime.utcnow()
                )
                self.stdout.write(f"Logged {plate}")
                time.sleep(1)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()

