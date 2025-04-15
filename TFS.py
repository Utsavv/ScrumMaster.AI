import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
import csv
import json  # at top of your file if not already
import unicodedata


# ------------------ CONFIGURATION ------------------
TFS_URL = "http://uslv-atfsapp-01:8080/tfs/DefaultCollection"
PROJECT = "nVision"
API_VERSION = "4.1"
PAT = "pguwsrk3wseqvyodwo4gpiqueyefl5f5udh63d5zv3qwtbpic6oq"  
OUTPUT_CSV = "tfs_workitems.csv"
# ---------------------------------------------------

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Normalize to closest ASCII equivalent
    normalized = unicodedata.normalize("NFKD", text)
    ascii_encoded = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_encoded.strip()

def get_work_item_ids_from_query(query_id):
    """
    Fetches work item IDs from a saved WIQL query.
    """
    wiql_url = f"{TFS_URL}/{PROJECT}/_apis/wit/wiql/{query_id}?api-version={API_VERSION}"
    response = requests.get(wiql_url, auth=HTTPBasicAuth("", PAT))
    response.raise_for_status()
    work_items = response.json().get("workItems", [])
    return [str(item["id"]) for item in work_items]

import requests

import requests
from datetime import datetime

def generate_test_cases_and_save_to_file(work_items, model="Gemma3:1b", sample_testcase="", user_guide=""):
    """
    Generates test cases via Ollama API and saves them to a timestamped text file.
    :param work_items: List of [id, title, description]
    :param model: Ollama model to use
    """
    api_url = "http://172.28.72.48:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ollama_testcases_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        for item_id, title, description in work_items:
            prompt = f"""
                You are a QA engineer for a casino management system. Your task is to write detailed and structured test cases based strictly on the defect description.
                ### Defect Title
                ```{title}```
                ### Defect Description
                ```{description}```
                ### Sample Test Cases
                ```{sample_testcase}```
                ### User Guide Snippet (For Reference)
                # ```{user_guide}```
                ### Important Instructions
                - Write test cases that directly relate to the **defect description** — do not include generic merge/unmerge test cases.
                - Ensure both **positive** and **negative** scenarios are covered.
                - Structure each test case using the following format:
                - **Scenario**
                - **Preconditions**
                - **Steps**
                - **Expected Result**
                - Prioritize issues that arise **{description}.

                Begin test case creation now:
                """


            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }

            try:
                response = requests.post(api_url, json=payload, headers=headers)
                response.raise_for_status()
                test_cases = response.json().get("response", "")
            except Exception as e:
                test_cases = f"ERROR generating test cases: {e}"
                print(f"ERROR generating test cases: {e}")

            # Write to file
            f.write(f"=== Model {model} ===\n")
            f.write(f"=== Test Cases for WorkItem {item_id} ===\n")
            f.write(f"=== Description {description} ===\n")
            f.write(test_cases.strip() + "\n\n")
            print(f"✅ Processed WorkItem {item_id}")

    print(f"\n📝 Test cases saved to file: {filename}")


def get_work_items_details(work_item_ids):
    """
    Fetches work item details for a list of IDs.
    Returns list of [id, title, plain-text description].
    """
    rows = []
    batch_size = 200
    for i in range(0, len(work_item_ids), batch_size):
        batch_ids = ",".join(work_item_ids[i:i + batch_size])
        fields = "System.Id,System.Title,System.Description,ATI.Bug.Description,Microsoft.VSTS.TCM.ReproSteps"
        url = f"{TFS_URL}/_apis/wit/workitems?ids={batch_ids}&fields={fields}&api-version={API_VERSION}"
        response = requests.get(url, auth=HTTPBasicAuth("", PAT))
        response.raise_for_status()

        items = response.json().get("value", [])
        for item in items:
            item_id = item.get("id", "")
            fields = item.get("fields", {})
            title = fields.get("System.Title", "")

            # 🔍 Fallback logic for description
            description_html = (
                fields.get("ATI.Bug.Description")
                or fields.get("Microsoft.VSTS.TCM.ReproSteps")
                or fields.get("System.Description")
                or ""
            )
            description_text = clean_text(BeautifulSoup(description_html, "html.parser").get_text())

            # Debug print
            if not description_text.strip():
                print(f"Empty description for WorkItem {item_id}, available fields: {list(fields.keys())}")

            rows.append([item_id, title, description_text])
    return rows
def extract_business_logic_from_pdf(filepath="PlayerMergeUserGuid.pdf"):
    """
    Extracts business logic sections from the Player Merge User Guide.
    Focuses on business rules, balances, awards, restrictions, and merges.
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(filepath)
        all_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        # Define section markers
        sections = [
            "Business Rules",
            "Account Balances",
            "Bucket Awards Tab",
            "Casino Barred Restrictions",
            "Earnings Tab",
            "Offers Tab",
            "Player Functions",
            "Player Info Tab",
            "Player Transactions Tab",
            "Running Balances Tab",
            "Trips Tab",
            "Tier History Tab",
            "Tier Points Earnings Tab",
            "Universal Promo Transactions Tab",
        ]

        # Create a dict to hold section-wise data
        extracted = {}
        current_section = None

        for line in all_text.splitlines():
            line_stripped = line.strip()

            if line_stripped in sections:
                current_section = line_stripped
                extracted[current_section] = []
            elif current_section:
                extracted[current_section].append(line_stripped)

        # Combine into a clean markdown-style string
        output = []
        for sec, content in extracted.items():
            output.append(f"### {sec}\n" + "\n".join(content).strip() + "\n")

        print("✅ Extracted business logic sections from PDF.")
        return "\n".join(output).strip()

    except Exception as e:
        print(f"❌ ERROR extracting business logic: {e}")
        return ""

def read_pdf(filepath="PlayerMergeUserGuid.pdf"):    
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        print("✅ Successfully read PDF file:")        
        return text
    except Exception as e:
        print(f"❌ ERROR reading PDF file {filepath}: {e}")
        return None
def export_to_csv(rows, filename=OUTPUT_CSV):
    """
    Exports list of rows to a CSV file.
    """
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Title", "Description"])
        writer.writerows(rows)
    print(f"✅ Exported {len(rows)} work items to {filename}")
def read_sample_testcases(filepath="SampleTestCase.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        print("✅ Successfully read sample test cases:")        
        return content
    except Exception as e:
        print(f"❌ ERROR reading file {filepath}: {e}")
        return None

def main():
    # print("Select mode:")
    # print("1. Fetch from saved query")
    # print("2. Manually enter Work Item IDs. USe CSV for multiple IDs")
    # choice = input("Enter 1 or 2: ").strip()
    
    # try:
    #     if choice == "1":
    #         query_id = input("Enter the WIQL Query ID: ").strip()
    #         ids = get_work_item_ids_from_query(query_id)
    #     elif choice == "2":
    #         ids_input = input("Enter comma-separated Work Item IDs: ").strip()
    #         ids = [id.strip() for id in ids_input.split(",") if id.strip().isdigit()]
    #     else:
    #         print("Invalid choice.")
    #         return

    #     if not ids:
    #         print("No valid work item IDs found.")
    #         return
        # ids_input = "697281, 703799, 694671, 612643, 611537, 569621, 462696, 455329,    424587, 395769, 390959, 390950, 390949, 389155, 388234,    368290, 358729, 358727, 254231, 253524, 250679, 197840"
        ids_input = "390950, 703799, 694671"
        ids = [id.strip() for id in ids_input.split(",") if id.strip().isdigit()]
        
        rows = get_work_items_details(ids)
        # export_to_csv(rows)
        # test_cases = generate_test_cases_and_save_to_file(model="Gemma3:1b",work_items= rows, sample_testcase=read_sample_testcases(), user_guide=read_pdf())
        # test_cases = generate_test_cases_and_save_to_file(model="Llama3.3",work_items= rows, sample_testcase=read_sample_testcases(), user_guide=read_pdf())
        test_cases = generate_test_cases_and_save_to_file(model="qwen2.5-coder:32b",work_items= rows, sample_testcase=read_sample_testcases(), user_guide=extract_business_logic_from_pdf())

    # except requests.HTTPError as e:
    #     print(f" HTTP error occurred: {e.response.status_code} - {e.response.text}")
    # except Exception as ex:
    #     print(f" Unexpected error: {str(ex)}")

if __name__ == "__main__":
    main()
    read_sample_testcases()
