# detectors/alpr.py
import easyocr
import cv2
reader = easyocr.Reader(["en"])  # you can add other langs

def detect_and_read_plate(frame):
    # frame: OpenCV BGR array
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = reader.readtext(gray)
    # pick the text box with highest confidence and plausible length
    for bbox, text, conf in sorted(results, key=lambda x: -x[2]):
        if len(text) >= 5 and conf > 0.5:
            return text.replace(" ", "")
    return None
