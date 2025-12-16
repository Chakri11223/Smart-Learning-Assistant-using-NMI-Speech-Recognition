
from youtubesearchpython import VideosSearch
import json

def test_youtube():
    query = "Python Basics Introduction tutorial"
    print(f"Searching for: {query}")
    try:
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        print("Raw Results:")
        print(json.dumps(results, indent=2))
        
        if results and results.get('result'):
            video = results['result'][0]
            print("\nParsed Video:")
            print(f"Title: {video.get('title')}")
            print(f"Link: {video.get('link')}")
        else:
            print("\nNo results found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_youtube()
