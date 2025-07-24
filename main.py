import os
import json
import io
import pandas as pd
from flask import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import matplotlib.pyplot as plt
from fpdf import FPDF

def generate_report(request: Request):
    """Cloud Function entry point that processes failed logs and generates a PDF report."""
    try:
        print("[LOG] Starting report generation function.")

        # Step 1: Load credentials and folder ID from environment variables
        service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        folder_id = os.environ.get("DRIVE_FOLDER_ID")
        if not service_account_json or not folder_id:
            print("[ERROR] Required environment variables are missing.")
            return "Error: Required environment variables (GOOGLE_SERVICE_ACCOUNT_JSON, DRIVE_FOLDER_ID) are missing.", 500
        try:
            credentials_info = json.loads(service_account_json)
        except Exception as e:
            print(f"[ERROR] Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
            return f"Error: Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}", 500
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=["https://www.googleapis.com/auth/drive"]
        )
        print("[LOG] Credentials created successfully.")

        # Step 2: Build Drive service
        drive_service = build('drive', 'v3', credentials=credentials)
        print(f"[LOG] Using Drive folder ID from env: {folder_id}")

        # Step 3: Find the file in Drive
        print("[LOG] Searching for failed_logs.xlsx in Drive folder...")
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and name='failed_logs.xlsx' and trashed=false",
            fields="files(id, name)").execute()
        files = results.get('files', [])
        print(f"[LOG] Files found: {files}")
        if not files:
            print("[ERROR] No failed_logs.xlsx found in Drive folder.")
            return "No failed_logs.xlsx found in Drive folder.", 404
        file_id = files[0]['id']
        print(f"[LOG] Found file ID: {file_id}")

        # Step 4: Download the file
        print("[LOG] Downloading failed_logs.xlsx...")
        request_drive = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_drive)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"[LOG] Download progress: {int(status.progress() * 100)}%")
        fh.seek(0)
        print("[LOG] File downloaded successfully.")

        # Step 5: Load into DataFrame
        print("[LOG] Loading Excel into pandas DataFrame...")
        df = pd.read_excel(fh)
        print(f"[LOG] DataFrame loaded. Shape: {df.shape}")

        # Step 6: Validate DataFrame columns
        required_cols = ['dataset', 'reason', 'date']
        for col in required_cols:
            if col not in df.columns:
                print(f"[ERROR] Required column missing: {col}")
                return f"Error: Required column missing: {col}", 500

        # Step 7: Generate PDF report
        print("[LOG] Generating PDF report...")
        total_failures = len(df)
        by_dataset = df['dataset'].value_counts()
        most_common_error = df['reason'].value_counts().idxmax() if not df['reason'].isnull().all() else "N/A"
        most_recent = df['date'].max()
        recent_failures = df[['date', 'dataset', 'reason']].head(5)

        # Plot: Failures by dataset
        plt.figure(figsize=(6, 3))
        by_dataset.plot(kind='bar')
        plt.title('Failures by Dataset')
        plt.xlabel('Dataset')
        plt.ylabel('Count')
        plt.tight_layout()
        chart_path = '/tmp/failures_by_dataset.png'
        plt.savefig(chart_path)
        plt.close()

        # Prepare summary text (max 300 words)
        summary_lines = [
            f"Failed Query Log Report",
            f"Total failed queries: {total_failures}",
            f"Most recent failure: {most_recent}",
            "",
            "Failures by dataset (top 5):"
        ]
        for dataset, count in by_dataset.head(5).items():
            summary_lines.append(f"  - {dataset}: {count}")
        summary_lines.append("")
        summary_lines.append(f"Most common error: {most_common_error}")
        summary_lines.append("")
        summary_lines.append("Recent failures (top 5):")
        for _, row in recent_failures.iterrows():
            summary_lines.append(f"  - Date: {row['date']}, Dataset: {row['dataset']}, Reason: {str(row['reason'])[:60]}...")

        summary_text = "\n".join(summary_lines)
        words = summary_text.split()
        if len(words) > 300:
            summary_text = " ".join(words[:300]) + "..."

        # Generate PDF report
        pdf_path = '/tmp/failed_logs_report.pdf'
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, summary_text)
        # Add bar chart
        if os.path.exists(chart_path):
            pdf.image(chart_path, x=10, y=pdf.get_y(), w=pdf.w - 20)
            pdf.ln(60)
        pdf.output(pdf_path)
        print(f"[LOG] PDF report generated at {pdf_path}")

        # Step 8: Upload PDF report to Drive
        print("[LOG] Uploading PDF report to Drive...")
        file_metadata = {
            'name': 'failed_logs_report.pdf',
            'parents': [folder_id]
        }
        media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
        # Check if report already exists
        report_results = drive_service.files().list(
            q=f"'{folder_id}' in parents and name='failed_logs_report.pdf' and trashed=false",
            fields="files(id, name)"
        ).execute()
        report_files = report_results.get('files', [])
        if report_files:
            # Update existing
            report_id = report_files[0]['id']
            drive_service.files().update(
                fileId=report_id,
                media_body=media
            ).execute()
            print(f"[LOG] Updated existing PDF report in Drive with ID: {report_id}")
        else:
            # Create new
            new_report = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            print(f"[LOG] Created new PDF report in Drive with ID: {new_report.get('id')}")

        return f"PDF report generated and uploaded to Drive.", 200

    except Exception as e:
        print(f"[ERROR] Error generating PDF report: {e}")
        return f"Error generating PDF report: {e}", 500