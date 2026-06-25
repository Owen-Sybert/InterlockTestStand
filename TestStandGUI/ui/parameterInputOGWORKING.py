
import os
from PyQt6.QtWidgets import QComboBox, QFileDialog, QGroupBox, QMessageBox, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QFormLayout
from PyQt6.QtCore import QTimer, Qt
from utils.navigation import exitApp, goBack
from utils.saveTests import save_to_json
from utils.storedDataPaths import getSavedTestsDir

class enduranceTestSetup(QWidget):
    def __init__(self, mode, parent_window=None):
        super().__init__()
        self.setWindowTitle("Endurance Test Parameters")
        self.parent_window = parent_window
        self.mode = mode
        self.testType = "endurance" # Set test type for saving purposes

        self._build_ui()
        self.showFullScreen()

        # If saved mode, select, then load saved parameters and display them
        if self.mode == "saved":
            self.chooseSavedTest()

    def _build_ui(self):
        # Create Layout
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        

        # Navigation Exit/Back Bar
        navBar = QHBoxLayout()
        exitButton = QPushButton("Exit")
        exitButton.clicked.connect(exitApp)
        backButton = QPushButton("Back")
        backButton.clicked.connect(lambda: goBack(self.parent_window))
        navBar.addWidget(exitButton)
        navBar.addWidget(backButton)
        navBar.addStretch(5)
        self.layout.addLayout(navBar)

        # Add title and instructions
        title = QLabel("Endurance Test Setup")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        instructions = QLabel("Select parameters for your endurance test. You can switch between basic and advanced settings using the tabs below.")
        self.layout.addWidget(title)
        self.layout.addWidget(instructions)

        # Create inner layout for tabs and auto display
        innerLayout = QHBoxLayout()
        self.layout.addLayout(innerLayout)

        # Add display area with estimated test time and number of cycles based on parameters selected (this will update as parameters are changed)
        summary_box = QGroupBox()
        summary_layout = QVBoxLayout()
        self.estimated_duration_label = QLabel("Estimated Testing Duration:")
        self.estimated_duration_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        summary_layout.addWidget(self.estimated_duration_label)
        self.estimated_duration_time_string = QLabel("--d:--h:--m:--s") # Placeholder until parameters are input and time can be calculated
        self.estimated_duration_time_string.setStyleSheet("font-size: 14px;")
        summary_layout.addWidget(self.estimated_duration_time_string)
        summary_layout.addStretch(1) # Add stretch to push content to top of summary box
        summary_box.setLayout(summary_layout)
        innerLayout.addWidget(summary_box,1) # Add stretch factor to make summary box smaller than tabs

        # Tabs
        self.tabs = QTabWidget()

        # Metadata Tab
        self.tabMetadata = QWidget()
        layoutMetadata = QVBoxLayout()
        metadataLabel = QLabel("Test Metadata:")
        metadataLabel.setStyleSheet("font-size: 16px; font-weight: bold")
        layoutMetadata.addWidget(metadataLabel)

        self.testNameInput = QLineEdit()
        self.operatorInput = QLineEdit()
        self.dutSerialNumberInput = QLineEdit()
        self.projectNumberInput = QLineEdit()
        self.notesInput = QTextEdit()
        self.notesInput.setPlaceholderText("Optional test notes, setup details, fixture comments, etc.")

        metadataGrid = QFormLayout()
        metadataGrid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        metadataGrid.addRow("Test Name:", self.testNameInput)
        metadataGrid.addRow("Operator:", self.operatorInput)
        metadataGrid.addRow("DUT Serial Number:", self.dutSerialNumberInput)
        metadataGrid.addRow("Project Number:", self.projectNumberInput)
        metadataGrid.addRow("Notes:", self.notesInput)
        layoutMetadata.addLayout(metadataGrid)
        layoutMetadata.addStretch(1)
        self.tabMetadata.setLayout(layoutMetadata)

        # Basic Tab
        self.tabBasic = QWidget()
        layoutBasic = QVBoxLayout()
        # Basic Settings
        layoutBasicLabel = QLabel("Basic Test Parameters:")
        layoutBasicLabel.setStyleSheet("font-size: 16px; font-weight: bold")
        layoutBasic.addWidget(layoutBasicLabel)
        self.motionProfileVersionInput = QLineEdit()
        self.motionProfileVersionInput.setText("1")
        self.motionProfileVersionInput.setPlaceholderText("Default: 1")
        self.cycleTimeInput = QLineEdit()
        self.makeAndCarryTimeInput = QLineEdit()
        self.numberOfCyclesInput = QLineEdit()
        self.cycleTimeInput.textChanged.connect(self.updateTimeEstimate) # Update estimated time as parameters are changed
        self.numberOfCyclesInput.textChanged.connect(self.updateTimeEstimate) # Update estimated time as parameters are changed
        basicParamGrid = QFormLayout()
        basicParamGrid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        basicParamGrid.addRow("Motion Profile Version:", self.motionProfileVersionInput)
        basicParamGrid.addRow("Cycle Time (s):", self.cycleTimeInput)
        basicParamGrid.addRow("Make and Carry Time (s):", self.makeAndCarryTimeInput)
        basicParamGrid.addRow("Number of Cycles:", self.numberOfCyclesInput)
        layoutBasic.addLayout(basicParamGrid)
        layoutBasic.addStretch(1) # Add stretch to push content to top of basic tab

        self.tabBasic.setLayout(layoutBasic)

        # Advanced Tab
        self.tabAdvanced = QWidget()
        layoutAdvanced = QVBoxLayout()
        # Advanced Settings
        layoutAdvancedLabel = QLabel("Advanced Test Parameters:")
        layoutAdvancedLabel.setStyleSheet("font-size: 16px; font-weight: bold")
        layoutAdvanced.addWidget(layoutAdvancedLabel)
        # Servo 1 Settings
        servo1box = QGroupBox("Servo 1 Settings:")
        servo1box.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        #layoutAdvanced.addWidget(QLabel("Servo 1 Settings:"))
        self.servo1DwellTimeLowerEntry = QLineEdit()
        self.servo1DwellTimeUpperEntry = QLineEdit()
        self.servo1VelocityLimitEntry = QLineEdit()
        self.servo1AccelerationLimitEntry = QLineEdit()
        servo1Grid = QFormLayout()
        servo1Grid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        servo1Grid.addRow("Dwell Time Lower Limit (s):", self.servo1DwellTimeLowerEntry)
        servo1Grid.addRow("Dwell Time Upper Limit (s):", self.servo1DwellTimeUpperEntry)
        servo1Grid.addRow("Velocity Limit (s):", self.servo1VelocityLimitEntry)
        servo1Grid.addRow("Acceleration Limit (s):", self.servo1AccelerationLimitEntry)
        servo1box.setLayout(servo1Grid)
        layoutAdvanced.addWidget(servo1box)

        # Servo 2 Settings
        servo2box = QGroupBox("Servo 2 Settings:")
        servo2box.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.servo2DwellTimeLowerEntry = QLineEdit()
        self.servo2DwellTimeUpperEntry = QLineEdit()
        self.servo2VelocityLimitEntry = QLineEdit()
        self.servo2AccelerationLimitEntry = QLineEdit()
        servo2Grid = QFormLayout()
        servo1Grid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        servo2Grid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        servo2Grid.addRow("Dwell Time Lower Limit (s):", self.servo2DwellTimeLowerEntry)
        servo2Grid.addRow("Dwell Time Upper Limit (s):", self.servo2DwellTimeUpperEntry)
        servo2Grid.addRow("Velocity Limit (s):", self.servo2VelocityLimitEntry)
        servo2Grid.addRow("Acceleration Limit (s):", self.servo2AccelerationLimitEntry)
        servo2box.setLayout(servo2Grid)
        layoutAdvanced.addWidget(servo2box)

        # Servo 3 Settings
        servo3box = QGroupBox("Servo 3 Settings:")
        servo3box.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.servo3DwellTimeLowerEntry = QLineEdit()
        self.servo3DwellTimeUpperEntry = QLineEdit()
        self.servo3VelocityLimitEntry = QLineEdit()
        self.servo3AccelerationLimitEntry = QLineEdit()
        servo3Grid = QFormLayout()
        servo3Grid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        servo3Grid.addRow("Dwell Time Lower Limit (s):", self.servo3DwellTimeLowerEntry)
        servo3Grid.addRow("Dwell Time Upper Limit (s):", self.servo3DwellTimeUpperEntry)
        servo3Grid.addRow("Velocity Limit (s):", self.servo3VelocityLimitEntry)
        servo3Grid.addRow("Acceleration Limit (s):", self.servo3AccelerationLimitEntry)
        servo3box.setLayout(servo3Grid)
        layoutAdvanced.addWidget(servo3box)

        # Servo 4 Settings
        servo4box = QGroupBox("Servo 4 Settings:")
        servo4box.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.servo4DwellTimeLowerEntry = QLineEdit()
        self.servo4DwellTimeUpperEntry = QLineEdit()
        self.servo4VelocityLimitEntry = QLineEdit()
        self.servo4AccelerationLimitEntry = QLineEdit()
        servo4Grid = QFormLayout()
        servo4Grid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        servo4Grid.addRow("Dwell Time Lower Limit (s):", self.servo4DwellTimeLowerEntry)
        servo4Grid.addRow("Dwell Time Upper Limit (s):", self.servo4DwellTimeUpperEntry)
        servo4Grid.addRow("Velocity Limit (s):", self.servo4VelocityLimitEntry)
        servo4Grid.addRow("Acceleration Limit (s):", self.servo4AccelerationLimitEntry)
        servo4box.setLayout(servo4Grid)
        layoutAdvanced.addWidget(servo4box)

        # Image Settings
        imagebox = QGroupBox("Image Settings:")
        imagebox.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.imagesDropDown = QComboBox()
        self.imagesDropDown.addItems(["Yes", "No"])
        self.imageFrequencyEntry = QLineEdit()
        imageGrid = QFormLayout()
        imageGrid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        imageGrid.addRow("Take Images?", self.imagesDropDown)
        imageGrid.addRow("Image Frequency:", self.imageFrequencyEntry)
        imagebox.setLayout(imageGrid)
        layoutAdvanced.addWidget(imagebox)

        # Logging Settings
        loggingbox = QGroupBox("Logging Settings:")
        loggingbox.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.loggingDropDown = QComboBox()
        self.loggingDropDown.addItems(["Yes", "No"])
        self.logLevelDropDown = QComboBox()
        self.logLevelDropDown.addItems(["INFO", "DEBUG", "WARNING", "ERROR"])
        self.telemetryFrequencyEntry = QLineEdit()
        self.telemetryFrequencyEntry.setPlaceholderText("Example: 10")
        loggingGrid = QFormLayout()
        loggingGrid.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        loggingGrid.addRow("Enable Logging?", self.loggingDropDown)
        loggingGrid.addRow("Log Level:", self.logLevelDropDown)
        loggingGrid.addRow("Telemetry Frequency (Hz):", self.telemetryFrequencyEntry)
        loggingbox.setLayout(loggingGrid)
        layoutAdvanced.addWidget(loggingbox)

        layoutAdvanced.addStretch(1) # Add stretch to push content to top of tab
        self.tabAdvanced.setLayout(layoutAdvanced)
        
        # Add the widgets to the Tab Widget
        self.tabs.addTab(self.tabMetadata, "Metadata")
        self.tabs.addTab(self.tabBasic, "Basic")
        self.tabs.addTab(self.tabAdvanced, "Advanced")

        # Add tabs to main layout
        innerLayout.addWidget(self.tabs,3)

        # Continue Bar
        continueBar = QHBoxLayout()
        continueBar.addStretch(5)
        # Review Settings and Run Test
        continueButton = QPushButton("Save Settings and Run Test")
        continueButton.clicked.connect(self.saveThenReturn) # Save current settings to json (if file path is None, it will generate a new file in the saved tests directory with a date based name)
        continueBar.addWidget(continueButton)
        self.layout.addLayout(continueBar)
        
    def updateTimeEstimate(self):
        # Get cycle time and number of cycles from input, calculate total time, and update label
        try:
            cycle_time = float(self.cycleTimeInput.text())
            number_of_cycles = int(self.numberOfCyclesInput.text())
            total_time_seconds = cycle_time * number_of_cycles
            # Convert total time to d:h:m:s format
            days = total_time_seconds // (24 * 3600)
            hours = (total_time_seconds % (24 * 3600)) // 3600
            minutes = (total_time_seconds % 3600) // 60
            seconds = total_time_seconds % 60
            self.estimated_duration_time_string.setText(f"{int(days)}d:{int(hours)}h:{int(minutes)}m:{int(seconds)}s")
        except ValueError:
            # If inputs are not valid numbers, show placeholder text
            self.estimated_duration_time_string.setText("--d:--h:--m:--s")   

    def chooseSavedTest(self):
        dialog = QFileDialog(self, "Select Saved Test")
        dialog.setDirectory(str(getSavedTestsDir()))
        dialog.setNameFilter("JSON Files (*.json)")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        file_path = None

        if dialog.exec():
            selected_files = dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]

        if file_path:
            self.receive_data(file_path)

        self.showFullScreen()
            
    def dataFormat(self):
        data = {
            # Metadata
            "test_type": self.testType,
            "test_name": self.testNameInput.text(),
            "operator": self.operatorInput.text(),
            "dut_serial_number": self.dutSerialNumberInput.text(),
            "project_number": self.projectNumberInput.text(),
            "notes": self.notesInput.toPlainText(),

            # Basic parameters
            "motion_profile_version": self.motionProfileVersionInput.text(),
            "cycle_time": self.cycleTimeInput.text(),
            "make_and_carry_time": self.makeAndCarryTimeInput.text(),
            "number_of_cycles": self.numberOfCyclesInput.text(),

            # Servo 1
            "servo1_dwell_lower": self.servo1DwellTimeLowerEntry.text(),
            "servo1_dwell_upper": self.servo1DwellTimeUpperEntry.text(),
            "servo1_velocity": self.servo1VelocityLimitEntry.text(),
            "servo1_acceleration": self.servo1AccelerationLimitEntry.text(),

            # Servo 2
            "servo2_dwell_lower": self.servo2DwellTimeLowerEntry.text(),
            "servo2_dwell_upper": self.servo2DwellTimeUpperEntry.text(),
            "servo2_velocity": self.servo2VelocityLimitEntry.text(),
            "servo2_acceleration": self.servo2AccelerationLimitEntry.text(),

            # Servo 3
            "servo3_dwell_lower": self.servo3DwellTimeLowerEntry.text(),
            "servo3_dwell_upper": self.servo3DwellTimeUpperEntry.text(),
            "servo3_velocity": self.servo3VelocityLimitEntry.text(),
            "servo3_acceleration": self.servo3AccelerationLimitEntry.text(),

            # Servo 4
            "servo4_dwell_lower": self.servo4DwellTimeLowerEntry.text(),
            "servo4_dwell_upper": self.servo4DwellTimeUpperEntry.text(),
            "servo4_velocity": self.servo4VelocityLimitEntry.text(),
            "servo4_acceleration": self.servo4AccelerationLimitEntry.text(),

            # Image settings
            "images_enabled": self.imagesDropDown.currentText(),
            "image_frequency": self.imageFrequencyEntry.text(),

            # Logging settings
            "logging_enabled": self.loggingDropDown.currentText(),
            "log_level": self.logLevelDropDown.currentText(),
            "telemetry_frequency_hz": self.telemetryFrequencyEntry.text(),
        }
        return data

    def saveThenReturn(self):
        data = self.dataFormat()
        save_to_json(data)
        QMessageBox.information(self, "Success", "Test saved successfully!")
        goBack(self.parent_window)

class loadCellTestSetup(QWidget):
    def __init__(self, mode, parent_window=None):
        super().__init__()
        self.setWindowTitle("Load Cell Test Parameters")
        self.parent_window = parent_window
        self.mode = mode
        print(mode)
        