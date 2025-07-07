# VidExtract

VidExtract is a simple GUI application that extracts a video snippet from an MKV file based on timestamp overlays that appear on the top-right corner of the frames. The timestamps must be in the format `DD/MM/YYYY HH:mm:ss:SSS`.

## Requirements

- Python 3.11
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and available in your system `PATH`
- The Python packages listed in `requirements.txt`

### Installing Tesseract OCR

Tesseract OCR must be installed separately from the Python dependencies:

#### Windows
1. Download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run the installer and follow the instructions
3. Make sure to check the option "Add to PATH" during installation
4. Verify installation by opening Command Prompt and typing: `tesseract --version`

#### macOS
1. Install using Homebrew: `brew install tesseract`
2. Verify installation: `tesseract --version`

#### Linux
1. Ubuntu/Debian: `sudo apt install tesseract-ocr`
2. Fedora: `sudo dnf install tesseract`
3. Verify installation: `tesseract --version`

### Installing Python Dependencies

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

Run the application with:

```bash
python main.py
```

1. Click **Select MKV** and choose your video file.
2. Enter the desired **start** and **end** timestamps that appear in the video overlay.
3. Press **Extract**. A snippet named `snippet.mp4` will be saved in the same folder as the source video.

## Customizing the UI

VidExtract now uses PyQt6 and a UI file that can be edited with Qt Designer. This makes it easy to customize the application's appearance without having to write code.

For detailed instructions on how to edit the UI, see [README_UI.md](README_UI.md).

## Limitations and possible improvements

- The OCR step can be slow because every frame between the start and end time is scanned. A more efficient approach would be to sample frames or cache OCR results.
- Error handling could be expanded to better inform the user of OCR failures or missing timestamps.
- Adding support for more video formats beyond MKV.
- Implementing a preview feature to verify timestamp detection.
