from youtubesearchpython import VideosSearch
import json

def test_search(query):
    print(f"Searching for: {query}")
    try:
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        print("Raw Results:")
        print(json.dumps(results, indent=2))
        
        if results and results.get('result'):
            video = results['result'][0]
            print(f"Found video: {video.get('title')}")
            print(f"Link: {video.get('link')}")
        else:
            print("No results found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search("Python Basics")
