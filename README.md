# Automated Failed Query Log Report Generator

This project provides a Google Cloud Function that automatically generates a concise PDF report summarizing failed queries from a log Excel file stored in Google Drive. The report includes key statistics, a bar chart, and recent failure details, and is uploaded back to Google Drive for easy access and sharing.

## Features
- **Automated Reporting:** Generates a PDF report from an Excel log file (`failed_logs.xlsx`) in Google Drive.
- **Summary & Visualization:** Includes total failures, most recent failure, most common error, failures by dataset (with a bar chart), and recent failure details.
- **Cloud-Native:** Designed to run as a Google Cloud Function, triggered via HTTP or scheduled with Cloud Scheduler.
- **Generalized & Secure:** No hardcoded secrets or IDs; all configuration is via environment variables.

## How It Works
1. The function authenticates using a Google service account (provided as an environment variable).
2. It searches for `failed_logs.xlsx` in a specified Google Drive folder.
3. Downloads and processes the Excel file using pandas.
4. Generates a PDF report (max 300 words, with a bar chart and recent failures) using `fpdf` and `matplotlib`.
5. Uploads (or updates) the PDF report (`failed_logs_report.pdf`) in the same Drive folder.

## Requirements
- Python 3.10+
- Google Cloud Functions (2nd gen recommended)
- A Google service account with access to Google Drive

## Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/your-repo.git
   cd your-repo
   ```
2. **Install dependencies (for local testing):**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables:**
   - **You must create a `.env` file (not included in this repo) with the following environment variables:**
     ```
     GOOGLE_SERVICE_ACCOUNT_JSON=your_service_account_json_here
     DRIVE_FOLDER_ID=your_drive_folder_id_here
     ```
   - **Do not commit your real `.env` file or any secrets to the repository.**
   - Set these in the GCP Console for deployment.

## Deployment (Google Cloud Functions)
1. **Deploy the function:**
   ```bash
   gcloud functions deploy generate-report \
     --runtime python310 \
     --trigger-http \
     --entry-point generate_report \
     --region us-east1
   ```
2. **Set environment variables in the GCP Console:**
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `DRIVE_FOLDER_ID`
3. **(Optional) Schedule with Cloud Scheduler:**
   - Use Cloud Scheduler to trigger the function every 24 hours or as needed.

## Usage
- The function will look for `failed_logs.xlsx` in your specified Drive folder.
- It will generate and upload/update `failed_logs_report.pdf` in the same folder.
- You can trigger the function manually via HTTP or on a schedule.

## Security
- **Never commit your actual service account JSON or secrets to the repository.**
- Use environment variables for all sensitive information.
- Add `.env` and any secret files to your `.gitignore`.

## License
MIT 

Mady by Ansuhree
