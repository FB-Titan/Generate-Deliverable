import requests
import config
import json

def check_description_format(task_id):
    url = f"{config.CLICKUP_API_BASE_URL}/task/{task_id}?include_markdown_description=true"
    headers = {"Authorization": config.CLICKUP_API_TOKEN}
    
    print(f"Fetching {task_id}...")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("\n--- description ---")
        print(repr(data.get('description', '')))
        
        print("\n--- markdown_description ---")
        print(repr(data.get('markdown_description', 'MISSING')))
        
        return data
    else:
        print(f"Error: {response.status_code}")

if __name__ == "__main__":
    check_description_format("86dvdkn82")
