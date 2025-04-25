from django.core.management.base import BaseCommand
from parking.models import ParkingRecord
from detectors.alpr import detect_and_read_plate
from datetime import datetime
from django.utils import timezone
import cv2, time

class Command(BaseCommand):
    help = "Run entrance camera loop"

    def handle(self, *args, **options):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.stdout.write(self.style.ERROR("Camera not accessible."))
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            plate = detect_and_read_plate(frame)
            if plate:
                plate = plate.strip().upper()
                existing = ParkingRecord.objects.filter(plate=plate, exit_time__isnull=True).first()
                if not existing:
                    ParkingRecord.objects.create(
                        plate=plate,
                        entry_time=timezone.now()
                    )
                    self.stdout.write(self.style.SUCCESS(f"Logged new entry for {plate}"))
                else:
                    self.stdout.write(f"{plate} already logged. Skipping.")

                time.sleep(1)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

