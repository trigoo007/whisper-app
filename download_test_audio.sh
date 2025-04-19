#!/bin/bash
mkdir -p test_files
echo "Downloading a sample audio file for testing..."
curl -L "https://github.com/openai/whisper/raw/main/tests/jfk.flac" -o "test_files/test_audio.mp3"
echo "Download complete. Test audio file saved to test_files/test_audio.mp3"
