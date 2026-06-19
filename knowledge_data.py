from langchain.tools import tool
import streamlit as st

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=st.secrets["OPENAI_API_KEY"]
)


vectorstore = Chroma(
    collection_name="course_material",
    embedding_function=embeddings,
    chroma_cloud_api_key=st.secrets["CHROMA_API_KEY"],
    tenant=st.secrets["CHROMA_TENANT"],
    database=st.secrets["CHROMA_DATABASE"]
)



@tool
def get_knowledge_data(question:str):

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
            "context":
            "No relevant course material found."
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