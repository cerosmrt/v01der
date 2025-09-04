# test_voider.py
# Sistema de tests completo para el proyecto Voider.
# Usa pytest para testing, ya que es conciso y soporta fixtures bien.
# Este archivo debe colocarse en la raíz del proyecto.
# Para ejecutar: python -m pytest test_voider.py
# (Asegúrate de tener pytest instalado: pip install pytest)

import os
import random
import tempfile
import pytest
from unittest.mock import MagicMock, patch

# Importar módulos del proyecto
from controls import (
    setup_controls,
    show_random_line_from_current_file,
    show_random_line_from_random_file,
    show_previous_current_file_line,
    show_next_current_file_line
)
from files import setup_file_handling, void_line
from tools import clean_text, close_program, show_cursor
from noise_controls import NoiseController
# from new_interface import FullscreenCircleApp  # UI testing es opcional/complejo, se mockea
# from voider import ...  # Main script, no se testa directamente

# Fixture para crear un mock de la app (simula FullscreenCircleApp sin Qt)
@pytest.fixture
def mock_app():
    app = MagicMock()
    app.void_dir = tempfile.mkdtemp()  # Directorio temporal para tests de archivos
    app.void_file_path = os.path.join(app.void_dir, '0.txt')
    app.current_file_path = app.void_file_path
    app.txt_files = [app.void_file_path]
    app.current_file_index = 0
    app.entry = MagicMock()  # Mock para el QLineEdit
    app.entry.text.return_value = ""
    app.entry.setText = MagicMock()
    app.entry.setCursorPosition = MagicMock()
    app.entry.clear = MagicMock()
    app.current_active_line = None
    app.current_active_line_index = None
    app.last_inserted_index = None
    app.first_up_after_submission = False
    yield app
    # Cleanup: eliminar directorio temporal
    for file in os.listdir(app.void_dir):
        os.remove(os.path.join(app.void_dir, file))
    os.rmdir(app.void_dir)

# Fixture para setup inicial (llama a setup_file_handling y setup_controls)
@pytest.fixture
def setup_app(mock_app):
    setup_file_handling(mock_app)
    setup_controls(mock_app)
    yield mock_app

# --- Tests para controls.py ---

def test_setup_controls(setup_app):
    """Prueba que setup_controls inicialice el estado de navegación correctamente."""
    assert setup_app.first_up_after_submission == False

def test_show_random_line_from_current_file(setup_app):
    """Prueba selección de línea aleatoria del archivo actual, excluyendo la actual si posible."""
    # Caso: archivo vacío
    show_random_line_from_current_file(setup_app)
    assert setup_app.current_active_line is None
    assert setup_app.current_active_line_index is None
    setup_app.entry.clear.assert_called()

    # Caso: archivo con líneas
    with open(setup_app.current_file_path, 'w', encoding='utf-8') as f:
        f.write("Line1\nLine2\nLine3\n")
    setup_app.current_active_line = "Line2"  # Simular línea actual
    with patch('random.choice') as mock_choice:
        mock_choice.return_value = "Line1"
        show_random_line_from_current_file(setup_app)
        assert setup_app.current_active_line == "Line1"
        assert setup_app.current_active_line_index == 0
        setup_app.entry.setText.assert_called_with("Line1")
        setup_app.entry.setCursorPosition.assert_called_with(0)

    # Caso: solo una línea
    with open(setup_app.current_file_path, 'w', encoding='utf-8') as f:
        f.write("OnlyLine\n")
    show_random_line_from_current_file(setup_app)
    assert setup_app.current_active_line == "OnlyLine"
    assert setup_app.current_active_line_index == 0

def test_show_random_line_from_random_file(setup_app):
    """Prueba selección de línea aleatoria de un archivo aleatorio, excluyendo el actual si posible."""
    # Caso: sin archivos
    setup_app.txt_files = []
    show_random_line_from_random_file(setup_app)
    assert setup_app.current_active_line is None
    setup_app.entry.clear.assert_called()

    # Caso: múltiples archivos
    file2 = os.path.join(setup_app.void_dir, '1.txt')
    with open(file2, 'w', encoding='utf-8') as f:
        f.write("LineA\nLineB\n")
    setup_app.txt_files = [setup_app.current_file_path, file2]
    with open(setup_app.current_file_path, 'w', encoding='utf-8') as f:
        f.write("CurrentLine\n")
    with patch('random.choice') as mock_choice:
        mock_choice.side_effect = [file2, "LineA"]  # Primero elige archivo, luego línea
        show_random_line_from_random_file(setup_app)
        # Verificar que el archivo seleccionado está en txt_files
        assert setup_app.current_file_path in setup_app.txt_files
        # Si se seleccionó file2, verificar que la línea es de file2
        if setup_app.current_file_path == file2:
            assert setup_app.current_active_line == "LineA"
            assert setup_app.current_active_line_index == 0
        # Verificar que el índice del archivo se actualizó correctamente
        assert setup_app.current_file_index == setup_app.txt_files.index(setup_app.current_file_path)
        setup_app.entry.setText.assert_called_with("LineA")
        setup_app.entry.setCursorPosition.assert_called_with(0)

    # Caso: archivo vacío seleccionado
    with open(file2, 'w', encoding='utf-8') as f:
        f.write("")
    setup_app.txt_files = [setup_app.current_file_path, file2]  # Restaurar txt_files
    with patch('random.choice') as mock_choice:
        mock_choice.return_value = file2
        show_random_line_from_random_file(setup_app)
        assert setup_app.current_active_line is None
        # Verificar que el archivo seleccionado está en txt_files, incluso si es vacío
        assert setup_app.current_file_path in setup_app.txt_files
        assert setup_app.current_file_index == setup_app.txt_files.index(setup_app.current_file_path)
        setup_app.entry.clear.assert_called()

def test_show_previous_current_file_line(setup_app):
    """Prueba navegación a línea anterior, con loop y lógica de first_up_after_submission."""
    # Caso: archivo vacío
    show_previous_current_file_line(setup_app)
    assert setup_app.current_active_line is None
    setup_app.entry.clear.assert_called()

    # Caso: con líneas, first_up_after_submission=True
    with open(setup_app.current_file_path, 'w', encoding='utf-8') as f:
        f.write("Line1\nLine2\nLine3\n")
    setup_app.first_up_after_submission = True
    setup_app.last_inserted_index = 1  # "Line2"
    show_previous_current_file_line(setup_app)
    assert setup_app.current_active_line == "Line2"
    assert setup_app.current_active_line_index == 1
    assert setup_app.first_up_after_submission == False

    # Caso: navegación normal con loop
    setup_app.current_active_line_index = 0
    show_previous_current_file_line(setup_app)
    assert setup_app.current_active_line == "Line3"  # Loop al final
    assert setup_app.current_active_line_index == 2

    # Caso: líneas vacías (salta)
    with open(setup_app.current_file_path, 'w', encoding='utf-8') as f:
        f.write("Line1\n\nLine3\n")
    setup_app.current_active_line_index = 2
    show_previous_current_file_line(setup_app)
    assert setup_app.current_active_line == "Line1"
    assert setup_app.current_active_line_index == 0

def test_show_next_current_file_line(setup_app):
    """Prueba navegación a línea siguiente, con loop."""
    # Caso: archivo vacío
    show_next_current_file_line(setup_app)
    assert setup_app.current_active_line is None

    # Caso: con líneas, desde None usa last_inserted_index
    with open(setup_app.current_file_path, 'w', encoding='utf-8') as f:
        f.write("Line1\nLine2\nLine3\n")
    setup_app.current_active_line_index = None
    setup_app.last_inserted_index = 0
    show_next_current_file_line(setup_app)
    assert setup_app.current_active_line == "Line2"
    assert setup_app.current_active_line_index == 1

    # Caso: loop al principio
    setup_app.current_active_line_index = 2
    show_next_current_file_line(setup_app)
    assert setup_app.current_active_line == "Line1"
    assert setup_app.current_active_line_index == 0

    # Caso: líneas vacías (salta)
    with open(setup_app.current_file_path, 'w', encoding='utf-8') as f:
        f.write("Line1\n\nLine3\n")
    setup_app.current_active_line_index = 0
    show_next_current_file_line(setup_app)
    assert setup_app.current_active_line == "Line3"
    assert setup_app.current_active_line_index == 2

# --- Tests para files.py ---

def test_setup_file_handling(mock_app):
    """Prueba inicialización de manejo de archivos, crea directorios y archivos si no existen."""
    # Eliminar void_dir temporalmente para test
    os.rmdir(mock_app.void_dir)
    setup_file_handling(mock_app)
    assert os.path.exists(mock_app.void_dir)
    assert os.path.exists(mock_app.current_file_path)
    assert os.path.exists(mock_app.void_file_path)
    assert mock_app.current_active_line is None
    assert mock_app.current_active_line_index is None
    assert mock_app.last_inserted_index is None

def test_void_line(setup_app):
    """Prueba procesamiento de líneas: inserción, edición, comandos, formateo, movimientos."""
    # Caso: input vacío - resetea índices y mueve al final
    setup_app.entry.text.return_value = ""
    void_line(setup_app)
    assert setup_app.current_active_line_index is None
    assert setup_app.last_inserted_index == -1  # Archivo vacío

    # Caso: input normal con formateo
    setup_app.entry.text.return_value = "test sentence without period"
    void_line(setup_app)
    with open(setup_app.current_file_path, 'r') as f:
        content = f.read().strip()
    assert content == "Test sentence without period."

    # Caso: punto solo, no consecutivo
    setup_app.entry.text.return_value = "."
    void_line(setup_app)
    with open(setup_app.current_file_path, 'r') as f:
        lines = f.readlines()
    assert lines[-1].strip() == "."

    # Caso: punto consecutivo evitado
    setup_app.entry.text.return_value = "."
    void_line(setup_app)
    with open(setup_app.current_file_path, 'r') as f:
        lines = f.readlines()
    assert len(lines) == 2  # No se añadió el segundo punto

    # Caso: comando cambio de archivo //
    setup_app.entry.text.return_value = "//1"
    void_line(setup_app)
    assert setup_app.current_file_path == os.path.join(setup_app.void_dir, "1.txt")
    assert os.path.exists(setup_app.current_file_path)

    # Caso: mover línea simple "content /file"
    setup_app.entry.text.return_value = "Move this /2.txt"
    void_line(setup_app)
    target_path = os.path.join(setup_app.void_dir, "2.txt")
    with open(target_path, 'r') as f:
        assert f.read().strip() == "Move this"

    # Caso: mover bloque "/file"
    with open(setup_app.current_file_path, 'w') as f:
        f.write(".\nBlock line1\nBlock line2\n")
    setup_app.entry.text.return_value = "/3.txt"
    void_line(setup_app)
    target_path = os.path.join(setup_app.void_dir, "3.txt")
    with open(target_path, 'r') as f:
        assert f.read().strip() == ".\nBlock line1\nBlock line2"

    # Caso: edición de línea existente
    with open(setup_app.current_file_path, 'w') as f:
        f.write("Old line\n")
    setup_app.current_active_line_index = 0
    setup_app.entry.text.return_value = "New line."
    void_line(setup_app)
    with open(setup_app.current_file_path, 'r') as f:
        assert f.read().strip() == "New line."

    # Caso: error (mock exception)
    with patch('builtins.open') as mock_open:
        mock_open.side_effect = Exception("Test error")
        void_line(setup_app)
        setup_app.entry.clear.assert_called()

# --- Tests para tools.py ---

def test_clean_text():
    """Prueba que clean_text devuelva el texto sin cambios (según implementación actual)."""
    assert clean_text("test") == "test"
    assert clean_text("") == ""

def test_close_program(setup_app):
    """Prueba cierre de la app."""
    close_program(setup_app)
    setup_app.close.assert_called()

def test_show_cursor(setup_app):
    """Prueba mostrar cursor en entry."""
    show_cursor(setup_app)
    setup_app.entry.setCursorVisible.assert_called_with(True)

# --- Tests para noise_controls.py ---

def test_noise_controller_init():
    """Prueba inicialización de NoiseController."""
    nc = NoiseController()
    assert nc.sample_rate == 44100
    assert nc.volume == 0.01
    assert nc.noise_type == 'brown'
    nc.stop()  # Cleanup

def test_noise_controller_methods():
    """Prueba setters de NoiseController."""
    nc = NoiseController()
    nc.set_volume(0.5)
    assert nc.volume == 0.5
    nc.set_noise_type('white')
    assert nc.noise_type == 'white'
    nc.set_bitcrush({'bit_depth': 10})
    assert nc.bitcrush['bit_depth'] == 10
    nc.set_lfo_freq(0.02, 0.04)
    assert nc.lfo_min_freq == 0.02
    nc.set_glitch_prob(0.002)
    assert nc.glitch_prob == 0.002
    nc.set_cutoff_freq(1000)
    assert nc.cutoff_freq == 1000
    nc.stop()

# Para expandir: agrega nuevas funciones de test aquí o en fixtures separadas.