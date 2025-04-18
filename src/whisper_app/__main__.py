#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada cuando se ejecuta el módulo directamente
"""

import sys
from whisper_app.app import main

if __name__ == "__main__":
    sys.exit(main())