from ultralytics import YOLO

model = YOLO("yolov8s.pt")  # or yolov8n/yolov8m as you need

def detect_vehicles(frame):
    """
    Returns list of (x1,y1,x2,y2, class_name, confidence)
    for each car/truck/bus detected.
    """
    result = model(frame)[0]
    dets = []
    for box in result.boxes:
        cls = int(box.cls)
        name = model.names[cls]
        if name in ("car","truck","bus"):
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            dets.append((x1,y1,x2,y2, name, conf))
    return dets
