import requests

def test_news():
    try:
        response = requests.get('http://127.0.0.1:5000/api/news')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            print(f"Fetched {len(articles)} articles.")
            for i, article in enumerate(articles[:3]):
                print(f"{i+1}. {article['title']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_news()
