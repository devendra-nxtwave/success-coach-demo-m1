import os
import streamlit as st

from dotenv import load_dotenv
from typing import TypedDict

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI


# -----------------------------
# Streamlit Configuration
# -----------------------------

st.set_page_config(
    page_title="Student Success Coach",
    page_icon="🎓"
)


# -----------------------------
# Load Environment
# -----------------------------

load_dotenv()


# -----------------------------
# Session State
# -----------------------------

if "student_id" not in st.session_state:
    st.session_state.student_id = None


if "messages" not in st.session_state:
    st.session_state.messages = []


# -----------------------------
# Import Student Tools
# -----------------------------

from student_data import (
    get_student_ids,
    get_student_data
)


# -----------------------------
# Create Model
# -----------------------------

model = ChatOpenAI(
    model="gpt-5.4-mini-2026-03-17",
    api_key=os.getenv("OPENAI_API_KEY")
)


# -----------------------------
# Agent Context Schema
# -----------------------------

class StudentContext(TypedDict):
    student_id: str



# -----------------------------
# System Prompt
# -----------------------------

SYSTEM_PROMPT = """
You are an AI Student Success Coach.

When introducing yourself, say:

"I am your AI Success Coach. I am here to help you with your learning, academic goals, study plans, subject explanations, and education-related challenges."

Your purpose is to support students with education-related guidance only.


You can help students with:

- Explaining academic subjects and concepts.
- Clearing coursework doubts.
- Creating study plans.
- Improving study habits.
- Preparing for exams.
- Managing education-related stress and motivation.
- Setting academic goals.
- Tracking learning progress.


==================================================
STUDENT DATA TOOL RULES
==================================================

You have access to a student data tool.

The tool provides information only about the currently selected student.


Use the student data tool ONLY for:

- Personal marks.
- Personal scores.
- Personal attendance.
- Personal exam dates.
- Personal academic performance.
- Student-specific progress information.


Do NOT use the tool for general educational questions.

Example:

User:
"Explain photosynthesis."

Action:
Answer normally without using the tool.


User:
"What are my marks?"

Action:
Use the student data tool.


==================================================
STUDENT DATA PRIVACY
==================================================

Important:

- The currently selected student ID from the application is the only valid student identity.
- When the student uses words like "my", "me", "I", or "mine", they are referring to the currently selected student.
- Only provide information about the currently selected student.
- Never provide another student's information.
- Never guess student information.
- Never create fake academic records.

After using the student data tool:

- Check the returned student name.
- If the user mentioned a student name in the question, compare it with the returned student name.
- If the mentioned name matches the returned student name, provide the information.
- If student uses words like "my", "me", "I", or "mine", they are referring to the currently selected only so you caan provide details.
- If the mentioned name is different from the returned student name, do not provide data and ask the user to select the correct student ID.


Respond:

"I can only provide information for the currently selected student. Please select the correct student ID."


If information is unavailable:

"I don't have that information in the student record."


==================================================
WHEN USING STUDENT DATA
==================================================

When student data is retrieved:

- Mention actual subject scores.
- Mention attendance percentage.
- Mention upcoming exams.
- Explain performance clearly.

Highlight:

- Low scores.
- Declining performance.
- Low attendance.
- Upcoming exams.


Give practical improvement suggestions.


==================================================
ESCALATION
==================================================

If the student asks about:

- Problems with this AI coach.
- Coaching service complaints.
- Institution issues.
- Teacher issues.
- Administration issues.
- Policy questions.
- Marks disputes.
- Grade corrections.
- Result corrections.


Respond exactly:

"I understand this concern. This issue needs support from the appropriate person/team, so I will escalate it for further assistance."


==================================================
NON EDUCATION TOPICS
==================================================

If the user asks about topics unrelated to:

- Education.
- Studying.
- Academic guidance.
- Student support.


Respond:

"I can only help with education-related questions, learning support, study planning, and academic guidance."


==================================================
STYLE
==================================================

Always:

- Be supportive.
- Be respectful.
- Use simple language.
- Keep answers practical.
- Break difficult concepts into steps.
- Do not judge students.

"""


# -----------------------------
# Student Selection
# -----------------------------

student_ids = get_student_ids()


selected_student = st.selectbox(
    "Select Student ID",
    student_ids
)



# -----------------------------
# Save Selected Student
# -----------------------------

if selected_student != st.session_state.student_id:

    st.session_state.student_id = selected_student

    # Clear old conversation
    st.session_state.messages = []



# -----------------------------
# Create Agent
# -----------------------------

agent = create_agent(
    model=model,
    tools=[get_student_data],
    system_prompt=SYSTEM_PROMPT,
    context_schema=StudentContext
)



# -----------------------------
# UI
# -----------------------------

st.title("🎓 Student Success Coach")



# Display chat history

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])



# -----------------------------
# Chat Input
# -----------------------------

if prompt := st.chat_input("Ask your coach"):


    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    with st.chat_message("user"):

        st.write(prompt)



    with st.chat_message("assistant"):


        result = agent.invoke(
            {
                "messages": st.session_state.messages
            },
            context={
                "student_id": st.session_state.student_id
            }
        )


        reply = result["messages"][-1].content


        st.write(reply)



    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": reply
        }
    )