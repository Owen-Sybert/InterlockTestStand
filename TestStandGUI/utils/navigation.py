from PyQt6.QtWidgets import QApplication

def exitApp():
    QApplication.instance().quit()

def goBack(parent_window):
    if parent_window:
        parent_window.show() 

