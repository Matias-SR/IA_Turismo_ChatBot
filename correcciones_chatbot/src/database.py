import os
import json
from langchain_core.documents import Document
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from src.config import OPENAI_EMBEDDINGS_URL

def inicializar_base_vectores(api_key: str = None):
    """
    Carga el archivo documento.json, crea el índice FAISS en memoria
    y retorna un objeto retriever para realizar búsquedas semánticas.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "documento.json")
    
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"No se encontró el archivo de datos RAG en: {json_path}")
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    documents = []
    for item in data:
        documents.append(
            Document(
                page_content=item["content"],
                metadata={
                    "title": item["title"],
                    "category": item["category"],
                    "keywords": ", ".join(item.get("keywords", []))
                }
            )
        )
        
    # Splitter simple
    text_splitter = CharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    docs = text_splitter.split_documents(documents)
    
    # Inicializar embeddings de OpenAI (usará la API KEY configurada)
    embeddings = OpenAIEmbeddings(
        model="openai/text-embedding-3-small",
        api_key=api_key if api_key else "missing_key",
        base_url=OPENAI_EMBEDDINGS_URL
    )
    
    # Crear vector store FAISS en memoria
    vectorstore = FAISS.from_documents(docs, embeddings)
    
    # Retornar retriever con búsqueda por similitud
    return vectorstore.as_retriever(search_kwargs={"k": 2})
