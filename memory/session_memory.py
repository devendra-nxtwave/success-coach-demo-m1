import os
import json
import streamlit as st

from langchain_openai import ChatOpenAI

from memory.mem0_client import get_mem0_client



# ==================================================
# OpenAI Key
# Local + Streamlit Cloud
# ==================================================

def get_openai_key():

    key = os.getenv(
        "OPENAI_API_KEY"
    )

    if key:
        return key


    try:
        return st.secrets[
            "OPENAI_API_KEY"
        ]

    except Exception:

        raise Exception(
            "OPENAI_API_KEY is missing"
        )



# ==================================================
# OpenAI Model
# ==================================================

summary_model = ChatOpenAI(

    model="gpt-5.4-mini-2026-03-17",

    api_key=get_openai_key()

)



# ==================================================
# FACTUAL MEMORY
# ==================================================

def save_factual_memory(

    student_id,

    facts

):

    if not facts.strip():

        return


    client = get_mem0_client()


    client.add(

        facts,

        user_id=student_id,

        metadata={

            "memory_type":
            "factual_memory"

        }

    )



# ==================================================
# SESSION SUMMARY MEMORY
# ==================================================

def save_session_summary(

    student_id,

    summary

):

    if not summary.strip():

        return


    client = get_mem0_client()


    client.add(

        summary,

        user_id=student_id,

        metadata={

            "memory_type":
            "session_summary"

        }

    )



# ==================================================
# STUDENT SIGNAL MEMORY (M6)
# Coach-side only
# ==================================================

def save_student_signal(

    student_id,

    signal

):

    if not signal:

        return



    client = get_mem0_client()



    signal_text = f"""

Concern:

{signal.get("concern")}



Severity:

{signal.get("severity")}



Urgency:

{signal.get("urgency")}



Recommended Action:

{signal.get("recommended_action")}

"""



    client.add(

        signal_text,

        user_id=student_id,

        metadata={

            "memory_type":
            "student_signal",


            "severity":
            signal.get(
                "severity"
            ),


            "urgency":
            signal.get(
                "urgency"
            )

        }

    )



# ==================================================
# CREATE SESSION SUMMARY
# ==================================================

def create_session_summary(

    conversation

):


    response = summary_model.invoke(

        f"""

Create a short student coaching session summary.



Include only:

- Topics discussed
- Student difficulties
- Decisions made
- Action items



Rules:

- Do not include greetings.
- Do not include full conversation.
- Keep it concise.



Conversation:

{conversation}



Return only summary text.

"""

    )


    return response.content



# ==================================================
# EXTRACT FACTUAL MEMORY
# ==================================================

def extract_factual_memory(

    conversation

):


    response = summary_model.invoke(

        f"""

Extract long-term useful student facts.



Store only:

- Learning preferences
- Study habits
- Academic difficulties
- Stress triggers
- Helpful strategies
- Recurring patterns



Do not store:

- One-time questions
- Temporary requests
- Session-specific information



Conversation:

{conversation}



Return only factual memories.

"""

    )


    return response.content



# ==================================================
# DETECT STUDENT SIGNAL (M6)
# ==================================================

def detect_student_signal(

    conversation

):


    response = summary_model.invoke(

        f"""

Analyze this student coaching session.



Identify concerns requiring coach attention.



Look for:

- Exam stress
- Low motivation
- Learning difficulty
- Attendance issues
- Poor performance
- Repeated struggles



Return JSON only:



{{
"concern":"",
"severity":"",
"urgency":"",
"recommended_action":""
}}



Severity values:

low

medium

high



Urgency values:

today

tomorrow

monitor



If there is no concern:



{{
"concern":"none",
"severity":"low",
"urgency":"monitor",
"recommended_action":"No action required"
}}



Conversation:

{conversation}

"""

    )


    try:

        return json.loads(
            response.content
        )


    except Exception:

        return {

            "concern":
            "unknown",

            "severity":
            "low",

            "urgency":
            "monitor",

            "recommended_action":
            "Review student session"

        }



# ==================================================
# SAVE COMPLETE SESSION
# ==================================================

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



    # -----------------------------
    # Save session summary
    # -----------------------------

    summary = create_session_summary(

        conversation

    )


    save_session_summary(

        student_id,

        summary

    )



    # -----------------------------
    # Save factual memory
    # -----------------------------

    facts = extract_factual_memory(

        conversation

    )


    save_factual_memory(

        student_id,

        facts

    )



    # -----------------------------
    # Save student signal M6
    # -----------------------------

    signal = detect_student_signal(

        conversation

    )


    save_student_signal(

        student_id,

        signal

    )



# ==================================================
# GET STUDENT MEMORY FOR AI CHAT
# IMPORTANT:
# Does NOT return signals
# ==================================================

def get_student_memory(student_id):

    client = get_mem0_client()


    factual_memory = client.get_all(

        filters={

            "AND": [

                {
                    "user_id": student_id
                },

                {
                    "metadata": {
                        "memory_type": "factual_memory"
                    }
                }

            ]

        }

    )


    session_memory = client.get_all(

        filters={

            "AND": [

                {
                    "user_id": student_id
                },

                {
                    "metadata": {
                        "memory_type": "session_summary"
                    }
                }

            ]

        }

    )


    return {

        "factual_memory": factual_memory,

        "session_summary": session_memory

    }