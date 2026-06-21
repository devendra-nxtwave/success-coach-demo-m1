import os
import json
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_secret(key):
    value = os.getenv(key)
    if value:
        return value
    return st.secrets[key]

@st.cache_resource
def get_calendar_client():
    google_credentials = os.getenv("GOOGLE_CREDENTIALS")
    if google_credentials:
        credentials = json.loads(google_credentials)
    else:
        credentials = dict(st.secrets["google_credentials"])

    creds = Credentials.from_service_account_info(
        credentials,
        scopes=CALENDAR_SCOPES
    )
    return build("calendar", "v3", credentials=creds)

def create_calendar_event(summary, description, start_dt, end_dt):
    service = get_calendar_client()
    calendar_id = get_secret("COACH_CALENDAR_ID")

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
    }

    return service.events().insert(calendarId=calendar_id, body=event).execute()