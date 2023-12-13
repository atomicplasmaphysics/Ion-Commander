# Ion Commander

Quick and dirty python code for commanding our Ions in the LaserLab 💡⚔

## Examples

Basic examples are provided in the `saves` folder:

- Argon beam on Tungsten target (`Ar_on_W`)
- Hydrogen and Argon beam on layered Iron and Tungsten target under 60deg (`H_Ar_on_Fe_W_60deg`)

## Installation

The GUI needs [Python ≥ 3.11](https://www.python.org/downloads/) with following packages installed:

```
Package     Version
----------- ----------
PyQt6       6.5.2
pyqtgraph   0.13.3
numpy       1.24.3
scipy       1.10.1
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
You are a big boy 🐶, there is no manual needed, you can figure it out yourself

## TODOs
- [ ] Make LogNorm stuff working
- [ ] Better fitting routine and better starting parameters
- [ ] Make the current Data-Analysis application as a subtab
- [ ] Build a controll subtab (Pressure, Voltage, Laser)
- [ ] Logg everything in the controlltab
- [ ] Build a measure subtab (for TAC)
- [ ] Build a measure subtab (for TDC)
- [ ] Build a measure subtab (for NDIGO - if NDIGO is built)
- [ ] Build a laser subtab
- [ ] Make better logo and splash screen