import os
import json
import streamlit as st

from datetime import datetime

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

        return None



    client = get_mem0_client()



    # M7: explicit timestamp, written by us, not relying on
    # mem0's own created_at (format/availability varies by backend).

    timestamp = datetime.now().isoformat()



    signal_text = f"""

Concern:

{signal.get("concern")}



Severity:

{signal.get("severity")}



Urgency:

{signal.get("urgency")}



Recommended Action:

{signal.get("recommended_action")}



Detected At:

{timestamp}

"""



    result = client.add(

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
            ),


            # M7: stored explicitly so daily plan generation
            # can reason about how old a signal is.

            "timestamp":
            timestamp,


            # M7: tracks whether the coach has acted on this signal.
            # Starts unresolved until coach marks it completed.

            "resolved":
            False

        }

    )



    # M7: capture the memory id so the coach can later mark
    # this exact signal as resolved.
    # mem0's add() response shape varies by version - handle common cases.

    try:

        if isinstance(result, dict) and "results" in result:
            return result["results"][0].get("id")

        elif isinstance(result, list):
            return result[0].get("id")

        elif isinstance(result, dict):
            return result.get("id")

    except Exception:

        pass


    return None



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



# ==================================================
# M7: GET ALL SIGNALS (Coach-side, across students)
# Only returns UNRESOLVED signals - resolved ones are
# excluded so the daily plan never re-considers issues
# the coach already handled.
# ==================================================

def get_all_signals(student_ids):

    client = get_mem0_client()

    collected = []


    for sid in student_ids:

        result = client.get_all(

            filters={

                "AND": [

                    {
                        "user_id": sid
                    },

                    {
                        "metadata": {
                            "memory_type": "student_signal"
                        }
                    }

                ]

            }

        )


        # mem0 return shape varies by version - handle both

        if isinstance(result, dict):
            raw_signals = result.get("results", [])
        else:
            raw_signals = result


        cleaned = [

            {

                "id":
                item.get("id"),

                "memory":
                item.get("memory"),

                "metadata":
                item.get("metadata", {}),


                # prefer our own explicit timestamp,
                # fall back to mem0's created_at if missing

                "timestamp":
                item.get("metadata", {}).get("timestamp")
                or item.get("created_at")

            }

            for item in raw_signals

            # M7: skip anything already marked resolved by the coach

            if not item.get("metadata", {}).get("resolved", False)

        ]


        collected.append(

            {
                "student_id": sid,
                "signals": cleaned
            }

        )


    return collected





# ==================================================
# M7: MARK SIGNAL RESOLVED (Coach action)
# Called internally by mark_all_signals_resolved for
# each open signal belonging to a student.
# ==================================================

def mark_signal_resolved(signal_id):

    if not signal_id:
        return False


    client = get_mem0_client()

    resolved_at = datetime.now().isoformat()


    try:

        client.update(
            memory_id=signal_id,
            metadata={
                "resolved": True,
                "resolved_at": resolved_at
            }
        )

        return True


    except Exception:

        try:

            existing = client.get(signal_id)

            text = existing.get("memory")
            metadata = existing.get("metadata", {}) or {}
            user_id = existing.get("user_id")

            metadata["resolved"] = True
            metadata["resolved_at"] = resolved_at

            client.delete(signal_id)

            client.add(
                text,
                user_id=user_id,
                metadata=metadata
            )

            return True

        except Exception:

            return False
# ==================================================
# M7: MARK ALL SIGNALS FOR A STUDENT AS RESOLVED
# Called after a single meeting - one meeting addresses
# all of that student's currently open concerns at once.
# ==================================================

def mark_all_signals_resolved(student_id):

    client = get_mem0_client()

    result = client.get_all(

        filters={

            "AND": [

                {"user_id": student_id},

                {"metadata": {"memory_type": "student_signal"}}

            ]

        }

    )

    if isinstance(result, dict):
        raw_signals = result.get("results", [])
    else:
        raw_signals = result

    resolved_count = 0

    for item in raw_signals:

        already_resolved = item.get("metadata", {}).get("resolved", False)

        if not already_resolved:

            signal_id = item.get("id")

            if signal_id:

                success = mark_signal_resolved(signal_id)

                if success:
                    resolved_count += 1

    return resolved_count




# ==================================================
# M7: GENERATE DAILY PLAN
# ==================================================

def generate_daily_plan(signals_by_student, roster, max_sessions_today=6):

    id_to_name = {

        row["student_id"]: row.get("name", "Unknown")

        for row in roster

    }


    today_str = datetime.now().strftime("%Y-%m-%d (%A)")

    payload = json.dumps(signals_by_student, default=str)


    response = summary_model.invoke(

        f"""

You are helping a student success coach plan their day.

Today's date is: {today_str}

The coach can realistically fit {max_sessions_today} sessions today.

Below is the FULL unresolved signal history for every student the coach
is responsible for. Resolved signals have already been excluded. Some
students have no signals at all - that is expected and meaningful, it
means nothing concerning is currently open for them, not that they
should be ignored.

Each signal has: id, timestamp (when it was detected), a severity, an
urgency, a concern, and a recommended action.

Roster name mapping:
{id_to_name}

Signal data (per student, may be an empty list):
{payload}

==================================================
STEP 1: Determine each student's worst unresolved state
==================================================

For each student, do NOT just look at their most recent signal. Look at
their ENTIRE unresolved signal history and find the single most
concerning one - this is usually the highest severity, but also weigh:

- A "high" severity signal from a few days ago that has no later signal
  showing improvement should be treated as still unresolved and urgent.
- A mild/low signal today does not cancel out a serious unresolved signal
  from earlier - the coach may not have acted on it yet.
- If the same concern repeats across multiple signals, treat it as a
  worsening or recurring pattern and raise its effective urgency, even if
  each individual signal was only "medium".
- A signal's age matters: the longer a "today" or "high" severity issue
  has gone unaddressed, the more urgent it is now, not less.
- Urgency label ("today"/"tomorrow"/"monitor") reflects how soon it
  seemed at detection time - treat it as a starting point, then adjust
  based on how much time has actually passed since the timestamp.

This gives you each student's current "priority level" - effectively
comparing their worst unresolved issue against everyone else's worst
unresolved issue, not just comparing today's freshest signals against
each other.

==================================================
STEP 2: Rank students and fill today's schedule
==================================================

- Sort all students by priority level (their worst unresolved signal),
  highest concern first.
- Each student appears AT MOST ONCE in the entire plan , even if they have multiple unresolved signals. Pick their
  single worst signal to justify the one session - do not create separate
  entries for the same student's different signals.
- Fill up to {max_sessions_today} "today" slots starting from the highest
  priority students down.
- High severity or clearly overdue issues should almost always get a slot.
- If there is room left in the {max_sessions_today} slots after placing
  every student who has a real concern, use the remaining slots for
  routine check-ins with students who have NO unresolved signals at all
  (or only "none"/"monitor" low-severity signals) - a coach should still
  touch base with everyone over time, not only firefight. Pick these
  students in roster order, and make the reason clearly say it's a
  routine check-in, not a concern.
- Any student with a genuine concern who does not fit in today's slots
  goes to "tomorrow" with a reason that reflects their actual concern and
  why it's being deferred (e.g. lower priority than others today).
- Students with no concern and no room left in today's slots are simply
  omitted entirely - do not list every leftover student in "tomorrow".

==================================================
REASON WRITING STYLE
==================================================

The "reason" field is what the coach reads to instantly understand why
this student is on today's list - write it like a short handoff note,
not a compressed label. Be specific and unambiguous:

- State WHAT the concern is, in plain words.
- State WHEN it matters (e.g. "exam is tomorrow", "attendance dropped
  this week") - never leave timing vague or implied.
- State WHY it needs attention now (overdue, recurring, high severity,
  or simply due for a routine check-in).

Bad example (vague, ambiguous):
"Unresolved exam stress for tomorrow is the next highest priority."

Good example (clear, specific):
"Has an exam tomorrow and has been expressing stress about it - needs
a quick study plan and some reassurance today."

Bad example:
"Overdue high-severity exam office issue."

Good example:
"Flagged a serious issue with the exam office several days ago and it
still hasn't been followed up on - needs urgent attention today."

Bad example:
"Routine check-in with no unresolved concern."

Good example:
"No active concerns, but hasn't had a check-in in a while - good time
for a quick catch-up."

Keep each reason to one or two plain sentences, written as if you're
briefing the coach in person.
==================================================
OUTPUT
==================================================

Each "today" entry needs: student_id, student_name, session_type (one of:
check_in, academic_support, stress_support, attendance_followup), reason
(one short plain sentence - state clearly if this is a routine check-in,
an overdue/unresolved issue, or a recurring pattern), and signal_id - the
"id" field of the specific signal from the data above that justifies this
session. If this is a routine check-in with no real concern, set
signal_id to null.

Each "tomorrow" entry needs: student_id, student_name, reason, and
signal_id (or null) following the same rule.

Return JSON only, no markdown, in this exact shape:

{{
  "today": [
    {{"student_id": "", "student_name": "", "session_type": "", "reason": "", "signal_id": null}}
  ],
  "tomorrow": [
    {{"student_id": "", "student_name": "", "reason": "", "signal_id": null}}
  ]
}}
==================================================
TIME LANGUAGE - MUST BE GROUNDED IN ACTUAL DATES
==================================================

Never copy relative time words (such as "tomorrow", "today", "this week")
directly from the original signal's urgency label or concern text. Those
words reflect what was true WHEN the signal was detected, not now.

Instead, calculate the actual gap between the signal's timestamp and
today's date ({today_str}), and describe timing using that real gap:

- If the signal is from today: you can say "today" or "just flagged".
- If the signal is 1-2 days old: say "a couple of days ago".
- If the signal is 3-6 days old: say "earlier this week" or "X days ago".
- If the signal is over a week old: say "over a week ago" or give the
  approximate number of days, and clearly flag it as overdue.

If the original concern itself mentioned an exam or deadline date (e.g.
"exam tomorrow" as detected 5 days ago), do NOT assume that date is still
accurate - that "tomorrow" was 5 days ago, so the exam may have already
happened. In this case, phrase it neutrally instead of restating a stale
date, e.g.: "flagged exam-related stress a few days ago - worth checking
whether the exam already happened and how it went," rather than
asserting an exam is still upcoming.

Only state an exam/deadline is still upcoming if the signal is recent
enough that the original timing plausibly still holds, or if nothing in
the data suggests it has passed.

"""

    )


    try:

        return json.loads(response.content)


    except Exception:

        return {

            "today": [],

            "tomorrow": []

        }

# ==================================================
# M7: LOG A COMPLETED CHECK-IN (no prior signal existed)
# Used when coach marks "Mark Completed" on a routine
# check-in entry that had no signal_id - so future plans
# know this student was seen recently.
# ==================================================

def log_completed_checkin(student_id, session_type, reason):

    client = get_mem0_client()

    timestamp = datetime.now().isoformat()


    checkin_text = f"""

Concern:

none



Severity:

low



Urgency:

monitor



Recommended Action:

Routine check-in completed ({session_type})



Reason:

{reason}



Detected At:

{timestamp}

"""


    result = client.add(

        checkin_text,

        user_id=student_id,

        metadata={

            "memory_type": "student_signal",
            "severity": "low",
            "urgency": "monitor",
            "timestamp": timestamp,

            # mark resolved immediately - this is a completed
            # check-in record, not an open concern

            "resolved": True

        }

    )


    try:

        if isinstance(result, dict) and "results" in result:
            return result["results"][0].get("id")

        elif isinstance(result, list):
            return result[0].get("id")

        elif isinstance(result, dict):
            return result.get("id")

    except Exception:
        pass

    return None

# ==================================================
# M8: GET LAST COACH MEETING TIMESTAMP

# ==================================================

def get_last_meeting_timestamp(student_id):

    client = get_mem0_client()

    result = client.get_all(

        filters={

            "AND": [

                {"user_id": student_id},

                {"metadata": {"memory_type": "student_signal"}}

            ]

        }

    )

    if isinstance(result, dict):
        raw_signals = result.get("results", [])
    else:
        raw_signals = result


    meeting_timestamps = []

    for item in raw_signals:

        metadata = item.get("metadata", {})

        if metadata.get("resolved"):

            # resolved_at = when the meeting happened
            # fall back to timestamp only for old records that
            # predate this field

            ts = metadata.get("resolved_at") or metadata.get("timestamp")

            if ts:
                meeting_timestamps.append(ts)


    if not meeting_timestamps:
        return None

    meeting_timestamps.sort(reverse=True)

    return meeting_timestamps[0]
def generate_student_brief(student_id, academic_data):

    memory = get_student_memory(student_id)

    open_signals_data = get_all_signals([student_id])

    open_signals = open_signals_data[0]["signals"] if open_signals_data else []

    last_meeting_at = get_last_meeting_timestamp(student_id)


    # Only keep session summaries that happened AFTER the last
    # coach meeting - these represent what's new since then.
    # If there's no last meeting, keep everything (first-ever brief).

    all_sessions = memory.get("session_summary", [])

    if last_meeting_at:

        sessions_since_last_meeting = [
            s for s in all_sessions
            if s.get("timestamp") and s["timestamp"] > last_meeting_at
        ]

    else:

        sessions_since_last_meeting = all_sessions


    today_str = datetime.now().strftime("%Y-%m-%d (%A)")

    payload = json.dumps(
        {
            "academic_data": academic_data,
            "factual_memory": memory.get("factual_memory"),
            "last_meeting_at": last_meeting_at,
            "session_summaries_since_last_meeting": sessions_since_last_meeting,
            "open_signals": open_signals
        },
        default=str
    )


    response = summary_model.invoke(

        f"""

You are preparing a student success coach for an upcoming 1-on-1 meeting.

Today's date is: {today_str}

"last_meeting_at" tells you exactly when the coach last had a real
meeting with this student (or null if they've never met).

"session_summaries_since_last_meeting" contains ONLY the student's AI
chat sessions that happened after that last meeting - this is genuinely
new information the coach hasn't seen yet. If last_meeting_at is null,
this contains their entire chat history instead, since there's no prior
meeting to compare against.

"factual_memory" contains long-term facts about this student - study
habits, stress triggers, recurring patterns - collected over all time,
not limited to any date range. Always consider all of it, it's
foundational context regardless of when it was learned.

"open_signals" contains every currently UNRESOLVED concern for this
student, regardless of when each was flagged - each has its own
timestamp.

Data:
{payload}

Write a short, focused pre-meeting brief with these sections:

1. CURRENT SITUATION - one or two sentences on where this student stands
   right now academically (recent scores, attendance trend, upcoming
   exams). Be specific with numbers if available.

2. WHAT'S CHANGED SINCE LAST MEETING - state how long ago the last
   coach meeting was (using last_meeting_at vs today). Then summarize
   what's new based ONLY on session_summaries_since_last_meeting and
   current academic data - do not reference anything from before that
   meeting. If last_meeting_at is null, say the coach has not met with
   this student yet, and briefly summarize their chat history instead.

3. OPEN CONCERNS - list every entry in open_signals in plain language,
   with how long ago each was flagged (using each signal's own timestamp
   vs today). If open_signals is empty, say there are no open concerns
   right now.

4. CONVERSATION STARTERS - 2-3 specific, natural questions or talking
   points the coach could open with today, grounded in the actual data
   above - factual memory, open concerns, and what's new since the last
   meeting.

Rules:
- Be concise - this is a quick brief before a meeting, not a report.
- Do not invent facts not present in the data.
- Never state a time gap vaguely - always calculate it from the actual
  timestamp against today's date.
- If a section has nothing relevant, say so briefly rather than padding.
- Write in plain, direct language a busy coach can skim in under a minute.

"""

    )


    return response.content