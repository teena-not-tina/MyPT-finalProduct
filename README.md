# B-Fit CV-Service

## What is this?

The **B-Fit CV-Service** is a FastAPI-based backend providing computer vision features for the B-Fit health app.  
It analyzes exercise posture, counts reps, and supports real-time feedback using pose estimation and object detection.

## Project Structure

```
cv-service/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
└── modules/
    ├── exercise_analyzer.py
    ├── exercise_api.py
    ├── workout_routine_api.py
    └── exercise_websocket.py
```

## How to Run

1. **Install dependencies**  
   (Recommended: use a virtual environment)
   ```
   pip install -r requirements.txt
   ```

2. **Set up environment variables**  
   If needed, copy `.env.example` to `.env` and edit as required.

3. **Start the server**
   ```
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

4. **Access API docs**  
   Open [http://localhost:8001/docs](http://localhost:8001/docs) in your browser.

## API Endpoints

- `GET /`  
  Service info and available endpoints.

- `GET /health`  
  Health check for the service.

- `GET /exercise/exercises`  
  List available exercise types.

- `WebSocket /exercise/live-analysis`  
  Real-time exercise analysis.  
  - **Client sends:**  
    ```json
    {
      "type": "frame",
      "exercise": "PUSHUP",
      "data": "base64_encoded_image"
    }
    ```
  - **Server responds:**  
    ```json
    {
      "type": "feedback",
      "feedback": { ... },
      "annotated_frame": "base64_encoded_image"
    }
    ```

- (Other endpoints may exist for workout routines, see `/docs` for full list.)

## Notes

- This service is designed to be used with the B-Fit frontend.
- For development, make sure your frontend URL is allowed in CORS settings in `main.py`.