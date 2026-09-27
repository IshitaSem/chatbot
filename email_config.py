import os

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if present
    load_dotenv()
except ImportError:
    pass

# SENDER & SMTP CONFIGURATION
# Credentials must be provided via environment variables or a local .env file.
SENDER_EMAIL = os.environ.get("SENDER_EMAIL") or os.environ.get("SMTP_SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD") or os.environ.get("SMTP_SENDER_PASSWORD", "")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))

# Optional receiver/cafe notification email (if cafe staff also wants a copy)
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL") or os.environ.get("CAFE_NOTIFICATION_EMAIL", "")