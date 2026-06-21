# memory/session_memory.py

import os
import streamlit as st

from langchain_openai import ChatOpenAI

from memory.mem0_client import get_mem0_client



# ----------------------------------
# OpenAI Model
# Works locally + Streamlit Cloud
# ----------------------------------

summary_model = ChatOpenAI(
    model="gpt-5.4-mini-2026-03-17",
    api_key=(
        os.getenv("OPENAI_API_KEY")
        or st.secrets["OPENAI_API_KEY"]
    )
)



# ----------------------------------
# Save factual memory
# ----------------------------------

def save_factual_memory(
    student_id,
    facts
):

    client = get_mem0_client()


    client.add(
        facts,
        user_id=student_id,
        metadata={
            "memory_type": "factual_memory"
        }
    )



# ----------------------------------
# Save session summary
# ----------------------------------

def save_session_summary(
    student_id,
    summary
):

    client = get_mem0_client()


    client.add(
        summary,
        user_id=student_id,
        metadata={
            "memory_type": "session_summary"
        }
    )



# ----------------------------------
# Create short session summary
# ----------------------------------

def create_session_summary(
    conversation
):

    response = summary_model.invoke(
        f"""
Create a brief student coaching session summary.

Summarize only:

- Topics discussed
- Student difficulties identified
- Decisions made
- Action items or next steps


Rules:

- Keep it short.
- Do not include the full conversation.
- Do not include greetings.
- Do not include repeated information.


Conversation:

{conversation}


Return only the summary.
"""
    )


    return response.content



# ----------------------------------
# Extract long-term student facts
# ----------------------------------

def extract_factual_memory(
    conversation
):

    response = summary_model.invoke(
        f"""
Extract long-term useful facts about this student.

Store only:

- Learning preferences
- Study habits
- Academic difficulties
- Stress triggers
- Strategies that helped
- Recurring learning patterns


Do NOT store:

- One-time questions
- Session-specific details
- Temporary requests


Conversation:

{conversation}


Return only factual memories.
"""
    )


    return response.content



# ----------------------------------
# Save complete session
# ----------------------------------

def save_session_memory(
    student_id,
    messages
):


    if not messages:
        return



    conversation = "\n".join(
        [
            f"{message['role']}: {message['content']}"
            for message in messages
        ]
    )



    # Create short summary

    summary = create_session_summary(
        conversation
    )


    save_session_summary(
        student_id,
        summary
    )



    # Create factual memory

    facts = extract_factual_memory(
        conversation
    )


    save_factual_memory(
        student_id,
        facts
    )



# ----------------------------------
# Retrieve student memory
# ----------------------------------



def get_student_memory(student_id):

    client = get_mem0_client()

    memories = client.get_all(
        filters={
            "user_id": student_id
        }
    )

    return memories