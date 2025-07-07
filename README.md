# VidExtract

VidExtract is a GUI application that extracts video snippets based on timestamp overlays. It now supports multiple video formats (MKV, MP4, AVI, MOV, WMV) and various timestamp formats and positions.

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

### Adding Tesseract OCR to PATH

If you didn't add Tesseract to your PATH during installation or need to configure it manually:

#### Windows
1. Find the Tesseract installation directory (typically `C:\Program Files\Tesseract-OCR` or `C:\Program Files (x86)\Tesseract-OCR`)
2. Open System Properties (right-click on This PC, select Properties)
3. Click on "Advanced system settings"
4. Click on "Environment Variables"
5. Under "System variables", find the "Path" variable, select it and click "Edit"
6. Click "New" and add the Tesseract installation directory
7. Click "OK" on all dialogs to save the changes
8. Restart any open Command Prompt windows for the changes to take effect
9. Verify by typing `tesseract --version` in a new Command Prompt

#### macOS
1. Open Terminal
2. Edit your shell profile file (`~/.bash_profile`, `~/.zshrc`, or similar):
   ```bash
   nano ~/.zshrc  # or ~/.bash_profile
   ```
3. Add the following line (adjust the path if Tesseract is installed elsewhere):
   ```bash
   export PATH="/usr/local/bin:$PATH"
   ```
4. Save and exit (Ctrl+O, Enter, Ctrl+X)
5. Apply the changes:
   ```bash
   source ~/.zshrc  # or ~/.bash_profile
   ```
6. Verify with `tesseract --version`

#### Linux
1. Open Terminal
2. Edit your shell profile file:
   ```bash
   nano ~/.bashrc
   ```
3. Add the following line (adjust the path if Tesseract is installed elsewhere):
   ```bash
   export PATH="/usr/bin:$PATH"
   ```
4. Save and exit (Ctrl+O, Enter, Ctrl+X)
5. Apply the changes:
   ```bash
   source ~/.bashrc
   ```
6. Verify with `tesseract --version`

### Specifying a Custom Tesseract Path in the Application

If you can't add Tesseract to your PATH, you can modify the application to use a custom path:

1. Open `main.py` in a text editor
2. Add the following line after the import statements (around line 10):
   ```python
   # Set custom Tesseract path - adjust the path to match your installation
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows example
   # pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'  # macOS/Linux example
   ```
3. Save the file and run the application

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

1. Click **Select Video** and choose your video file (MKV, MP4, AVI, MOV, WMV).
2. Enter the desired **start** and **end** timestamps that appear in the video overlay.
   - Multiple timestamp formats are supported:
     - DD/MM/YYYY HH:mm:ss:SSS (e.g., 01/02/2023 12:34:56:789)
     - MM/DD/YYYY HH:mm:ss:SSS (e.g., 02/01/2023 12:34:56:789)
     - YYYY-MM-DD HH:mm:ss.SSS (e.g., 2023-02-01 12:34:56.789)
     - HH:mm:ss:SSS (e.g., 12:34:56:789)
     - HH:mm:ss.SSS (e.g., 12:34:56.789)
3. (Optional) Click **Preview** to verify timestamp detection.
4. Press **Extract**. You will be prompted to choose a name and location for the output file.

### New Features

- **Multiple Video Formats**: Support for MKV, MP4, AVI, MOV, and WMV files.
- **Flexible Timestamp Recognition**: Support for various timestamp formats and positions.
- **Preview Functionality**: Verify timestamp detection before extraction.
- **Output Customization**: Choose the name and location for the output file.
- **Improved Performance**: Adaptive frame sampling and better memory management.
- **Enhanced Error Handling**: More detailed error messages and suggestions.
- **Automatic Tesseract Detection**: Simplified setup and configuration.

## Customizing the UI

VidExtract now uses PyQt6 and a UI file that can be edited with Qt Designer. This makes it easy to customize the application's appearance without having to write code.

For detailed instructions on how to edit the UI, see [README_UI.md](README_UI.md).

## Packaging and Distribution

VidExtract now includes a setup.py file that can be used to create standalone executables:

### Using PyInstaller

```bash
# Install PyInstaller
pip install pyinstaller

# Create a standalone executable
python setup.py pyinstaller
```

The executable will be created in the `dist` directory.

### Using cx_Freeze

```bash
# Install cx_Freeze
pip install cx_freeze

# Create a standalone executable
python setup.py build_exe
```

The executable will be created in the `build` directory.

## Testing

VidExtract includes a test script to verify the functionality of key components:

```bash
# Run the tests
python test_vidextract.py
```

The tests cover:
- Timestamp parsing with various formats
- OCR configuration and region coordinate calculations
- Tesseract detection
- Timestamp pattern validation

## Future Improvements

While many improvements have been implemented, there are still some areas that could be enhanced in future versions:

- **Batch Processing**: Add support for processing multiple videos or time ranges at once.
- **Advanced Preview**: Implement a timeline view with marked timestamp positions.
- **Region Selection UI**: Add a graphical interface for selecting the timestamp region.
- **Custom Timestamp Formats**: Allow users to define custom timestamp formats.
- **Plugin System**: Create a plugin architecture for extensibility.
- **Automatic Optimization**: Implement automatic optimization based on video characteristics.
- **Parallel Processing**: Add multi-threading for OCR operations to improve performance on multi-core systems.
