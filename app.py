import os
import streamlit as st

from dotenv import load_dotenv
from typing import TypedDict
from datetime import datetime, timedelta

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from memory.session_memory import (
    save_session_memory,
    get_student_memory,
    get_all_signals,
    generate_daily_plan,
    mark_signal_resolved,
    mark_all_signals_resolved,
    log_completed_checkin
)

from calendar_client import create_calendar_event


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


# M5 Memory State

if "student_memory" not in st.session_state:
    st.session_state.student_memory = []


# M7 Coach State

if "daily_plan" not in st.session_state:
    st.session_state.daily_plan = None



# -----------------------------
# Import Student Tools
# -----------------------------

from student_data import (
    get_student_ids,
    get_student_data,
    get_student_roster
)

from knowledge_data import (
    get_knowledge_data
)



# -----------------------------
# Create Model
# -----------------------------

model = ChatOpenAI(
    model="gpt-5.4-mini-2026-03-17",
    api_key=(
        os.getenv("OPENAI_API_KEY")
        or st.secrets["OPENAI_API_KEY"]
    )
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

Before answering say this and continue:

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

Your information sources are limited to:

1. Student Data Tool
2. Knowledge Base Tool

Do not answer to the questions that require information outside these sources.

==================================================
KNOWLEDGE BASE RULES
==================================================

You have access to a knowledge base tool.

Use get_knowledge_data ONLY for:

- Subject explanations.
- Course concepts.
- Study questions.
- Academic doubts.


Important rules:

- For study-related questions, always use the knowledge base tool.
- Answer only using information returned by the knowledge base.
- Do not use your own general knowledge.
- Do not add facts that are not present in the retrieved content.


If the answer is not available in the knowledge base:

Respond:

"I don't have this topic in the course knowledge base."

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
- exam related problems


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
# View Switch (M7)
# -----------------------------

view = st.radio(
    "View",
    ["Student", "Coach"],
    horizontal=True
)



# ==================================================
# STUDENT VIEW (M1 - M6, unchanged)
# ==================================================

if view == "Student":


    # -----------------------------
    # Student Selection
    # -----------------------------

    student_ids = get_student_ids()


    selected_student = st.selectbox(
        "Select Student ID",
        student_ids
    )



    # -----------------------------
    # Load Student Memory M5
    # -----------------------------

    if selected_student != st.session_state.student_id:


        st.session_state.student_id = selected_student


        # Clear old session chat

        st.session_state.messages = []


        # Load previous memories from Mem0

        st.session_state.student_memory = get_student_memory(
            selected_student
        )



    # -----------------------------
    # Create Agent
    # -----------------------------

    agent = create_agent(
        model=model,
        tools=[
            get_student_data,
            get_knowledge_data
        ],
        system_prompt=SYSTEM_PROMPT,
        context_schema=StudentContext
    )



    # -----------------------------
    # UI
    # -----------------------------

    st.title(
        "🎓 Student Success Coach"
    )



    # -----------------------------
    # Display Chat History
    # -----------------------------

    for message in st.session_state.messages:

        with st.chat_message(
            message["role"]
        ):

            st.write(
                message["content"]
            )



    # -----------------------------
    # Chat Input
    # -----------------------------

    if prompt := st.chat_input(
        "Ask your coach"
    ):


        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )


        with st.chat_message("user"):

            st.write(prompt)



        with st.chat_message("assistant"):




            memory_message = {
                "role": "system",
                "content": f"""
    Previous student memory:

    {st.session_state.student_memory}

    You are given previous student context to improve coaching quality.

    Use this information silently while responding.

    Rules:
    - Never mention that you have memory or previous sessions.
    - Never say "I remember", "you told me before", or similar phrases.
    - Never reveal private stored details unless the student asks about their own progress.
    - Use previous context only to make responses more relevant.
    - Apply the context in some cases when earning preferences , study habits,academic patterns are required .

    If the stored context is unrelated to the current question, ignore it.

    """

            }



            result = agent.invoke(

                {
                    "messages": [
                        memory_message
                    ]
                    +
                    st.session_state.messages
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



    # -----------------------------
    # End Session - Save Memory
    # -----------------------------

    if st.button(
        "End Session"
    ):


        if st.session_state.messages:


            save_session_memory(
                st.session_state.student_id,
                st.session_state.messages
            )


            st.success(
                "Your session has been saved."
            )


            st.session_state.messages = []


            st.rerun()



        else:


            st.warning(
                "No conversation available to save."
            )



# ==================================================
# COACH VIEW (M7 - new)
# ==================================================



else:

    st.title(
        "📋 Coach Dashboard"
    )


    max_sessions = st.number_input(
        "Sessions coach can fit today",
        min_value=1,
        max_value=15,
        value=6
    )


    # M7: track which signals were marked done in this session
    # so the UI reflects it immediately without regenerating the plan

    if "resolved_today" not in st.session_state:
        st.session_state.resolved_today = set()


    if st.button("Generate Daily Plan"):

        roster = get_student_roster()

        student_ids = [
            row["student_id"] for row in roster
        ]

        signals = get_all_signals(student_ids)

        plan = generate_daily_plan(
            signals,
            roster,
            max_sessions_today=max_sessions
        )

        st.session_state.daily_plan = plan

        # reset resolved tracking for the new plan
        st.session_state.resolved_today = set()



    plan = st.session_state.daily_plan


    if plan:


        st.subheader("Today")

        for entry in plan.get("today", []):

            col1, col2 = st.columns([4, 1])

            session_type = entry.get("session_type") or "check_in"

            signal_id = entry.get("signal_id")

            # use student_id as the tracking key when there's no signal_id,
            # so each no-signal entry can still be marked done independently

            tracking_key = signal_id or f"checkin_{entry['student_id']}"

            is_done = tracking_key in st.session_state.resolved_today


            with col1:

                status = " ✅ Done" if is_done else ""

                st.markdown(
                    f"**{entry['student_name']}** — {session_type.replace('_', ' ').title()}{status}  \n"
                    f"_{entry['reason']}_"
                )

            with col2:

                if is_done:

                    st.markdown("✅ **Done**")

                else:

                    if st.button(
                        "Mark Completed",
                        key=f"resolve_{tracking_key}"
                    ):

                        if signal_id:

                            # one meeting closes ALL open signals
                            # for this student, not just this one
                            mark_all_signals_resolved(entry["student_id"])

                        else:

                            log_completed_checkin(
                                entry["student_id"],
                                session_type,
                                entry["reason"]
                            )

                        st.session_state.resolved_today.add(tracking_key)

                        st.rerun()

                        



        st.subheader("Deferred to Tomorrow")

        for entry in plan.get("tomorrow", []):

            st.markdown(
                f"**{entry['student_name']}** — {entry['reason']}"
            )



        # -----------------------------
        # Calendar Invite Scheduling
        # -----------------------------

        st.subheader("Schedule Calendar Invites")

        start_time_input = st.time_input(
            "Start time for today's sessions",
            value=datetime.now().replace(
                hour=10, minute=0, second=0, microsecond=0
            ).time()
        )

        session_length = st.number_input(
            "Session length (minutes)",
            min_value=10,
            max_value=120,
            value=30,
            step=5
        )


        if plan.get("today") and st.button("Create Calendar Invites for Today"):

            start_time = datetime.now().replace(
                hour=start_time_input.hour,
                minute=start_time_input.minute,
                second=0,
                microsecond=0
            )

            created = 0

            for entry in plan["today"]:

                end_time = start_time + timedelta(minutes=session_length)

                session_type = entry.get("session_type") or "check_in"

                create_calendar_event(
                    summary=f"{session_type.replace('_', ' ').title()} — {entry['student_name']}",
                    description=entry["reason"],
                    start_dt=start_time,
                    end_dt=end_time
                )

                start_time = end_time

                created += 1

            st.success(f"Created {created} calendar invites starting at {start_time_input.strftime('%I:%M %p')}.")