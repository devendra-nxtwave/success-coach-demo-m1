from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings



embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)



vectorstore = Chroma(
    persist_directory="./knowledge_base",
    embedding_function=embeddings
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