import os
import streamlit as st
import gspread

from google.oauth2.service_account import Credentials
from langchain.tools import tool, ToolRuntime


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]


# -----------------------------
# Connect Google Sheets
# -----------------------------

@st.cache_resource
def connect_google_sheet():

    creds = Credentials.from_service_account_info(
        st.secrets["google_credentials"],
        scopes=SCOPES
    )

    client = gspread.authorize(creds)

    return client



# -----------------------------
# Get Student IDs
# -----------------------------

def get_student_ids():

    client = connect_google_sheet()

    spreadsheet = client.open_by_key(
        st.secrets["GOOGLE_SHEET_ID"]
    )


    roster_sheet = spreadsheet.worksheet(
        "roster"
    )


    records = roster_sheet.get_all_records()


    student_ids = [
        row["student_id"]
        for row in records
    ]


    return student_ids



# -----------------------------
# Student Data Tool
# -----------------------------

@tool
def get_student_data(runtime: ToolRuntime):

    """
    Fetch selected student's academic data
    from Google Sheets.
    """

    # Get selected student from application context

    student_id = runtime.context["student_id"]


    client = connect_google_sheet()


    spreadsheet = client.open_by_key(
        st.secrets["GOOGLE_SHEET_ID"]
    )


    # -----------------------------
    # Roster
    # -----------------------------

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



    # -----------------------------
    # Scores
    # -----------------------------

    scores = spreadsheet.worksheet(
        "exam_scores"
    ).get_all_records()


    student_scores = [
        row
        for row in scores
        if row["student_id"] == student_id
    ]



    # -----------------------------
    # Attendance
    # -----------------------------

    attendance = spreadsheet.worksheet(
        "attendance"
    ).get_all_records()


    student_attendance = [
        row
        for row in attendance
        if row["student_id"] == student_id
    ]



    # -----------------------------
    # Exams
    # -----------------------------

    exams = spreadsheet.worksheet(
        "exam_schedule"
    ).get_all_records()


    student_exams = [
        row
        for row in exams
        if row["student_id"] == student_id
    ]



    # -----------------------------
    # Return Data
    # -----------------------------

    return {

        "student_id": student_id,

        "student_name":
            student_info["name"]
            if student_info
            else "Unknown",

        "scores": student_scores,

        "attendance": student_attendance,

        "exams": student_exams
    }