import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd

from openpyxl import load_workbook

# Load environment variables
load_dotenv()
TFS_URL = os.getenv("TFS_URL")
PROJECT = os.getenv("PROJECT")
PAT = os.getenv("PAT")
# TEAM = os.getenv("TEAM")
API_VERSION = os.getenv("API_VERSION", "4.1")

EXCEL_FILE = "burndown.xlsx"

def get_current_iteration():
    url = f"{TFS_URL}/{PROJECT}/_apis/work/teamsettings/iterations?$timeframe=current&api-version={API_VERSION}"
    response = requests.get(url, auth=HTTPBasicAuth("", PAT))
    response.raise_for_status()
    iterations = response.json()["value"]
    return iterations[0]["path"] if iterations else None

def get_work_items_for_iteration(iteration_path):
    url = f"{TFS_URL}/{PROJECT}/_apis/wit/wiql?api-version={API_VERSION}"    
    wiql = {
        "query": f"""
        SELECT [System.Id] FROM WorkItems 
        WHERE [System.IterationPath] = '{iteration_path}'
        AND [System.WorkItemType] = 'Task'
        """
    }
    response = requests.post(url, json=wiql, auth=HTTPBasicAuth("", PAT))
    response.raise_for_status()
    return [str(item["id"]) for item in response.json()["workItems"]]

def fetch_task_details(task_ids):
    batch_size = 200
    all_tasks = []
    for i in range(0, len(task_ids), batch_size):
        batch = ",".join(task_ids[i:i+batch_size])
        fields = ",".join([
            "System.Id", "System.Title", "System.AssignedTo",
            "Microsoft.VSTS.Scheduling.RemainingWork",
            "ATI.VSTS.Scheduling.DateDue"
        ])
        url = f"{TFS_URL}/_apis/wit/workitems?ids={batch}&fields={fields}&api-version={API_VERSION}"
        response = requests.get(url, auth=HTTPBasicAuth("", PAT))
        response.raise_for_status()
        for item in response.json().get("value", []):
            fields = item.get("fields", {})
            date_due = fields.get("ATI.VSTS.Scheduling.DateDue", None)
            if date_due:
                try:
                    date_due = datetime.fromisoformat(date_due).strftime("%Y-%m-%d")
                except ValueError:
                    date_due = None  # Ignore invalid date formats

            all_tasks.append({
                "ID": item["id"],
                "Title": fields.get("System.Title", ""),
                "AssignedTo": fields.get("System.AssignedTo", {}),
                "RemainingWork": fields.get("Microsoft.VSTS.Scheduling.RemainingWork", 0),
                "DateDue": date_due
            })
    return all_tasks

def load_previous_day_remaining():
    try:
        prev_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        df = pd.read_excel(EXCEL_FILE, sheet_name=prev_date)
        return df.set_index("ID")["RemainingWork"].to_dict()
    except:
        return {}

def save_today_burndown(tasks, iteration_path):
    today = datetime.now().strftime("%Y-%m-%d")
    prev_remaining = load_previous_day_remaining()

    rows = []
    for t in tasks:
        prev = prev_remaining.get(t["ID"])
        hours_burnt = prev - t["RemainingWork"] if prev is not None else None
        rows.append({
            "ID": t["ID"],
            "Title": t["Title"],
            "AssignedTo": t["AssignedTo"],
            "RemainingWork": t["RemainingWork"],
            "HoursBurnt": hours_burnt,
            "DateDue": t["DateDue"]
        })

    df = pd.DataFrame(rows)

    # Save or append sheet to burndown file
    if os.path.exists(EXCEL_FILE):
        try:
            with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode='a', if_sheet_exists="replace") as writer:
                df.to_excel(writer, sheet_name=today, index=False)
        except PermissionError:
            print(f"❌ Unable to write to {EXCEL_FILE}. It might be open. Please close it and try again.")
            return
    else:
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=today, index=False)

    print(f"✅ Saved {len(df)} tasks to burndown file → Sheet: {today}")

    # Reminders
    for t in rows:
        if t["DateDue"]:
            try:
                dev_date = datetime.fromisoformat(t["DateDue"])
                if (dev_date - datetime.now()).days <= 2:
                    print(f"🔔 Reminder: Task {t['ID']} ('{t['Title']}') assigned to {t['AssignedTo']} is due on {t['DateDue']} (in {(dev_date - datetime.now()).days} days).")
            except Exception as e:
                print(f"⚠️ Invalid DateDue for Task {t['ID']}")
        else:
            print(f"⚠️ DateDue missing for Task {t['ID']}")

def main(iteration=None):
    iteration_path = iteration or get_current_iteration()
    if not iteration_path:
        print("❌ No active iteration found.")
        return

    print(f"📦 Tracking tasks for iteration: {iteration_path}")
    task_ids = get_work_items_for_iteration(iteration_path)
    if not task_ids:
        print("ℹ️ No tasks found.")
        return

    tasks = fetch_task_details(task_ids)
    save_today_burndown(tasks, iteration_path)

if __name__ == "__main__":
    main()
