# knowledge_ingestion.py

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

import os
from dotenv import load_dotenv

load_dotenv()


# Load markdown file

loader = TextLoader(
    "course_material.md",
    encoding="utf-8"
)

documents = loader.load()


# Split into chunks

splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=150
)

chunks = splitter.split_documents(documents)


# Create embeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)


# Connect Chroma Cloud

vectorstore = Chroma(
    collection_name="course_material",
    embedding_function=embeddings,
    chroma_cloud_api_key=os.getenv("CHROMA_API_KEY"),
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE")
)


# Upload chunks


vectorstore.add_documents(
    documents=chunks
)


print("Number of chunks:", len(chunks))

print(
    "Chroma count:",
    vectorstore._collection.count()
)


print("Knowledge uploaded successfully")