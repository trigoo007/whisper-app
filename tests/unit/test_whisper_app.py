import os
import sys
import unittest
from pathlib import Path

# Add the project directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import app components - using the correct structure
try:
    from src.whisper_app.app import main
    from src.whisper_app.core.transcriber import Transcriber
    from src.whisper_app.core.config_manager import ConfigManager
except ImportError:
    print("Could not import app components. Make sure your app structure is correct.")
    sys.exit(1)

class TestWhisperApp(unittest.TestCase):
    def setUp(self):
        # Setup code - create test directory if it doesn't exist
        self.test_dir = Path(__file__).parent / "test_files"
        self.test_dir.mkdir(exist_ok=True)
        
        # Path to a test audio file - you'll need to provide this
        self.test_audio = str(self.test_dir / "test_audio.mp3")
        
        # Check if test file exists
        if not os.path.exists(self.test_audio):
            print(f"Warning: Test audio file not found at {self.test_audio}")
            print("Please add a test audio file to run complete tests")

        self.config_manager = ConfigManager()
        self.transcriber = Transcriber(self.config_manager)

    def tearDown(self):
        self.transcriber = None
        self.config_manager = None

    def test_app_exists(self):
        """Test that the app is properly initialized"""
        self.assertIsNotNone(self.transcriber)
        self.assertIsNotNone(self.config_manager)

    def test_transcription(self):
        """Test the transcription functionality if test file exists"""
        if os.path.exists(self.test_audio):
            config = ConfigManager()
            transcriber = Transcriber(config)
            transcriber.load_model("tiny")  # Use smallest model for testing
            result = transcriber.transcribe_file(self.test_audio)
            self.assertIsNotNone(result)
            print(f"Transcription result: {result}")
        else:
            self.skipTest("Test audio file not available")

if __name__ == "__main__":
    unittest.main()