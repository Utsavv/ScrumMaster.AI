import os
from datetime import datetime
import pytz  # Install using 'pip install pytz'
import win32com.client

def read_and_save_meeting_summaries():
    # Markers in the body
    start_marker = "Meeting summary for Data Analytics Daily Scrum "
    end_marker = "AI-generated content may be inaccurate or misleading. Always check for accuracy."

    # Define timezone and date range
    timezone = pytz.timezone("UTC")  # Adjust to your timezone if needed
    start_date = timezone.localize(datetime(2024, 12, 24))  # Example: December 24, 2024
    end_date = timezone.localize(datetime(2025, 1, 23))    # Example: December 31, 2024

    # Convert dates to Outlook-friendly format (yyyy-MM-dd HH:mm)
    start_date_str = start_date.strftime('%Y-%m-%d %H:%M')
    end_date_str = end_date.strftime('%Y-%m-%d %H:%M')

    # Create an instance of Outlook
    outlook = win32com.client.Dispatch("Outlook.Application")

    # Get the MAPI namespace
    mapi = outlook.GetNamespace("MAPI")

    # 6 refers to the inbox folder in Outlook
    inbox = mapi.GetDefaultFolder(6)

    # Use Restrict to filter messages within the date range
    filter_query = f"[ReceivedTime] >= '{start_date_str}' AND [ReceivedTime] <= '{end_date_str}'"
    messages = inbox.Items.Restrict(filter_query)

    # Prepare output file with date range in the name
    output_folder = "Mails"
    os.makedirs(output_folder, exist_ok=True)
    file_name = f"meeting_summaries_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.txt"
    output_file_path = os.path.join(output_folder, file_name)

    # Iterate through filtered messages
    for message in messages:
        # 43 = MailItem in Outlook
        if message.Class == 43:
            try:
                if message.Subject.strip() == "Meeting Summary for Data Analytics Daily Scrum":
                    body = message.Body

                    # Find start and end indices
                    start_index = body.find(start_marker)
                    end_index = body.find(end_marker)

                    if start_index != -1 and end_index != -1:
                        # Extract text between the two markers
                        extracted_text = body[start_index + len(start_marker):end_index].strip()

                        # Append to the output file
                        with open(output_file_path, "a", encoding="utf-8") as f:
                            f.write("\n\n=== Received on: {} ===\n".format(str(message.ReceivedTime)))
                            f.write(extracted_text + "\n")

            except Exception as e:
                print("Error reading or writing message:", e)


if __name__ == "__main__":
    read_and_save_meeting_summaries()
