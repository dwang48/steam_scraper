#!/usr/bin/env python3
"""
Standalone email test script to debug SMTP issues
"""
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

def test_email_config():
    print("=== Email Configuration Test ===")
    
    # Load environment variables
    load_dotenv()
    
    # Check if all required variables are set
    required_vars = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 'TO_EMAIL']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            # Hide password for security
            display_value = value if var != 'SMTP_PASS' else '*' * len(value)
            print(f"{var}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {missing_vars}")
        print("Make sure your .env file contains all required variables.")
        return False
    
    print("\n✅ All environment variables are set")
    return True

def test_smtp_connection():
    print("\n=== SMTP Connection Test ===")
    
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    
    try:
        print(f"Connecting to {smtp_host}:{smtp_port}...")
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            print("✅ Connected to SMTP server")
            
            print("Starting TLS...")
            smtp.starttls()
            print("✅ TLS started")
            
            print("Logging in...")
            smtp.login(smtp_user, smtp_pass)
            print("✅ Login successful")
            
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("Check your SMTP_USER and SMTP_PASS")
        if "gmail" in smtp_host.lower():
            print("For Gmail, make sure you're using an App Password, not your regular password")
            print("Visit: https://myaccount.google.com/apppasswords")
        return False
        
    except smtplib.SMTPConnectError as e:
        print(f"❌ Connection failed: {e}")
        print("Check your SMTP_HOST and SMTP_PORT")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_send_email():
    print("\n=== Send Test Email ===")
    
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    to_emails = os.environ.get("TO_EMAIL")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)
    
    # Parse email list
    email_list = [email.strip() for email in to_emails.split(",")]
    print(f"Testing email sending to {len(email_list)} recipients:")
    for i, email in enumerate(email_list, 1):
        print(f"  {i}. {email}")
    
    try:
        successful_sends = 0
        failed_sends = 0
        
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
            
            for i, to_email in enumerate(email_list):
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "Steam Crawler Test Email"
                    msg["From"] = from_email
                    msg["To"] = to_email
                    msg.set_content(f"This is a test email from the Steam crawler setup.\n\nRecipient: {to_email}\nSent to {len(email_list)} total recipients.\n\nIf you receive this, email configuration is working correctly!")
                    
                    smtp.send_message(msg)
                    successful_sends += 1
                    print(f"✅ Email sent to {to_email} ({i+1}/{len(email_list)})")
                    
                    # Add delay between emails if multiple recipients
                    if i < len(email_list) - 1 and len(email_list) > 1:
                        import time
                        time.sleep(2)
                        
                except Exception as e:
                    failed_sends += 1
                    print(f"❌ Failed to send to {to_email}: {e}")
            
        print(f"\n📊 Summary: {successful_sends} successful, {failed_sends} failed")
        if successful_sends > 0:
            print("Check your inbox (and spam folder) for test emails")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send emails: {e}")
        return False

def main():
    print("Steam Crawler Email Debug Tool\n")
    
    if not test_email_config():
        return
    
    if not test_smtp_connection():
        return
        
    test_send_email()
    
    print("\n=== Common Issues & Solutions ===")
    print("1. Gmail users: Use App Password, not regular password")
    print("2. Check if 2FA is enabled (required for App Passwords)")
    print("3. Verify SMTP settings for your email provider")
    print("4. Check firewall/network restrictions")
    print("5. Some ISPs block SMTP ports - try port 465 (SSL) instead of 587 (TLS)")

if __name__ == "__main__":
    main() 