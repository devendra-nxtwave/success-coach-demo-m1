# memory/session_memory.py

from memory.mem0_client import get_mem0_client


def save_session_memory(student_id, messages):

    if not messages:
        return


    client = get_mem0_client()


    conversation = "\n".join(
        [
            f"{m['role']}: {m['content']}"
            for m in messages
        ]
    )


    client.add(
        conversation,
        user_id=student_id
    )