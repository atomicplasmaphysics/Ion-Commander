# Ion Commander
Quick and dirty python code for commanding our Ions in the LaserLab 💡⚔

## Installation
The GUI needs [Python ≥ 3.11](https://www.python.org/downloads/) with following packages installed:

```
Package     Version
----------- ----------
PyQt6       6.5.2
pyqtgraph   0.13.3
numpy       1.24.3
scipy       1.10.1
matplotlib  3.8.3
pyserial    3.5
```

To execute the GUI, download all files from this repository and execute the `main.py` file from the console.
```bash
>> python3 main.py
```

### Alternative Installation
If one wishes to execute the GUI without calling it from the console, [PyInstaller](https://pyinstaller.org/en/stable/) can be used to compile all needed python files into one executable.
After executing the `compile\pyinstaller.py` file (same packages and package PyInstaller are needed), a `Ion Commander.exe` will be created in the main folder.
For further information read the description of the `compile\pyinstaller.py` file.

## Manual
You are a big boy 🐶, there is no manual needed, you can figure it out yourself.
Maybe get some popcorn while figuring it out 🍿

## TODOs
- [x] Make LogNorm stuff working
- [x] Better fitting routine and better starting parameters
- [x] Make the current Data-Analysis application as a subtab
- [x] Build a control subtab (Pressure, Voltage, Laser)
- [x] Logg everything in the control-tab
- [ ] Build a measure subtab (for TAC)
- [ ] Build a measure subtab (for TDC)
- [ ] Build a measure subtab (for NDIGO - if NDIGO is built)
- [x] Build a laser subtab
- [x] Make better logo and splash screen
- [ ] Start TDC software automatic with a button press and safe it automatically
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 


## BUGs
- [ ] Pack images in executable - otherwise not shown
