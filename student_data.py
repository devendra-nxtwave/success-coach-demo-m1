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
    google_credentials = os.getenv(
        "GOOGLE_CREDENTIALS"
    )


    if google_credentials:

        credentials = json.loads(
            google_credentials
        )


    # Streamlit Cloud
    else:

        credentials = dict(
            st.secrets["google_credentials"]
        )


    creds = Credentials.from_service_account_info(
        credentials,
        scopes=SCOPES
    )


    client = gspread.authorize(
        creds
    )


    return client



# -----------------------------
# Get Student IDs
# -----------------------------

def get_student_ids():

    client = connect_google_sheet()


    spreadsheet = client.open_by_key(
        get_secret("GOOGLE_SHEET_ID")
    )


    roster_sheet = spreadsheet.worksheet(
        "roster"
    )


    records = roster_sheet.get_all_records()


    return [
        row["student_id"]
        for row in records
    ]



# -----------------------------
# Student Data Tool
# -----------------------------

@tool
def get_student_data(runtime: ToolRuntime):

    """
    Fetch selected student's academic data.
    """


    student_id = runtime.context["student_id"]


    client = connect_google_sheet()


    spreadsheet = client.open_by_key(
        get_secret("GOOGLE_SHEET_ID")
    )


    # Roster

    roster = spreadsheet.worksheet(
        "roster"
    ).get_all_records()


    student_info = next(
        (
            row
            for row in roster
            if row["student_id"] == student_id
        ),
        None
    )


    # Scores

    scores = spreadsheet.worksheet(
        "exam_scores"
    ).get_all_records()


    student_scores = [
        row
        for row in scores
        if row["student_id"] == student_id
    ]



    # Attendance

    attendance = spreadsheet.worksheet(
        "attendance"
    ).get_all_records()


    student_attendance = [
        row
        for row in attendance
        if row["student_id"] == student_id
    ]



    # Exams

    exams = spreadsheet.worksheet(
        "exam_schedule"
    ).get_all_records()


    student_exams = [
        row
        for row in exams
        if row["student_id"] == student_id
    ]



    return {

        "student_id": student_id,

        "student_name":
            student_info.get(
                "name",
                "Unknown"
            )
            if student_info
            else "Unknown",

        "scores": student_scores,

        "attendance": student_attendance,

        "exams": student_exams
    }