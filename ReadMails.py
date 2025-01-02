import os
import win32com.client

def read_and_save_meeting_summaries():
    # Markers in the body
    start_marker = "Meeting summary for Data Analytics Daily Scrum "
    end_marker = "AI-generated content may be inaccurate or misleading. Always check for accuracy."

    # Create an instance of Outlook
    outlook = win32com.client.Dispatch("Outlook.Application")

    # Get the MAPI namespace
    mapi = outlook.GetNamespace("MAPI")

    # 6 refers to the inbox folder in Outlook
    inbox = mapi.GetDefaultFolder(6)

    # Get all emails in Inbox
    messages = inbox.Items

    # Sort messages by received time descending (most recent first)
    messages.Sort("[ReceivedTime]", True)

    # Prepare output file (ensure 'Mails' folder exists)
    output_folder = "Mails"
    os.makedirs(output_folder, exist_ok=True)
    output_file_path = os.path.join(output_folder, "meeting_summaries.txt")

    # Iterate through messages
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
