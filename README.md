# 🏍️ Bike Helmet Detection System

This project detects motorcyclists without helmets and extracts license plate details using ML models.  

---

## 📂 Project Folders
The project structure is as follows:
```
BIKEHELMET/
│-- __pycache__/
│-- cropimages/
│-- logs/
│-- Media/
│-- output/
│-- Snaps/
│-- static/
│   │-- app.js
│   │-- main.css
│-- templates/
│   │-- index.html
│-- Weights/
│   │-- BikeFaceHelmet/
│       │-- best.pt
│   │-- LetterPlate/
│   │-- NoPlate/
│   │-- NoPlate1/
│   │-- yolov8l.pt
│-- app.py              # Main entry point
│-- app1.py             # Alternative entry with filtration modifications
│-- HelmetDetector.py   # Core detection logic (hardcoded video path)
│-- HelmetDetector1.py
│-- Detected_Plates.csv # Stores detected number plate details (temp)
│-- requirment.txt      # Project dependencies
│-- venv/               # Virtual environment (local use only)
```

---

## ⚙️ How to Run

1. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

2. **Activate the environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

3. **Install required libraries**
   ```bash
   pip install -r requirment.txt
   ```

4. **Run the main project**
   ```bash
   python app.py
   ```

5. **Alternative run (with filtration modifications)**
   ```bash
   python app1.py
   ```

---

## 🎥 Input Videos
- The video source is **hardcoded** inside `HelmetDetector.py`.  
- To test with a different video, update the file path inside `HelmetDetector.py`.  

---

## 📌 Notes
- Detected number plates are saved in the MySQL database.  

	so database creation mandatory using below query

	Create database BikeMonitoring;
	USE BikeMonitoring;


	CREATE TABLE IF NOT EXISTS Plates (
 	id INT AUTO_INCREMENT PRIMARY KEY,
  	frame_number INT NOT NULL,
  	plate_text VARCHAR(64),
  	plate_image_path VARCHAR(255),
  	detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);

CREATE INDEX idx_detected_at ON Plates(detected_at);
CREATE INDEX idx_plate_text ON Plates(plate_text);


- Pretrained YOLO weights are stored in the `Weights/` folder.  
- The web app uses Flask with HTML templates, CSS, and JS for the front-end.  
