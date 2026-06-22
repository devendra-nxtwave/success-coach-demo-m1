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
    log_completed_checkin,
    generate_student_brief,
    save_daily_plan,
    load_daily_plan_for_today,
    get_recent_plan_changes,
    get_pending_conflicts,
    resolve_pending_conflict,
    log_plan_change,
    get_changes_viewed_at,
    mark_changes_viewed
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
    get_student_roster,
    get_student_academic_data
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

You are given the full conversation history along with each new request.

If the conversation history contains no prior user messages (this is the
very first message of the session), begin your reply with this line and
then continue normally:

"I am your AI Success Coach. I am here to help you with your learning, academic goals, study plans, subject explanations, and education-related challenges."

If the history already contains prior user messages, do NOT repeat this
introduction - just answer the new question directly.

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


            # BUGFIX: reload memory immediately after saving so that if
            # the same student starts another session in this same tab
            # (without switching the selectbox away and back), the AI
            # already has what was just learned instead of working off
            # the stale snapshot loaded at the start of this session.

            st.session_state.student_memory = get_student_memory(
                st.session_state.student_id
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
# COACH VIEW (M7 - M9)
# ==================================================

else:

    st.title(
        "📋 Coach Dashboard"
    )


    # -----------------------------
    # Plan Generation Controls
    # (defined FIRST so it's available to the
    # conflict-resolution block below)
    # -----------------------------

    max_sessions = st.number_input(
        "Sessions coach can fit today",
        min_value=1,
        max_value=15,
        value=6
    )


    # -----------------------------
    # M9: load persisted plan.
    #
    # Every mutation path (Generate Daily Plan, conflict resolution,
    # Mark Completed, Create Calendar Invites, and the M9 auto-update
    # triggered from a student session) writes through save_daily_plan
    # immediately, so the persisted copy is always the source of
    # truth. We always re-sync session state from it on every render
    # so a plan changed elsewhere (or on a previous visit to this same
    # tab) is never stale.
    # -----------------------------

    persisted = load_daily_plan_for_today()

    if persisted:
        st.session_state.daily_plan = persisted["plan"]


    # -----------------------------
    # M9: banner - what changed automatically since
    # the plan was generated, before the coach does
    # anything else on this page.
    #
    # BUGFIX: previously this showed every change logged today on
    # every single render, because nothing ever recorded "the coach
    # has seen these already" - so the banner only ever grew and
    # never cleared, even across page reloads. get_changes_viewed_at
    # / mark_changes_viewed persist that watermark in mem0, scoped to
    # today, so the banner only shows what's new since the coach last
    # acknowledged it - and an explicit "Got it" dismiss button lets
    # the coach clear it without that being tied to any other action.
    # -----------------------------

    last_viewed_at = get_changes_viewed_at()

    changes = get_recent_plan_changes(since_timestamp=last_viewed_at)

    if changes:

        with st.container(border=True):

            st.markdown("### 🔔 Plan updated automatically")

            for c in changes:
                st.markdown(f"- {c['text']}")

            if st.button("Got it — dismiss"):
                mark_changes_viewed()
                st.rerun()


    # -----------------------------
    # M9: pending conflicts - coach must decide,
    # system will not pick for them
    # -----------------------------

    conflicts = get_pending_conflicts()

    for conflict in conflicts:

        with st.container(border=True):

            st.markdown("### ⚠️ Needs your call")

            st.markdown(conflict["explanation"])

            new_s = conflict["new_student"]

            st.markdown(
                f"**New case:** {new_s['student_name']} — {new_s['reason']}"
            )

            st.markdown("**Currently scheduled today (all high priority):**")

            for c in conflict["competing_with"]:
                st.markdown(f"- {c['student_name']} — {c['reason']}")

            choice = st.radio(
                "Who keeps today's slot?",
                options=(
                    [new_s["student_name"]]
                    + [c["student_name"] for c in conflict["competing_with"]]
                    + ["Add an extra slot instead"]
                ),
                key=f"conflict_choice_{conflict['_id']}"
            )

            # When the new student wins and there is more than one
            # competitor for the slot, ask explicitly who should be
            # bumped rather than always assuming competing_with[0].

            bump_target_name = None

            if choice == new_s["student_name"] and len(conflict["competing_with"]) > 1:

                bump_target_name = st.selectbox(
                    "Who should move to tomorrow to free up the slot?",
                    options=[c["student_name"] for c in conflict["competing_with"]],
                    key=f"conflict_bump_{conflict['_id']}"
                )

            if st.button(
                "Confirm decision",
                key=f"resolve_conflict_{conflict['_id']}"
            ):

                plan = st.session_state.daily_plan

                today_list = plan.get("today", [])
                tomorrow_list = plan.get("tomorrow", [])

                # BUGFIX: competing_with is a snapshot taken at the
                # moment the conflict was created. By the time the
                # coach resolves it, today_list may have changed (a
                # student could have been marked completed and
                # implicitly stayed, or another auto-update already
                # bumped them through a different path) - so the
                # student named in the snapshot might no longer be in
                # today_list at all. The old code did
                # next(c for c in competing_with if ...) with no
                # fallback, which raises StopIteration and crashes the
                # whole resolve action in that case. This degrades
                # gracefully instead: if the chosen bump target can't
                # be found in the live list anymore, treat the
                # conflict as already resolved by that other path and
                # just close it out instead of crashing.

                def _find_in_today(student_name_to_find):
                    return next(
                        (e for e in today_list if e["student_name"] == student_name_to_find),
                        None
                    )

                stale_conflict = False

                if choice == "Add an extra slot instead":

                    today_list.append({
                        "student_id": new_s["student_id"],
                        "student_name": new_s["student_name"],
                        "session_type": "stress_support",
                        "reason": new_s["reason"],
                        "signal_id": new_s["signal_id"],
                        "severity": "high",
                        "completed": False,
                        "invited": False
                    })


                elif choice == new_s["student_name"]:

                    if bump_target_name:
                        bumped_meta = next(
                            (c for c in conflict["competing_with"]
                             if c["student_name"] == bump_target_name),
                            None
                        )
                    else:
                        bumped_meta = conflict["competing_with"][0] if conflict["competing_with"] else None

                    bumped_live = _find_in_today(bumped_meta["student_name"]) if bumped_meta else None

                    if bumped_meta and bumped_live:

                        today_list = [
                            e for e in today_list
                            if e["student_id"] != bumped_live["student_id"]
                        ]

                        tomorrow_list.append({
                            "student_id": bumped_live["student_id"],
                            "student_name": bumped_live["student_name"],
                            "reason": (
                                f"Bumped to tomorrow by coach decision in favor "
                                f"of {new_s['student_name']}."
                            ),
                            "signal_id": bumped_live.get("signal_id")
                        })

                    else:
                        # The student we'd bump is no longer on today's
                        # list at all (already moved by another path) -
                        # nothing to bump, just add the new student.
                        stale_conflict = True

                    today_list.append({
                        "student_id": new_s["student_id"],
                        "student_name": new_s["student_name"],
                        "session_type": "stress_support",
                        "reason": new_s["reason"],
                        "signal_id": new_s["signal_id"],
                        "severity": "high",
                        "completed": False,
                        "invited": False
                    })


                else:

                    tomorrow_list.append({
                        "student_id": new_s["student_id"],
                        "student_name": new_s["student_name"],
                        "reason": (
                            f"Coach chose to keep {choice} today; "
                            f"{new_s['student_name']} deferred to tomorrow."
                        ),
                        "signal_id": new_s["signal_id"]
                    })


                plan["today"] = today_list
                plan["tomorrow"] = tomorrow_list

                st.session_state.daily_plan = plan

                # persist using the max_sessions currently set on screen
                save_daily_plan(plan, max_sessions)

                resolve_pending_conflict(conflict["_id"])

                if stale_conflict:
                    log_plan_change(
                        f"Coach resolved conflict: {choice} kept today's slot "
                        f"(the original competing student had already moved "
                        f"off today's list before this was confirmed)."
                    )
                else:
                    log_plan_change(
                        f"Coach resolved conflict: {choice} kept today's slot."
                    )

                st.rerun()


    # -----------------------------
    # Brief viewer
    # -----------------------------

    if st.session_state.get("current_brief"):

        with st.expander(
            f"📄 Brief — {st.session_state.current_brief['student_id']}",
            expanded=True
        ):
            st.markdown(st.session_state.current_brief["text"])


    # -----------------------------
    # BUGFIX (persistence across reloads/devices): "completed" and
    # "invited" status used to live ONLY in st.session_state
    # (resolved_today / invited_today sets), which reset on every page
    # reload and aren't shared across devices or browser tabs - even
    # though the plan itself is persisted via save_daily_plan. That
    # meant a refresh (or a second coach opening the dashboard) showed
    # everyone as "not done" / "not invited" again, with no protection
    # against re-resolving signals or re-sending calendar invites.
    #
    # Both flags now live directly on each plan entry (entry["completed"],
    # entry["invited"]) and are written through save_daily_plan
    # immediately, the same way every other plan mutation already is.
    # Older persisted plans (saved before this field existed) won't
    # have the keys, so every read below uses .get(..., False).
    # -----------------------------

    if st.button("Generate Daily Plan"):

        roster = get_student_roster()

        if not roster:

            # Stops here instead of falling through and calling
            # generate_daily_plan with an empty roster.

            st.warning("Roster is empty — check Google Sheets connection.")

        else:

            student_ids = [
                row["student_id"] for row in roster
            ]

            signals = get_all_signals(student_ids)

            plan = generate_daily_plan(
                signals,
                roster,
                max_sessions_today=max_sessions
            )

            # M9: attach severity to each today-entry so future
            # automatic updates know who's bumpable without
            # needing another LLM call. Also seed completed/invited
            # so every entry has a consistent shape from the start.

            signal_severity_lookup = {}

            for student_block in signals:
                for sig in student_block["signals"]:
                    signal_severity_lookup[sig["id"]] = sig["metadata"].get("severity", "low")

            for entry in plan.get("today", []):
                sig_id = entry.get("signal_id")
                entry["severity"] = (
                    signal_severity_lookup.get(sig_id, "none") if sig_id else "none"
                )
                entry["completed"] = False
                entry["invited"] = False

            st.session_state.daily_plan = plan

            # M9: persist so it's visible across sessions/devices
            save_daily_plan(plan, max_sessions)


    plan = st.session_state.daily_plan


    if plan:


        st.subheader("Today")

        if not plan.get("today"):
            st.caption("No sessions scheduled today.")

        for entry in plan.get("today", []):

            col1, col2 = st.columns([4, 1])

            session_type = entry.get("session_type") or "check_in"

            signal_id = entry.get("signal_id")

            # Done is driven ONLY by the coach explicitly clicking
            # "Mark Completed" — nothing else (plan generation,
            # calendar creation, background signal changes) can flip
            # this. Read directly off the persisted entry, not session
            # state, so it survives reloads.

            is_done = entry.get("completed", False)


            with col1:

                status = " ✅ Done" if is_done else ""

                st.markdown(
                    f"**{entry['student_name']}** — {session_type.replace('_', ' ').title()}{status}  \n"
                    f"_{entry['reason']}_"
                )

            with col2:

                if st.button("View Brief", key=f"brief_{entry['student_id']}"):

                    academic_data = get_student_academic_data(entry["student_id"])

                    brief = generate_student_brief(entry["student_id"], academic_data)

                    st.session_state.current_brief = {
                        "student_id": entry["student_id"],
                        "text": brief
                    }

                    st.rerun()


                if is_done:

                    st.markdown("✅ **Done**")

                else:

                    if st.button(
                        "Mark Completed",
                        key=f"resolve_{signal_id or ('checkin_' + entry['student_id'])}"
                    ):

                        # This is the ONLY place signals are ever
                        # marked resolved. Plan generation, calendar
                        # creation, and page reloads never touch this.

                        if signal_id:

                            # One meeting closes ALL open signals for
                            # this student, not just the one that put
                            # them on today's plan.
                            mark_all_signals_resolved(entry["student_id"])

                        else:

                            # Routine check-in with no originating
                            # signal — log a completed check-in record
                            # in mem0 so future plans know this student
                            # was seen today.
                            log_completed_checkin(
                                entry["student_id"],
                                session_type,
                                entry["reason"]
                            )

                        # Persist done status directly on the plan
                        # entry, then write the whole plan through so
                        # it survives a reload or another device.
                        entry["completed"] = True

                        save_daily_plan(plan, max_sessions)

                        st.rerun()



        st.subheader("Deferred to Tomorrow")

        if not plan.get("tomorrow"):
            st.caption("No students deferred to tomorrow.")

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

        # Invited status is read off the persisted plan entry, not
        # session state, so a reload (or someone else opening the
        # dashboard) doesn't lose track of who already has an invite
        # and re-send duplicates for everyone.

        pending_invites = [
            entry for entry in plan.get("today", [])
            if not entry.get("invited", False)
        ]

        if pending_invites and st.button("Create Calendar Invites for Today"):

            start_time = datetime.now().replace(
                hour=start_time_input.hour,
                minute=start_time_input.minute,
                second=0,
                microsecond=0
            )

            created = 0

            for entry in pending_invites:

                end_time = start_time + timedelta(minutes=session_length)

                session_type = entry.get("session_type") or "check_in"

                create_calendar_event(
                    summary=f"{session_type.replace('_', ' ').title()} — {entry['student_name']}",
                    description=entry["reason"],
                    start_dt=start_time,
                    end_dt=end_time
                )

                entry["invited"] = True

                start_time = end_time

                created += 1

            # persist the invited flags so a reload doesn't forget
            # who's already been invited
            save_daily_plan(plan, max_sessions)

            st.success(f"Created {created} calendar invites starting at {start_time_input.strftime('%I:%M %p')}.")

        elif plan.get("today") and not pending_invites:

            st.caption("Everyone on today's list already has a calendar invite.")