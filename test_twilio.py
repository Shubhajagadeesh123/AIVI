"""
Standalone Twilio check. Put this file in the same folder as app.py and .env, then run:

    python test_twilio.py +916362061178

It sends ONE test SMS and prints exactly what Twilio answers.
"""
import os, sys, re, requests
from dotenv import load_dotenv

load_dotenv()
sid   = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
frm   = (os.environ.get("TWILIO_SMS_FROM_NUMBER") or os.environ.get("TWILIO_PHONE_NUMBER") or "").strip()

print("Account SID set :", bool(sid))
print("Auth token set  :", bool(token))
print("From number     :", frm or "MISSING")

if len(sys.argv) < 2:
    sys.exit("Usage: python test_twilio.py +91XXXXXXXXXX")
to = "+" + re.sub(r"\D", "", sys.argv[1])
print("To number       :", to)

if not (sid and token and frm):
    sys.exit("\nSTOP: a Twilio value is missing from .env (is .env in this folder?)")

r = requests.post(
    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
    auth=(sid, token),
    data={"From": frm, "To": to, "Body": "AIVI Twilio test message"},
    timeout=15,
)
print("\nHTTP status:", r.status_code)
print(r.text)
if r.status_code == 201:
    print("\nOK: Twilio accepted the message. Check the Messaging log for delivery status.")