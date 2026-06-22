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
# JSON PARSING HELPER
#
# BUGFIX: detect_student_signal() and generate_daily_plan() both ask
# the model to "return JSON only" and then call json.loads() directly
# on the response. Models frequently wrap that JSON in ```json ... ```
# fences (or add a stray sentence before/after it) even when told not
# to - when that happens json.loads() throws, and the caller silently
# falls back to a default ("unknown" signal / empty plan) with no
# indication anything went wrong. This strips common wrapping before
# parsing so a real response doesn't get discarded for a formatting
# quirk.
# ==================================================

def _parse_json_response(text):

    if not text:
        return text

    cleaned = text.strip()

    if cleaned.startswith("```"):

        cleaned = cleaned.strip("`")

        # drop a leading language tag like "json"
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:]

        cleaned = cleaned.strip()

    # if there's still leading/trailing prose around the object,
    # fall back to slicing between the first { and the last }
    if not cleaned.startswith("{"):

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end + 1]

    return cleaned



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


    # explicit timestamp, written by us rather than relying on
    # mem0's own created_at. generate_student_brief() needs this to
    # know which session summaries happened after the last coach
    # meeting - without it, every summary was being filtered out (see
    # the fix in generate_student_brief below).

    timestamp = datetime.now().isoformat()


    client.add(

        summary,

        user_id=student_id,

        metadata={

            "memory_type":
            "session_summary",


            "timestamp":
            timestamp

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



    # explicit timestamp, written by us, not relying on
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


            "concern":
            signal.get(
                "concern"
            ),


            "severity":
            signal.get(
                "severity"
            ),


            "urgency":
            signal.get(
                "urgency"
            ),


            # stored explicitly so daily plan generation
            # can reason about how old a signal is.

            "timestamp":
            timestamp,


            # tracks whether the coach has acted on this signal.
            # Starts unresolved until coach marks it completed.

            "resolved":
            False

        }

    )



    # capture the memory id so the coach can later mark
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
            _parse_json_response(response.content)
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

    signal = detect_student_signal(conversation)

    signal_id = save_student_signal(student_id, signal)

    
    student_name = student_id

    try:
        from student_data import get_student_roster
        roster = get_student_roster()
        match = next((r for r in roster if r["student_id"] == student_id), None)
        if match:
            student_name = match.get("name", student_id)
    except Exception:
        pass

    # NOTE: recurring-medium-severity escalation (escalate_for_recurring_pattern)
    # is implemented further down but intentionally disabled here for now -
    # for this demo, only a raw "high" severity signal auto-updates the plan.
    # Re-enable by swapping this back to:
    #
    #   effective_signal, pattern_note = escalate_for_recurring_pattern(
    #       student_id, signal
    #   )
    #   update_plan_for_new_signal(
    #       student_id, student_name, effective_signal, signal_id, pattern_note
    #   )

    update_plan_for_new_signal(
        student_id, student_name, signal, signal_id
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


    # mem0's get_all() can return either a plain list or a
    # dict shaped like {"results": [...]}, depending on version/
    # backend - normalize before using the result.

    if isinstance(factual_memory, dict):
        factual_memory = factual_memory.get("results", [])

    if isinstance(session_memory, dict):
        session_memory = session_memory.get("results", [])


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

            # skip anything already marked resolved by the coach

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


    # some mem0 versions/backends REPLACE a record's metadata
    # on update() rather than merge it, which would silently drop
    # memory_type, severity, urgency, etc. Anything that later filters
    # on those fields (e.g. get_last_meeting_timestamp, which filters
    # explicitly on metadata.memory_type == "student_signal") would
    # then quietly stop seeing this record at all. Fetching the
    # existing metadata and merging the new fields into it before
    # calling update() protects against that either way.

    try:
        existing = client.get(signal_id)
    except Exception:
        existing = None

    if existing:
        metadata = (existing.get("metadata", {}) or {}).copy()
    else:
        metadata = {}

    metadata["resolved"] = True
    metadata["resolved_at"] = resolved_at


    try:

        client.update(
            memory_id=signal_id,
            metadata=metadata
        )

        return True


    except Exception:

        # the replacement is written first, and the old record is
        # only removed once that succeeds, so a failure in add()
        # after a successful delete() can't permanently lose the
        # signal.

        if not existing:

            try:
                existing = client.get(signal_id)
            except Exception:
                return False

        try:

            text = existing.get("memory")
            user_id = existing.get("user_id")

            client.add(
                text,
                user_id=user_id,
                metadata=metadata
            )

            client.delete(signal_id)

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
- Each student appears AT MOST ONCE in the entire plan, even if they
  have multiple unresolved signals. Pick their single worst signal to
  justify the one session - do not create separate entries for the same
  student's different signals.
- Fill up to {max_sessions_today} "today" slots starting from the
  highest priority students down.
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
        plan = json.loads(_parse_json_response(response.content))
    except Exception:
        return {"today": [], "tomorrow": []}

    # --- M7 SIGNAL ID VALIDATION ---
    # Build the complete set of real signal IDs from the data we
    # actually passed to the model. If the model hallucinated an ID
    # or copied one incorrectly, null it out rather than letting a
    # bad reference propagate into the plan. A null signal_id is
    # handled safely everywhere downstream (mark_all_signals_resolved
    # resolves by student_id, and log_completed_checkin is called
    # instead when signal_id is None).

    valid_signal_ids = {
        sig["id"]
        for student_block in signals_by_student
        for sig in student_block["signals"]
        if sig.get("id")
    }

    for entry in plan.get("today", []):
        sid = entry.get("signal_id")
        if sid and sid not in valid_signal_ids:
            entry["signal_id"] = None

    for entry in plan.get("tomorrow", []):
        sid = entry.get("signal_id")
        if sid and sid not in valid_signal_ids:
            entry["signal_id"] = None

    return plan

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

    # session summary timestamps live under metadata (see
    # save_session_summary), with created_at as a fallback for older
    # records saved before that field existed.

    def _session_timestamp(s):
        return s.get("metadata", {}).get("timestamp") or s.get("created_at")

    if last_meeting_at:

        sessions_since_last_meeting = [
            s for s in all_sessions
            if _session_timestamp(s) and _session_timestamp(s) > last_meeting_at
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
# ==================================================
# M9: PERSISTENT DAILY PLAN STORAGE
# Stored in mem0 under a fixed coach-level id so any
# process (student session or coach session) can read/
# write the same plan. Keyed by date.
# ==================================================

PLAN_OWNER_ID = "__coach_daily_plan__"


def _today_key():
    return datetime.now().strftime("%Y-%m-%d")


def save_daily_plan(plan, max_sessions_today):
    """
    Overwrites today's persisted plan.

    ORDERING FIX: write the new record FIRST, then delete the old one.
    The previous version deleted first and then wrote - if the write
    failed after a successful delete, today's plan was permanently lost
    with no recovery path. Writing first means a failure in delete()
    leaves a harmless duplicate (the next load will just see two records
    and use the first one) rather than losing the plan entirely.
    """

    client = get_mem0_client()

    date_key = _today_key()

    payload = {
        "date": date_key,
        "max_sessions_today": max_sessions_today,
        "plan": plan
    }

    # Write the new record first.
    client.add(
        json.dumps(payload, default=str),
        user_id=PLAN_OWNER_ID,
        metadata={
            "memory_type": "daily_plan",
            "date": date_key
        }
    )

    # Now remove any previously existing records for today.
    # If this fails, the worst outcome is a duplicate - load_daily_plan_for_today
    # reads raw[0] which will be the record just written (mem0 returns
    # newest first in most backends), so the plan is still correct.
    existing = client.get_all(
        filters={
            "AND": [
                {"user_id": PLAN_OWNER_ID},
                {"metadata": {"memory_type": "daily_plan"}},
                {"metadata": {"date": date_key}}
            ]
        }
    )

    raw = existing.get("results", []) if isinstance(existing, dict) else existing

    # Keep the most recently written record (last in list after add),
    # delete everything else.
    if len(raw) > 1:
        # Sort by timestamp if available so we keep the newest.
        # If timestamps are unavailable, keep the last element
        # (mem0 typically appends, so last = most recent).
        def _ts(item):
            return item.get("metadata", {}).get("timestamp") or item.get("created_at") or ""

        sorted_records = sorted(raw, key=_ts)
        records_to_delete = sorted_records[:-1]  # delete all but the newest

        for item in records_to_delete:
            try:
                client.delete(item.get("id"))
            except Exception:
                pass


def load_daily_plan_for_today():

    client = get_mem0_client()

    date_key = _today_key()

    result = client.get_all(
        filters={
            "AND": [
                {"user_id": PLAN_OWNER_ID},
                {"metadata": {"memory_type": "daily_plan"}},
                {"metadata": {"date": date_key}}
            ]
        }
    )

    raw = result.get("results", []) if isinstance(result, dict) else result

    if not raw:
        return None

    try:
        return json.loads(raw[0].get("memory"))
    except Exception:
        return None


# ==================================================
# M9: PLAN CHANGE LOG
# Human-readable change entries shown to the coach as
# a banner the next time they open the dashboard - this
# is the "summary of what changed and why" requirement.
# ==================================================

def log_plan_change(summary_text):

    client = get_mem0_client()

    client.add(
        summary_text,
        user_id=PLAN_OWNER_ID,
        metadata={
            "memory_type": "plan_change",
            "date": _today_key(),
            "timestamp": datetime.now().isoformat()
        }
    )


def get_recent_plan_changes(since_timestamp=None):

    client = get_mem0_client()

    result = client.get_all(
        filters={
            "AND": [
                {"user_id": PLAN_OWNER_ID},
                {"metadata": {"memory_type": "plan_change"}},
                {"metadata": {"date": _today_key()}}
            ]
        }
    )

    raw = result.get("results", []) if isinstance(result, dict) else result

    changes = [
        {
            "text": item.get("memory"),
            "timestamp": item.get("metadata", {}).get("timestamp")
        }
        for item in raw
    ]

    if since_timestamp:
        changes = [c for c in changes if c["timestamp"] and c["timestamp"] > since_timestamp]

    changes.sort(key=lambda c: c["timestamp"] or "")

    return changes


# ==================================================
# BUGFIX (banner never clearing): get_recent_plan_changes()
# already supported filtering by since_timestamp, but nothing
# ever persisted "the coach has seen changes up to here" - so
# every dashboard load re-showed every change logged that day,
# growing forever. These two functions persist that watermark
# in mem0 (coach-level, keyed by date) so it survives reloads
# and works across devices/sessions, the same way the plan and
# conflicts already do.
# ==================================================

def get_changes_viewed_at():

    client = get_mem0_client()

    result = client.get_all(
        filters={
            "AND": [
                {"user_id": PLAN_OWNER_ID},
                {"metadata": {"memory_type": "changes_viewed"}},
                {"metadata": {"date": _today_key()}}
            ]
        }
    )

    raw = result.get("results", []) if isinstance(result, dict) else result

    if not raw:
        return None

    return raw[0].get("metadata", {}).get("timestamp")


def mark_changes_viewed():

    client = get_mem0_client()

    date_key = _today_key()

    existing = client.get_all(
        filters={
            "AND": [
                {"user_id": PLAN_OWNER_ID},
                {"metadata": {"memory_type": "changes_viewed"}},
                {"metadata": {"date": date_key}}
            ]
        }
    )

    raw = existing.get("results", []) if isinstance(existing, dict) else existing

    for item in raw:
        try:
            client.delete(item.get("id"))
        except Exception:
            pass

    client.add(
        "changes_viewed_marker",
        user_id=PLAN_OWNER_ID,
        metadata={
            "memory_type": "changes_viewed",
            "date": date_key,
            "timestamp": datetime.now().isoformat()
        }
    )


# ==================================================
# M9: PENDING CONFLICTS
# Used when two+ students are both critical and there
# isn't a clear slot to free up - the system does NOT
# decide, it asks the coach.
# ==================================================

def add_pending_conflict(conflict):

    client = get_mem0_client()

    client.add(
        json.dumps(conflict, default=str),
        user_id=PLAN_OWNER_ID,
        metadata={
            "memory_type": "plan_conflict",
            "date": _today_key(),
            "resolved": False,
            "timestamp": datetime.now().isoformat()
        }
    )


def get_pending_conflicts():

    client = get_mem0_client()

    result = client.get_all(
        filters={
            "AND": [
                {"user_id": PLAN_OWNER_ID},
                {"metadata": {"memory_type": "plan_conflict"}},
                {"metadata": {"date": _today_key()}}
            ]
        }
    )

    raw = result.get("results", []) if isinstance(result, dict) else result

    conflicts = []

    for item in raw:

        if item.get("metadata", {}).get("resolved", False):
            continue

        try:
            data = json.loads(item.get("memory"))
        except Exception:
            continue

        data["_id"] = item.get("id")
        conflicts.append(data)

    return conflicts


def resolve_pending_conflict(conflict_id):

    client = get_mem0_client()

    # Fetch existing metadata first and merge "resolved: True" into it
    # rather than passing only {"resolved": True} to client.update().
    # Some mem0 versions/backends REPLACE a record's metadata on
    # update() instead of merging - passing only the new field would
    # silently drop memory_type, date, and timestamp, causing
    # get_pending_conflicts() to never find this record again and
    # potentially showing it as unresolved on the next load.
    # This is the same fetch-merge pattern already used in
    # mark_signal_resolved().

    try:
        existing = client.get(conflict_id)
    except Exception:
        existing = None

    if existing:
        metadata = (existing.get("metadata", {}) or {}).copy()
    else:
        metadata = {}

    metadata["resolved"] = True

    try:
        client.update(
            memory_id=conflict_id,
            metadata=metadata
        )

    except Exception:

        # Fallback: write a new record with the merged metadata then
        # delete the old one. Write first so a failure in delete()
        # leaves a duplicate rather than losing the record entirely.

        if not existing:
            try:
                existing = client.get(conflict_id)
            except Exception:
                return

        try:
            text = existing.get("memory")
            user_id = existing.get("user_id")

            client.add(
                text,
                user_id=user_id,
                metadata=metadata
            )

            client.delete(conflict_id)

        except Exception:
            pass


# ==================================================
# M9: ESCALATE FOR RECURRING PATTERN
#
# generate_daily_plan() (a full replan) already reasons about a
# student's ENTIRE unresolved signal history and raises effective
# urgency when the same concern repeats across multiple "medium"
# signals - but update_plan_for_new_signal() only ever looked at the
# single signal just detected, so a student quietly stacking up
# several medium-severity signals on the same recurring concern would
# never trigger an automatic plan update in between full replans -
# only "Generate Daily Plan" would eventually catch it.
#
# This mirrors that same reasoning at the single-signal hot path: if
# the new signal is "medium" and there are enough other unresolved
# signals about the same concern, treat it as effectively "high" for
# the purposes of deciding whether to touch today's plan, and attach
# a note explaining why so the coach sees the real reason in the
# change log rather than a bare severity bump.
# ==================================================

RECURRING_PATTERN_THRESHOLD = 2  # this signal + at least this many prior matches


def _concern_key(concern_text):
    return (concern_text or "").strip().lower()


def escalate_for_recurring_pattern(student_id, signal):
    """
    Returns (effective_signal, pattern_note).

    effective_signal is a shallow copy of `signal` with severity
    possibly bumped to "high". pattern_note is None unless an
    escalation happened, in which case it's a short human-readable
    explanation suitable for the plan change log.
    """

    effective = dict(signal)

    if signal.get("severity") != "medium":
        return effective, None

    concern = _concern_key(signal.get("concern"))

    if not concern or concern == "none":
        return effective, None

    try:
        existing = get_all_signals([student_id])
        open_signals = existing[0]["signals"] if existing else []
    except Exception:
        return effective, None

    matching_medium_count = sum(
        1
        for s in open_signals
        if s.get("metadata", {}).get("severity") == "medium"
        and _concern_key(s.get("metadata", {}).get("concern")) == concern
    )

    # the signal we just saved is itself already in open_signals
    # (get_all_signals only excludes resolved ones), so
    # matching_medium_count already includes it.

    if matching_medium_count >= RECURRING_PATTERN_THRESHOLD:

        effective["severity"] = "high"

        pattern_note = (
            f"'{signal.get('concern')}' has now come up as a medium-severity "
            f"concern {matching_medium_count} times without being resolved - "
            f"treating it as a recurring pattern."
        )

        return effective, pattern_note

    return effective, None


# ==================================================
# M9: UPDATE PLAN WHEN A SERIOUS SIGNAL SURFACES
# Called right after a new signal is saved during a
# student session. Acts on "high" severity (including
# severity escalated by escalate_for_recurring_pattern
# above) - that's what "serious concern" means here.
# ==================================================

def update_plan_for_new_signal(student_id, student_name, signal, signal_id, pattern_note=None):

    if signal.get("severity") != "high":
        return  # not serious enough to touch the plan

    state = load_daily_plan_for_today()

    if not state:
        # No plan generated yet today - nothing to update.
        # Next "Generate Daily Plan" run will naturally pick this up.
        return

    plan = state["plan"]
    max_sessions = state["max_sessions_today"]

    today_list = plan.get("today", [])
    tomorrow_list = plan.get("tomorrow", [])

    if pattern_note:
        reason_text = (
            f"Recurring concern flagged again: {signal.get('concern')}. "
            f"{pattern_note} Recommended action: {signal.get('recommended_action')}."
        )
    else:
        reason_text = (
            f"New high-severity concern flagged: {signal.get('concern')}. "
            f"Recommended action: {signal.get('recommended_action')}."
        )

    # Already has a slot today - just note it, don't duplicate
    if any(e.get("student_id") == student_id for e in today_list):
        log_plan_change(
            f"{student_name} already has a session today; a new serious "
            f"concern came in ({signal.get('concern')}) - same slot now "
            f"covers this too."
        )
        return

    new_entry = {
        "student_id": student_id,
        "student_name": student_name,
        "session_type": "stress_support" if "stress" in signal.get("concern", "").lower() else "academic_support",
        "reason": reason_text,
        "signal_id": signal_id,
        "severity": "high",
        "completed": False,
        "invited": False
    }

    # Room available - just add it
    if len(today_list) < max_sessions:

        today_list.append(new_entry)
        plan["today"] = today_list

        log_plan_change(
            f"Added {student_name} to today's plan - {reason_text}"
        )

        save_daily_plan(plan, max_sessions)
        return

    # No room - look for a slot to free up: anyone today whose
    # severity is NOT high can be bumped to tomorrow.
    bumpable = [e for e in today_list if e.get("severity") != "high"]

    if bumpable:

        priority_order = {"none": 0, "low": 1, "medium": 2}
        bumpable.sort(key=lambda e: priority_order.get(e.get("severity", "none"), 0))

        bumped = bumpable[0]
        today_list.remove(bumped)

        bumped_for_tomorrow = {
            "student_id": bumped["student_id"],
            "student_name": bumped["student_name"],
            "reason": (
                f"Moved from today to tomorrow to make room for a more "
                f"urgent case ({student_name} - {signal.get('concern')})."
            ),
            "signal_id": bumped.get("signal_id")
        }

        tomorrow_list.append(bumped_for_tomorrow)
        today_list.append(new_entry)

        plan["today"] = today_list
        plan["tomorrow"] = tomorrow_list

        log_plan_change(
            f"{student_name} added to today's plan ({reason_text}). "
            f"{bumped['student_name']} moved to tomorrow to free the slot - "
            f"their concern was lower priority."
        )

        save_daily_plan(plan, max_sessions)
        return

    # Every slot today is already "high" severity - the system will
    # NOT decide who loses their slot. Surface it to the coach.
    explanation_text = (
        f"{student_name} just flagged a high-severity concern "
        f"({signal.get('concern')}), but today's schedule is full and "
        f"every current slot is also high severity. Pick who keeps "
        f"today's slot, who moves to tomorrow, or add an extra slot."
    )

    if pattern_note:
        explanation_text = (
            f"{student_name}'s concern ({signal.get('concern')}) has been "
            f"recurring at medium severity and is now being treated as high "
            f"priority - {pattern_note} Today's schedule is full and every "
            f"current slot is also high severity. Pick who keeps today's "
            f"slot, who moves to tomorrow, or add an extra slot."
        )

    add_pending_conflict({
        "new_student": {
            "student_id": student_id,
            "student_name": student_name,
            "reason": reason_text,
            "signal_id": signal_id
        },
        "competing_with": [
            {
                "student_id": e["student_id"],
                "student_name": e["student_name"],
                "reason": e.get("reason"),

                # include signal_id here so that if the coach later
                # bumps this student to tomorrow via the conflict
                # resolution UI, the original signal that justified
                # their slot isn't lost.

                "signal_id": e.get("signal_id")
            }
            for e in today_list
        ],
        "explanation": explanation_text
    })

    log_plan_change(
        f"⚠️ Conflict: {student_name}'s {'recurring' if pattern_note else 'new high-severity'} "
        f"concern can't be slotted today without bumping another critical "
        f"student - needs your call."
    )