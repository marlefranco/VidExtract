# VidExtract Requirements

## Overview
VidExtract is a GUI application that extracts video snippets from MKV files based on timestamp overlays that appear on the top-right corner of the frames. The timestamps must be in the format `DD/MM/YYYY HH:mm:ss:SSS`.

## Functional Requirements

### Core Functionality
1. Extract video snippets from MKV files based on start and end timestamps
2. Recognize timestamp overlays in the top-right corner of video frames using OCR
3. Support timestamp format: DD/MM/YYYY HH:mm:ss:SSS
4. Save extracted snippets as MP4 files

### User Interface
1. Provide a graphical user interface for selecting input files and specifying timestamps
2. Display progress during extraction process
3. Show appropriate error messages for common issues
4. Allow UI customization through Qt Designer

## Technical Requirements

### Dependencies
1. Python 3.11
2. Tesseract OCR installed and available in system PATH
3. Python packages:
   - opencv-python (for video processing)
   - pytesseract (for OCR)
   - Pillow (for image processing)
   - PyQt6 (for GUI)

### Performance
1. Keep the UI responsive during extraction by using threading
2. Implement efficient frame searching algorithms to reduce processing time
3. Use caching for OCR results to avoid redundant processing

## Constraints

### Input Constraints
1. Currently only supports MKV input files
2. Timestamps must be in the format DD/MM/YYYY HH:mm:ss:SSS
3. Timestamps must appear in the top-right corner of the frames

### Output Constraints
1. Output is saved as MP4 format
2. Output is saved in the same directory as the input file with a fixed name "snippet.mp4"

## Known Limitations

1. OCR step can be slow because every frame between the start and end time is scanned
2. Limited error handling for OCR failures or missing timestamps
3. Only supports MKV input format
4. No preview feature to verify timestamp detection

## Future Improvements

1. Add support for more video formats beyond MKV
2. Allow customization of the timestamp format and position
3. Add options to configure OCR parameters for better recognition
4. Implement a preview feature to verify timestamp detection
5. Improve OCR efficiency by sampling frames or caching results
6. Expand error handling to better inform users of issues
7. Allow customization of output filename and location