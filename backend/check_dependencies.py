import sys

def check_import(module_name):
    try:
        __import__(module_name)
        print(f"[OK] {module_name}")
    except ImportError as e:
        print(f"[MISSING] {module_name}: {e}")
    except Exception as e:
        print(f"[ERROR] {module_name}: {e}")

print("Checking dependencies...")
check_import("yt_dlp")
check_import("ffmpeg") # ffmpeg-python
check_import("imageio_ffmpeg")
check_import("whisper") # openai-whisper
