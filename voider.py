# --- voider.py ---
import os
import sys
from PyQt6.QtWidgets import QApplication
from new_interface import FullscreenCircleApp

if __name__ == "__main__":
    try:
        if getattr(sys, 'frozen', False):
            # If running as an executable (PyInstaller), app_path is the directory of the .exe
            app_path = os.path.dirname(sys.executable)
            # For EXE, void_dir is the same directory as the executable
            void_dir = app_path
            print(f"EXE Mode: Files will be saved directly in the executable's directory.")
        else:
            # If running as a Python script, app_path is the directory of the script
            app_path = os.path.dirname(os.path.abspath(__file__))
            # For script, void_dir is a 'void' subdirectory
            void_dir = os.path.join(app_path, 'void')
            print(f"Script Mode: Files will be saved in the 'void' subdirectory.")

        # Check for command-line arguments
        file_to_open = None
        if len(sys.argv) > 1:
            # Get the first argument (potential file path)
            candidate_file = sys.argv[1]
            # Verify it's a .txt file and exists (or can be created)
            if candidate_file.lower().endswith('.txt'):
                # Convert to absolute path to handle drag-and-drop or relative paths
                candidate_file = os.path.abspath(candidate_file)
                if os.path.exists(candidate_file) or os.path.dirname(candidate_file) == void_dir:
                    file_to_open = candidate_file
                    print(f"Opening specified file: {file_to_open}")
                else:
                    print(f"File {candidate_file} does not exist and is not in void_dir. Defaulting to 0.txt.")
            else:
                print(f"Argument {candidate_file} is not a .txt file. Defaulting to 0.txt.")
        
        # If no valid file was provided, default to 0.txt in void_dir
        if not file_to_open:
            file_to_open = os.path.join(void_dir, '0.txt')
            print(f"No file specified. Defaulting to: {file_to_open}")

        read_dir = os.path.dirname(app_path)
        
        print(f"Working directory: {os.getcwd()}")
        print(f"App path: {app_path}")
        print(f"Void dir (where files are saved): {void_dir}")
        print(f"Active file: {file_to_open}")
        
        app = QApplication(sys.argv)
        # Pass void_dir and the file to open to FullscreenCircleApp
        window = FullscreenCircleApp(read_dir=read_dir, void_dir=void_dir, file_to_open=file_to_open)
        window.show()
        print("Window shown")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")