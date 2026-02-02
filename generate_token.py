import os.path
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
    user_token_json = os.getenv("GOOGLE_USER_TOKEN_JSON")
    if user_token_json:
        token_info = json.loads(user_token_json)
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_json = os.getenv("GOOGLE_CLIENT_SECRETS_JSON")
            if not client_secrets_json:
                print("ERROR: GOOGLE_CLIENT_SECRETS_JSON not found in environment variables.")
                return
            
            client_config = json.loads(client_secrets_json)
            flow = InstalledAppFlow.from_client_config(
                client_config, SCOPES)
            creds = flow.run_local_server(port=0, host='127.0.0.1')
        # Save the credentials for the next run (Local file still used for updates, user should manually update .env)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    print("Token generated successfully! Saved to token.json")
    print("IMPORTANT: Please copy the content of token.json to GOOGLE_USER_TOKEN_JSON in your .env file.")

if __name__ == '__main__':
    main()
