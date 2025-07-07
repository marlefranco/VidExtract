import sys
import os
from PyQt6.QtWidgets import QApplication
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
    else:
        print(f"Error: Video file not found at {video_path}")
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()