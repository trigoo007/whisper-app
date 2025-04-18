import pytest
from whisper_app.utils import text_utils

def test_clean_text():
    texto = "  hola   mundo ! esto es   una prueba."
    limpio = text_utils.clean_text(texto)
    assert limpio.startswith("Hola mundo!")
    assert "." in limpio

def test_extract_keywords():
    texto = "python python código código prueba prueba prueba test test"
    keywords = text_utils.extract_keywords(texto, max_keywords=2, language='es')
    assert len(keywords) == 2
    assert "prueba" in keywords
    assert "python" in keywords

def test_split_long_segments():
    segs = [{"id": 1, "start": 0, "end": 10, "text": "Esto es una frase muy larga. Y aquí otra oración también larga."}]
    result = text_utils.split_long_segments(segs, max_chars=20, max_duration=5)
    assert len(result) > 1
    for seg in result:
        assert len(seg["text"]) <= 25 