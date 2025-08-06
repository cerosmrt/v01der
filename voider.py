import os
import sys
from PyQt6.QtWidgets import QApplication
from new_interface import FullscreenCircleApp

if __name__ == "__main__":
    try:
        if getattr(sys, 'frozen', False):
            # Si es un ejecutable (PyInstaller), app_path es el directorio del .exe
            app_path = os.path.dirname(sys.executable)
            # MODIFICACIÓN CLAVE AQUÍ: Para el EXE, void_dir es la misma carpeta del EXE
            void_dir = app_path 
            print(f"Modo EXE: Los archivos se guardarán directamente en la carpeta del ejecutable.")
        else:
            # Si es un script de Python, app_path es el directorio del script
            app_path = os.path.dirname(os.path.abspath(__file__))
            # MODIFICACIÓN CLAVE AQUÍ: Para el script, void_dir es una subcarpeta 'void'
            void_dir = os.path.join(app_path, 'void')  
            print(f"Modo Script: Los archivos se guardarán en la subcarpeta 'void'.")
        
        # read_dir parece no usarse para los archivos void, se mantiene como estaba en tu código.
        read_dir = os.path.dirname(app_path) 
        
        print(f"Working directory: {os.getcwd()}")
        print(f"App path: {app_path}")
        print(f"Void dir (donde se guardarán los archivos): {void_dir}") # Mensaje aclaratorio
        
        # La creación del directorio void_dir (si es una subcarpeta) se manejará en files.py
        # a través de setup_file_handling, que es donde se asegura que void_dir exista.
        
        app = QApplication(sys.argv)
        # Se pasa void_dir a FullscreenCircleApp para que sepa dónde guardar los archivos.
        window = FullscreenCircleApp(read_dir=read_dir, void_dir=void_dir)
        window.show()
        print("Window shown")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
