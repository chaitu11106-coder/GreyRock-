#!/bin/bash
echo "🪨 Starting Grey Rock Strategy..."

# Start backend
echo "→ Starting Python backend on port 5000..."
cd backend
pip install -r requirements.txt -q
python app.py &
BACKEND_PID=$!
cd ..

# Wait for backend
sleep 2

# Start frontend
echo "→ Starting React frontend on port 3000..."
cd frontend
npm install --silent
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Grey Rock Strategy running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT
wait
