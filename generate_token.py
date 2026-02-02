import os
import os.path
import json
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # Priority: Environment variable then file
    token_json = os.getenv('GOOGLE_USER_TOKEN_JSON')
    if token_json:
        print("DEBUG: Loading existing token from environment variable.")
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    elif os.path.exists('token.json'):
        print("DEBUG: Loading existing token from file.")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("DEBUG: Token expired, refreshing...")
            creds.refresh(Request())
        else:
            print("DEBUG: No valid credentials, starting OAuth flow...")
            client_secrets_json = os.getenv('GOOGLE_CLIENT_SECRETS_JSON')
            if client_secrets_json:
                print("DEBUG: Using client secrets from environment variable.")
                client_config = json.loads(client_secrets_json)
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            else:
                print("DEBUG: Using client secrets from file (credentials.json).")
                if not os.path.exists('credentials.json'):
                    print("ERROR: credentials.json not found and GOOGLE_CLIENT_SECRETS_JSON not set.")
                    return
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            
            creds = flow.run_local_server(port=0, host='127.0.0.1')
        
        # Save the credentials for the next run (printing to terminal for user to copy)
        print("\n" + "="*50)
        print("NEW TOKEN GENERATED!")
        print("Please copy the following JSON and update your GOOGLE_USER_TOKEN_JSON in .env:")
        print("="*50)
        print(creds.to_json())
        print("="*50 + "\n")
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    print("Token is valid and ready to use!")

if __name__ == '__main__':
    main()
