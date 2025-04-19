#!/usr/bin/env python3

import os
import sys

# Añadir src al PYTHONPATH para que los imports absolutos funcionen
src_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'src')
sys.path.insert(0, src_path)

# Importar la aplicación después de configurar el PYTHONPATH
from whisper_app.app import main

if __name__ == "__main__":
    sys.exit(main())
