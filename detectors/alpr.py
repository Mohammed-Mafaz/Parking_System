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


# # detectors/alpr.py
# import cv2
# import numpy as np
# from easyocr import Reader
# import re

# # Initialize EasyOCR reader once
# reader = Reader(["en"], gpu=False)

# # Allow only Indian plate characters and digits, optional separators
# ALLOWLIST = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
# PLATE_REGEX = re.compile(r"^[A-Z0-9]{2,3}[ -]?[A-Z0-9]{2,3}[ -]?[A-Z0-9]{3,5}$", re.IGNORECASE)


# def ocr_plate_from_frame(frame):
#     """
#     Full pipeline: detect plate bbox, crop, preprocess, OCR, and validate.
#     Returns cleaned plate text or None.
#     """
#     from detectors.yolo_detector import detect_plate_bbox

#     # 1. Detect bounding box
#     bbox = detect_plate_bbox(frame)
#     if bbox is None:
#         return None
#     x1, y1, x2, y2 = bbox

#     # 2. Crop
#     roi = frame[y1:y2, x1:x2]
#     if roi.size == 0:
#         return None

#     # 3. Upscale if too small
#     h, w = roi.shape[:2]
#     if w < 200:
#         roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

#     # 4. Preprocess: grayscale, equalize, threshold
#     gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
#     gray = cv2.equalizeHist(gray)
#     _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

#     # 5. OCR with allowlist
#     texts = reader.readtext(thresh, detail=0, allowlist=ALLOWLIST)
#     if not texts:
#         return None

#     # 6. Clean & validate
#     for txt in texts:
#         txt = txt.strip().upper().replace(' ', '')
#         # common misreads
#         txt = txt.replace('B', '8').replace('S', '5').replace('O', '0')
#         if PLATE_REGEX.fullmatch(txt):
#             return txt
#     return None