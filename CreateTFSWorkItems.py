import requests
import pandas as pd
from requests.auth import HTTPBasicAuth
import json

# ------------------ CONFIGURATION ------------------
TFS_URL = "http://uslv-atfsapp-01:8080/tfs/DefaultCollection"
PROJECT = "nVision"
API_VERSION = "4.1"
PAT = "pguwsrk3wseqvyodwo4gpiqueyefl5f5udh63d5zv3qwtbpic6oq"  # 🔒 Replace with your PAT
CSV_PATH = "azure_devops_pbIs.csv"
# ---------------------------------------------------

auth = HTTPBasicAuth('', PAT)

def search_work_item_by_title(title):
    """
    Searches for an existing work item by title using WIQL.
    """
    wiql = {
        "query": f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{PROJECT}' AND [System.Title] = '{title}'"
    }

    url = f"{TFS_URL}/{PROJECT}/_apis/wit/wiql?api-version={API_VERSION}"
    response = requests.post(url, json=wiql, auth=auth)
    response.raise_for_status()
    results = response.json()

    if results.get("workItems"):
        return results["workItems"][0]["id"]
    return None

def update_work_item(work_item_id, title, description, tags):
    url = f"{TFS_URL}/_apis/wit/workitems/{work_item_id}?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json-patch+json"
    }
    patch_doc = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description},
        {"op": "add", "path": "/fields/System.Tags", "value": tags}
    ]

    response = requests.patch(url, auth=auth, headers=headers, json=patch_doc)
    response.raise_for_status()
    print(f"🔁 Updated work item {work_item_id}: {title}")

def create_work_item(title, description, tags):
    url = f"{TFS_URL}/{PROJECT}/_apis/wit/workitems/$Product%20Backlog%20Item?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json-patch+json"
    }
    patch_doc = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description},
        {"op": "add", "path": "/fields/System.Tags", "value": tags}
    ]

    response = requests.post(url, auth=auth, headers=headers, json=patch_doc)
    response.raise_for_status()
    work_item_id = response.json().get("id")
    print(f"🆕 Created work item {work_item_id}: {title}")

def sync_pbIs_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        title = row['title']
        description = row['description']
        tags = row['tags']

        try:
            existing_id = search_work_item_by_title(title)
            if existing_id:
                update_work_item(existing_id, title, description, tags)
            else:
                create_work_item(title, description, tags)
        except requests.HTTPError as e:
            print(f"❌ Error processing '{title}': {e.response.status_code} - {e.response.text}")

# ---------- Run It ----------
if __name__ == "__main__":
    sync_pbIs_from_csv(CSV_PATH)
