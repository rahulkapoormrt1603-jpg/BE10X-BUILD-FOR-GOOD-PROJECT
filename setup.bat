@echo off
echo Setting up UNStammer Speech Assessment...
echo.

echo [1/4] Setting up backend...
cd backend
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
cd ..

echo.
echo [2/4] Setting up frontend...
cd frontend
npm install
cd ..

echo.
echo [3/4] Setup complete!
echo.
echo To run the project:
echo.
echo 1. Start backend (in one terminal):
echo    cd backend
echo    venv\Scripts\activate
echo    flask run
echo.
echo 2. Start frontend (in another terminal):
echo    cd frontend
echo    npm start
echo.
echo Backend will run on http://localhost:5000
echo Frontend will run on http://localhost:3000
echo.
pause