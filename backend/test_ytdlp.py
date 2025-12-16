import yt_dlp
import sys

url = "https://www.youtube.com/watch?v=kqtD5dpn9C8"
ydl_opts = {
    'quiet': False, # Enable output to see what's happening
    'no_warnings': False,
    'skip_download': True,
    'socket_timeout': 10,
}

print(f"Testing yt-dlp with URL: {url}")
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success!")
        print(f"Title: {info.get('title')}")
except Exception as e:
    print(f"Error: {e}")
