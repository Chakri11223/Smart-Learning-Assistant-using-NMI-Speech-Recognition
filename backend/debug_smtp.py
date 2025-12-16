import os
from dotenv import load_dotenv
import smtplib

# Load environment variables
load_dotenv()

host = os.getenv('SMTP_HOST')
port = os.getenv('SMTP_PORT')
user = os.getenv('SMTP_USER')
password = os.getenv('SMTP_PASS')

print("--- SMTP Configuration Check ---")
print(f"SMTP_HOST: {host}")
print(f"SMTP_PORT: {port}")
print(f"SMTP_USER: {user}")
# Do not print the actual password
print(f"SMTP_PASS: {'[SET]' if password else '[NOT SET]'}")

if not all([host, port, user, password]):
    print("\n[ERROR] Missing one or more SMTP configuration variables in .env")
else:
    print("\nAttempting to connect to SMTP server...")
    try:
        port = int(port)
        if port == 465:
            server = smtplib.SMTP_SSL(host, port)
        else:
            server = smtplib.SMTP(host, port)
            server.starttls()
        
        print("[SUCCESS] Connected to SMTP server.")
        
        print("Attempting to login...")
        server.login(user, password)
        print("[SUCCESS] Login successful!")
        
        server.quit()
    except Exception as e:
        print(f"\n[ERROR] Connection or Login failed: {e}")
