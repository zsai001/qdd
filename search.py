import requests
import yaml

def load_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

config = load_config()
API_KEY = config['GOOGLE_API_KEY']
SEARCH_ENGINE_ID = config['GOOGLE_SEARCH_ENGINE_ID']

def google_search(query, api_key, cse_id, **kwargs):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'key': api_key,
        'cx': cse_id,
    }
    params.update(kwargs)
    response = requests.get(url, params=params)
    return response.json()

def display_results(results):
    items = results.get("items", [])
    for i, item in enumerate(items, start=1):
        print(f"\n--- Result {i} ---")
        print(f"Title: {item['title']}")
        print(f"Link: {item['link']}")
        print(f"Snippet: {item['snippet']}")

if __name__ == "__main__":
    search_query = input("Enter your search query: ")
    results = google_search(search_query, API_KEY, SEARCH_ENGINE_ID)
    display_results(results)