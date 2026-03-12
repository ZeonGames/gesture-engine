@echo off
title GestureEngine
color 0C
echo.
echo  +================================================+
echo  ^|      GESTURE ENABLEMENT LAYER                  ^|
echo  ^|  Universal hand gesture controller              ^|
echo  +------------------------------------------------+
echo  ^|  RIGHT HAND  -^>  mouse / aim                   ^|
echo  ^|  LEFT HAND   -^>  keyboard / actions             ^|
echo  +================================================+
echo.
echo [*] Installing / updating dependencies...
py -3.12 -m pip install -r requirements.txt --quiet
echo [*] Launching GestureEngine...
echo.
echo  TIP: Run your app in WINDOWED BORDERLESS mode
echo  TIP: Use the overlay KEY MAP button to remap gestures
echo.
py -3.12 main.py
pause
