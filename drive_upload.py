import os.path
import win32clipboard
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_NAME = "ViewClipper Scans"  # Name of the folder in Google Drive

def copy_link_to_clipboard(text):
    """Helper to copy the Google Drive link to clipboard"""
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text)
        win32clipboard.CloseClipboard()
        print("📋 Link copied to clipboard!")
    except Exception as e:
        print(f"⚠️ Could not copy link to clipboard: {e}")

def get_drive_service():
    """Handles Google Login"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Error: credentials.json not found in folder!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service):
    """Finds the folder ID or creates it if it doesn't exist"""
    try:
        # Search for the folder
        query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            print(f"📁 Creating new folder: {FOLDER_NAME}...")
            file_metadata = {
                'name': FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
        else:
            # Folder exists, return its ID
            return items[0]['id']
            
    except Exception as e:
        print(f"⚠️ Error finding folder: {e}")
        return None

def upload_to_drive(filepath):
    """Uploads file to specific folder and returns link"""
    try:
        service = get_drive_service()
        if not service:
            return None

        # Get folder ID
        folder_id = get_or_create_folder(service)
        
        filename = os.path.basename(filepath)
        print(f"☁️  Uploading {filename} to '{FOLDER_NAME}'...")
        
        file_metadata = {'name': filename}
        
        # If we successfully found/created the folder, put the file inside it
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(filepath, mimetype='image/png')
        
        # Upload the file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        link = file.get('webViewLink')
        print(f"✅ Upload Complete!")
        print(f"🔗 Link: {link}")
        
        # Automatically put link on clipboard
        copy_link_to_clipboard(link)
        
        return link
        
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        return None