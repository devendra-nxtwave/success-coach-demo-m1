from langchain.tools import tool
import streamlit as st

import os
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


# -----------------------------
# Load Environment
# -----------------------------

load_dotenv()


def get_secret(key):

    value = os.getenv(key)

    if value:
        return value

    return st.secrets[key]



# -----------------------------
# Create Vector Store
# -----------------------------

@st.cache_resource
def get_vectorstore():

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=get_secret("OPENAI_API_KEY")
    )


    return Chroma(
        collection_name="course_material",
        embedding_function=embeddings,
        chroma_cloud_api_key=get_secret("CHROMA_API_KEY"),
        tenant=get_secret("CHROMA_TENANT"),
        database=get_secret("CHROMA_DATABASE")
    )



vectorstore = get_vectorstore()



# -----------------------------
# Knowledge Base Tool
# -----------------------------

@tool
def get_knowledge_data(question: str):

    """
    Retrieve information from the student's course material.

    Use this tool only for:
    - subject questions
    - concepts
    - coursework doubts

    Answer only from retrieved content.
    """


    docs = vectorstore.similarity_search(
        question,
        k=4
    )


    if not docs:

        return {
            "context": "No relevant course material found."
        }



    return {

        "context":
            "\n\n".join(
                [
                    doc.page_content
                    for doc in docs
                ]
            )

    }