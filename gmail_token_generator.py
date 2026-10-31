from google_auth_oauthlib.flow import InstalledAppFlow

# Required scope for sending emails via Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

if __name__ == "__main__":
    # Load your downloaded credentials file
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    
    # Opens a local server to handle the browser authentication flow
    creds = flow.run_local_server(port=0)
    
    # Save the resulting credentials to token.json
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
        
    print("Authentication successful! 'token.json' has been generated.")