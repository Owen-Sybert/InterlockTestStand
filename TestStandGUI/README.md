# Test Stand GUI

## How to Edit Code

This program was created in VSCode with Anaconda.
The conda env is saved to a .yml file. To activate the conda env:
`conda env create -f environment.yml` followed by `conda activate teststandgui`

If you edit the environment (adding packages, etc) you should re-export the environment via:
`conda env export > environment.yml` in terminal.



## Setup for raspberryPi terminal

bash commands in terminal to get the ball rolling
#conda env create -f environment.yml
#conda activate teststandgui
#python main.py

# TROUBLESHOOT 1. "ModuleNotFoundError: No module named 'PyQt6'"
See the following ChatGPT conversation for the troubleshooting process: https://chatgpt.com/share/6a3a98b3-4200-83ea-941c-3eff7ba51384

So PyQt6 is installed, but not in the Python interpreter VS Code used to run landing.py.

Do this in VS Code:

Press Ctrl+Shift+P
Search Python: Select Interpreter
Choose something like:
Python 3.12 ('teststandgui': conda)

or a path like:

...\anaconda3\envs\teststandgui\python.exe

Then open a new VS Code terminal and run:

conda activate teststandgui
where python

You want it to show something like:

C:\Users\owens\anaconda3\envs\teststandgui\python.exe
not:
C:\Users\owens\AppData\Local\Microsoft\WindowsApps\python3.11.exe

Then run your file using that Python:
python "c:/Users/owens/OneDrive - cjanderson.biz/CJA - DIGITAL RELEASE - PRODUCT DRAWINGS/260608 - TestStand/TestStandGUI/ui/landing.py"

You can also test directly:
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"