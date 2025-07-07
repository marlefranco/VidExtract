import sys
import os
import time
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import QTimer
from main import MainWindow

def main():
    # Create the application
    app = QApplication(sys.argv)
    
    # Create the main window
    window = MainWindow()
    
    # Show the window
    window.show()
    
    # Set the video path
    video_path = r"C:\Users\Marle.Franco\Olympus\Katana Machine Learning - Data Repository-TRL 5 - Animal Lab 13 JUN 2025 - Documents\Data\Session 2\Computer Data Logger Video\2025-06-13 13-02-54.mkv"
    
    # Check if the video file exists
    if os.path.exists(video_path):
        print(f"Video file exists at {video_path}")
        window.video_path = video_path
        window.ui.filePathLabel.setText(os.path.basename(video_path))
        
        # Set the start and end timestamps
        window.ui.startTimeEdit.setText("13/06/2025 13:28:27:657")
        window.ui.endTimeEdit.setText("13/06/2025 13:28:37:872")
        
        # Define a function to handle the file dialog
        def handle_file_dialog():
            # This will be called when the file dialog appears
            # Get the active modal dialog
            for dialog in QApplication.topLevelWidgets():
                if dialog.isModal():
                    # Set the output file name
                    output_path = os.path.join(os.path.dirname(video_path), "test_snippet.mp4")
                    print(f"Setting output path to: {output_path}")
                    
                    # Use QFileDialog's methods to set the file name
                    if isinstance(dialog, QFileDialog):
                        dialog.selectFile(output_path)
                        
                        # Accept the dialog after a short delay
                        QTimer.singleShot(500, dialog.accept)
                    break
        
        # Schedule clicking the extract button after a short delay
        QTimer.singleShot(1000, lambda: print("Clicking extract button..."))
        QTimer.singleShot(1000, window.ui.extractButton.click)
        
        # Schedule handling the file dialog after the extract button is clicked
        QTimer.singleShot(2000, handle_file_dialog)
        
        # Schedule closing the application after a longer delay to allow extraction to complete
        QTimer.singleShot(60000, app.quit)
    else:
        print(f"Error: Video file not found at {video_path}")
        QTimer.singleShot(1000, app.quit)
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()