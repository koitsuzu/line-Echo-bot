import os.path
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    user_token_b64 = os.getenv("GOOGLE_USER_TOKEN_B64")
    if user_token_b64:
        token_info = json.loads(base64.b64decode(user_token_b64))
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_b64 = os.getenv("GOOGLE_CLIENT_SECRETS_B64")
            if not client_secrets_b64:
                print("ERROR: GOOGLE_CLIENT_SECRETS_B64 not found in environment variables.")
                return
            
            client_config = json.loads(base64.b64decode(client_secrets_b64))
            flow = InstalledAppFlow.from_client_config(
                client_config, SCOPES)
            creds = flow.run_local_server(port=0, host='127.0.0.1')
        # Save the credentials for the next run (Local file still used for updates, user should manually update .env with new B64)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    print("Token generated successfully! Saved to token.json")
    print("IMPORTANT: The token has been updated. Please run 'convert_to_b64.py' and update the B64 string in your .env file.")
    print("IMPORTANT: Please copy the content of token.json to GOOGLE_USER_TOKEN_JSON in your .env file.")

if __name__ == '__main__':
    main()
