from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


# 1. Load markdown file
import os
from dotenv import load_dotenv

load_dotenv()

loader = TextLoader(
    "course_material.md",
    encoding="utf-8"
)

documents = loader.load()


# 2. Split into chunks

splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=150
)

chunks = splitter.split_documents(
    documents
)


# 3. Create embeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


# 4. Store in ChromaDB

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./knowledge_base"
)





print("Knowledge base created")