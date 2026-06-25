import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication, QMessageBox
from ui.parameterInput import enduranceTestSetup, loadCellTestSetup
from utils.navigation import exitApp

class LandingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Stand Parameter Input")
        self.showFullScreen()

        layout = QVBoxLayout(self)

        # Top bar for exit button
        exitBar = QHBoxLayout()
        exitButton = QPushButton("Exit")
        exitButton.clicked.connect(exitApp)
        exitBar.addWidget(exitButton)
        exitBar.addStretch(5)
        layout.addLayout(exitBar)

        # Title and welcome screen
        title = QLabel("Select Test Type:")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Endurance Test
        layout.addStretch(1) # Create vertical space between title and buttons
        enduranceBox = QHBoxLayout() # Create horizontal layout for endurance test buttons
        savedEnduranceButton = QPushButton("Run Saved Endurance Test")
        createEnduranceButton = QPushButton("Create New Endurance Test")
        enduranceBox.addStretch(1) # Add stretch before buttons to push them to the right
        enduranceBox.addWidget(savedEnduranceButton)
        enduranceBox.addWidget(createEnduranceButton)
        enduranceBox.addStretch(1) # Add stretch after buttons to push them to the left, centering buttons in horizontal layout
        layout.addLayout(enduranceBox) # Add horizontal layout to main vertical layout

        # Load Cell Test
        loadCellBox = QHBoxLayout() # Create horizontal layout for load cell test buttons
        savedLoadCellButton = QPushButton("Run Saved Load Cell Test")
        createLoadCellButton = QPushButton("Create New Load Cell Test")
        loadCellBox.addStretch(1) # Add stretch before buttons to push them to the right
        loadCellBox.addWidget(savedLoadCellButton)
        loadCellBox.addWidget(createLoadCellButton)
        loadCellBox.addStretch(1) # Add stretch after buttons to push them to the left, centering buttons in horizontal layout
        layout.addLayout(loadCellBox) # Add horizontal layout to main vertical layout

        # Add final vertical stretch to push content to middle
        layout.addStretch(1)

        # Connect buttons
        savedEnduranceButton.clicked.connect(self.openSavedEnduranceTest)
        createEnduranceButton.clicked.connect(self.createEnduranceTest)
        savedLoadCellButton.clicked.connect(self.openSavedLoadCellTest)
        createLoadCellButton.clicked.connect(self.createLoadCellTest)

    def openSavedEnduranceTest(self):
        self.parameterWindow = enduranceTestSetup(parent_window=self,mode="saved")
        self.parameterWindow.show()
        self.close()

    def createEnduranceTest(self):
        self.parameterWindow = enduranceTestSetup(parent_window=self,mode="create")
        self.parameterWindow.show()
        self.close()

    def openSavedLoadCellTest(self):
        self.parameterWindow = loadCellTestSetup(parent_window=self,mode="saved")
        self.parameterWindow.show()
        self.close()

    def createLoadCellTest(self):
        self.parameterWindow = loadCellTestSetup(parent_window=self,mode="create")
        self.parameterWindow.show()
        self.close()

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    window = LandingPage()
    window.show()

    sys.exit(app.exec())