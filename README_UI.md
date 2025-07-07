# Editing the VidExtract UI

VidExtract now uses Qt Designer UI files for its graphical interface. This makes it easy to modify the application's appearance without having to write code.

## Requirements

To edit the UI, you'll need:

1. **Qt Designer** - This is a visual tool for creating and editing UI files.
   - If you have PyQt6 installed, Qt Designer might be included.
   - Otherwise, you can download it as part of the [Qt framework](https://www.qt.io/download).
   - For Windows users, you can also find standalone versions online.

## Editing the UI

1. **Open the UI file**:
   - Launch Qt Designer
   - Open the `mainwindow.ui` file from the VidExtract project directory

2. **Make your changes**:
   - Drag and drop widgets from the widget box to add new elements
   - Select existing widgets to modify their properties
   - Use the property editor to change colors, sizes, fonts, etc.
   - Use the layout tools to arrange widgets

3. **Important guidelines**:
   - Do not change the names of existing widgets (e.g., `selectFileButton`, `startTimeEdit`, etc.)
   - Do not remove existing widgets that are used by the application
   - Keep the same basic structure of frames and layouts

4. **Save your changes**:
   - Save the file back to `mainwindow.ui` in the project directory

5. **Test your changes**:
   - Run the application with `python main.py` to see your changes in action

## UI Structure

The current UI consists of:

- **File selection section**: A button to select MKV files and a label to display the selected file
- **Input fields**: Text fields for entering start and end timestamps
- **Progress section**: A progress bar and status label to show extraction progress
- **Extract button**: The main action button to start the extraction process
- **Menu bar**: Contains File menu with Open and Exit actions

## Advanced Customization

If you need more advanced customization:

1. You can add new widgets and then extend the `MainWindow` class in `main.py` to handle them
2. You can modify the stylesheets in the UI file to change the appearance
3. For complex changes, you might need to modify both the UI file and the Python code

## Batch Extract UI

The batch extract application also uses a UI file:

1. **Open the UI file**:
   - Launch Qt Designer
   - Open the `batchextract.ui` file from the VidExtract project directory

2. **Make your changes**:
   - Drag and drop widgets from the widget box to add new elements
   - Select existing widgets to modify their properties
   - Use the property editor to change colors, sizes, fonts, etc.
   - Use the layout tools to arrange widgets

3. **Important guidelines**:
   - Do not change the names of existing widgets (e.g., `select_file_button`, `dir_path_label`, etc.)
   - Do not remove existing widgets that are used by the application
   - Keep the same basic structure of frames and layouts

## Troubleshooting

If you encounter issues after editing the UI:

1. Make sure you haven't removed or renamed any widgets that are referenced in the code
2. Check that all layouts are properly set up
3. Try reverting to the original UI file and making changes incrementally
4. If the application crashes, check the console for error messages
