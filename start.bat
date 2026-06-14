@echo off
echo 🪨 Starting Grey Rock Strategy...

echo Starting Python backend...
cd backend
start "Grey Rock Backend" cmd /k "pip install -r requirements.txt && python app.py"
cd ..

timeout /t 3 /nobreak >nul

echo Starting React frontend...
cd frontend
start "Grey Rock Frontend" cmd /k "npm install && npm start"
cd ..

echo.
echo ✅ Grey Rock Strategy starting!
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:5000
echo.
pause
