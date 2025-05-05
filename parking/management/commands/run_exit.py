# cameras/exit.py
import cv2
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from detectors.alpr import detect_and_read_plate
from parking.models import ParkingRecord

class Command(BaseCommand):
    help = 'Monitor exit camera and record vehicle exits'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting exit camera monitoring...'))

        # Call the function to monitor exit camera
        run_exit_camera(source=0)  # You can change the source if needed

        self.stdout.write(self.style.SUCCESS('Exit camera monitoring completed'))


def run_exit_camera(source):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Error: Could not open video source. {source}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break

        # Detect the plate using the ALPR system
        plate = detect_and_read_plate(frame)
        if plate:
            plate = plate.strip().upper()
            print(f"Detected plate: {plate}") 
            # Fetch the latest open parking record for this plate
            rec = ParkingRecord.objects.filter(plate=plate, exit_time=None).order_by('-entry_time').first()

            if rec:
                rec.exit_time = datetime.utcnow()  # Update exit time
                rec.save()  # Save the updated record to the database
                print(f"[Exit] {plate} exited at {rec.exit_time}")

            time.sleep(1)  # Wait for a moment before reading the next frame

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture and close any OpenCV windows
    cap.release()
    cv2.destroyAllWindows()

