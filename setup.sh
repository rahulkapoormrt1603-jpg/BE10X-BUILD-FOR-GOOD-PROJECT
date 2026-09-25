#!/bin/bash
echo "Setting up UNStammer Speech Assessment..."
echo

echo "[1/4] Setting up backend..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
cd ..

echo
echo "[2/4] Setting up frontend..."
cd frontend
npm install
cd ..

echo
echo "[3/4] Setup complete!"
echo
echo "To run the project:"
echo
echo "1. Start backend (in one terminal):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   flask run"
echo
echo "2. Start frontend (in another terminal):"
echo "   cd frontend"
echo "   npm start"
echo
echo "Backend will run on http://localhost:5000"
echo "Frontend will run on http://localhost:3000"