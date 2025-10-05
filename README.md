# 🅿️ Intelligent Multi-Floor Parking System using ANPR and OCR

## 🎓 Project Information

This project was developed as a Final Year Project for the Bachelor of Engineering in Computer Science and Engineering (CSE) program.  
It demonstrates the integration of Computer Vision, Deep Learning, and Web Technologies to build an automated parking management system.
---


## 🚀 Overview
**ParkingSystem** is a Django-powered smart parking management solution that uses **Automatic Number Plate Recognition (ANPR)** to detect and manage vehicle entries and exits. It integrates **YOLOv8** for license plate detection, enabling real-time automation of parking workflows.

This project provides a complete system — from ANPR-based entry/exit management to dashboard analytics and API integration.

---

## 🧩 Features
- 🚘 **Automatic Vehicle Detection & Recognition (ANPR)**
- 🎥 Real-time video frame processing using YOLOv8
- 🧠 Deep learning models: `license_plate_detector.pt` and `yolov8n.pt`
- 🏢 Multi-section parking support
- 📊 Interactive admin dashboard for parking slot management
- 🔌 REST API endpoints (for IoT integration)
- 🔔 WebSocket-based event broadcasts
- 🗂️ Command scripts for automated ANPR workflows
- 🧱 Modular Django app architecture

---

## 🗂️ Project Structure
```
ParkingSystem/
├── manage.py
├── utils.py
├── parkingSystem/                     # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── parking/               # Core app
│   ├── models.py
│   ├── views.py
│   ├── api_views.py
│   ├── serializers.py
│   ├── routing.py
│   ├── templates/parking/
│   ├── management/commands/
│   │   ├── entrance_anpr.py
│   │   ├── exit_anpr.py
│   │   ├── run_all_anpr.py
│   │   └── parking_section_anpr.py
│   ├── migrations/
│   └── ...
├── models/                # AI Models
│   ├── yolov8n.pt
│   └── license_plate_detector.pt
└── sort/
    └── sort.py
```

---

## ⚙️ Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/ParkingSystem.git
cd ParkingSystem
```

### 2️⃣ Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # (Linux/Mac)
venv\Scripts\activate         # (Windows)
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5️⃣ Start the Django development server
```bash
python manage.py runserver
```

---

## 🤖 Running ANPR Commands
The project provides Django management commands to automate ANPR workflows:
```bash
python manage.py entrance_anpr
python manage.py exit_anpr
python manage.py run_all_anpr
```

---

## 📡 API Endpoints
| Endpoint | Description |
|-----------|--------------|
| `/api/parking/` | Get all parking slots |
| `/api/vehicles/` | Manage vehicle data |
| `/api/entry/` | Record vehicle entry |
| `/api/exit/` | Record vehicle exit |
| `/dashboard/` | Admin and analytics UI |

*(Exact routes may vary based on `urls.py` and `dashboard_urls.py` configuration.)*

---

## 🧠 Model Details
| Model | Purpose |
|--------|----------|
| `yolov8n.pt` | Vehicle detection backbone |
| `license_plate_detector.pt` | License plate region localization |

---

## 🧰 Tech Stack
- **Backend:** Django, Django REST Framework
- **AI/ML:** YOLOv8 (PyTorch)
- **Database:** SQLite / PostgreSQL
- **Frontend:** HTML, Bootstrap (Django templates)
- **Communication:** Django Channels (WebSockets)

---

## 🙏 Acknowledgment
This project was created as part of the **Final Year Project** for the **Bachelor of Engineering in Computer Science and Engineering (CSE)** program.  
Special thanks to faculty mentors and teammates for their guidance and support.
