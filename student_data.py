import os
import json
import streamlit as st
import gspread

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from langchain.tools import tool, ToolRuntime


# -----------------------------
# Load Environment
# -----------------------------

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]


# -----------------------------
# Get Config
# Local -> .env
# Cloud -> st.secrets
# -----------------------------

def get_secret(key):

    value = os.getenv(key)

    if value:
        return value

    return st.secrets[key]


# -----------------------------
# Connect Google Sheets
# -----------------------------

@st.cache_resource
def connect_google_sheet():

    # Local (.env)
    google_credentials = os.getenv("GOOGLE_CREDENTIALS")

    if google_credentials:
        credentials = json.loads(google_credentials)

    # Streamlit Cloud
    else:
        credentials = dict(st.secrets["google_credentials"])

    creds = Credentials.from_service_account_info(
        credentials,
        scopes=SCOPES
    )

    client = gspread.authorize(creds)

    return client


# -----------------------------
# BUGFIX: safe worksheet reader, used by every lookup below.
#
# Two problems this guards against:
#
# 1. A missing or renamed tab (gspread.WorksheetNotFound) used to
#    crash the whole chat turn, or the coach's "Generate Daily Plan" /
#    "View Brief" actions, instead of degrading gracefully.
#
# 2. Trailing blank rows in a Google Sheet come back from
#    get_all_records() as dicts where every value - including
#    student_id - is an empty string, not a missing key. So
#    row["student_id"] never raised an error, it just silently
#    returned "". That let blank rows leak into the student picker
#    dropdown, the roster used for daily planning, etc. Filtering on
#    a non-empty student_id here stops that at the source.
# -----------------------------

def _safe_get_records(spreadsheet, worksheet_name):

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()

    except Exception:
        return []

    return [
        row for row in records
        if str(row.get("student_id", "")).strip()
    ]


# -----------------------------
# Get Student IDs
# -----------------------------

def get_student_ids():

    client = connect_google_sheet()

    spreadsheet = client.open_by_key(
        get_secret("GOOGLE_SHEET_ID")
    )

    records = _safe_get_records(spreadsheet, "roster")

    return [row["student_id"] for row in records]


# -----------------------------
# Get Full Student Roster (M7)
# Used by coach view to list all students
# for daily plan generation.
# -----------------------------

def get_student_roster():

    client = connect_google_sheet()

    spreadsheet = client.open_by_key(
        get_secret("GOOGLE_SHEET_ID")
    )

    return _safe_get_records(spreadsheet, "roster")




def _fetch_student_academic_data(student_id):

    client = connect_google_sheet()

    spreadsheet = client.open_by_key(
        get_secret("GOOGLE_SHEET_ID")
    )

    roster = _safe_get_records(spreadsheet, "roster")

    student_info = next(
        (row for row in roster if row["student_id"] == student_id),
        None
    )

    scores = _safe_get_records(spreadsheet, "exam_scores")

    student_scores = [
        row for row in scores if row["student_id"] == student_id
    ]

    attendance = _safe_get_records(spreadsheet, "attendance")

    student_attendance = [
        row for row in attendance if row["student_id"] == student_id
    ]

    exams = _safe_get_records(spreadsheet, "exam_schedule")

    student_exams = [
        row for row in exams if row["student_id"] == student_id
    ]

    return {
        "student_id": student_id,
        "student_name": student_info.get("name", "Unknown") if student_info else "Unknown",
        "scores": student_scores,
        "attendance": student_attendance,
        "exams": student_exams
    }


# -----------------------------
# Student Data Tool
# -----------------------------

@tool
def get_student_data(runtime: ToolRuntime):
    """
    Fetch selected student's academic data.
    """

    student_id = runtime.context["student_id"]

    return _fetch_student_academic_data(student_id)


def get_student_academic_data(student_id):

    return _fetch_student_academic_data(student_id)