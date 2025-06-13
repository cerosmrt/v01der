# --- voider.py ---
import os
import sys
from PyQt6.QtWidgets import QApplication
from new_interface import FullscreenCircleApp

if __name__ == "__main__":
    try:
        if getattr(sys, 'frozen', False):
            app_path = os.path.dirname(sys.executable)
        else:
            app_path = os.path.dirname(os.path.abspath(__file__))  # V01DER directory
        read_dir = os.path.dirname(app_path)  # Z:\programming\Voider\V2
        void_dir = os.path.join(app_path, 'void')  # Z:\programming\Voider\V2\V01DER\void
        print(f"Working directory: {os.getcwd()}")
        print(f"App path: {app_path}")
        print(f"Void dir: {void_dir}")
        if not os.path.exists(void_dir):
            print(f"Creating: {void_dir}")
            try:
                os.makedirs(void_dir)
            except Exception as e:
                print(f"Error creating void folder: {e}")
        else:
            print(f"Void folder exists: {void_dir}")
        app = QApplication(sys.argv)
        window = FullscreenCircleApp(read_dir=read_dir, void_dir=void_dir)
        window.show()
        print("Window shown")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")