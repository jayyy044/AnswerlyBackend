import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
from supabase import create_client, Client
import json
from voyageai import Client as VoyageClient
from langchain_tavily import TavilySearch
import base64

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)  # ← ADD THIS LINE

# Global instances (singleton pattern)
_llm = None
_embeddingconfig = None
_supabaseClient = None
_tavilyClient = None
# _query_embedder_instance = None
bucketName = 'answerlyData'

def getSupabaseClient():
    global _supabaseClient
    if _supabaseClient is None:
        sUrl = os.getenv("SUPABASE_URL")
        sApiKey = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not sUrl or not sApiKey:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env file")
        
        _supabaseClient = create_client(sUrl, sApiKey)
        logger.info("Supabase client initialized")
    
    return _supabaseClient


async def uploadResume(client, resume, filePath):
    try:
        fileBytes= await resume.read() 
        upload = client.storage.from_(bucketName).upload(
            filePath,
            fileBytes,
            {"content-type": "application/pdf"},
        )
        
        logger.info(f"Resume uploaded successfully to {bucketName}/{filePath}")
        
    except Exception as e:
        logger.error(f"Unexpected error while uploading resume: {e}")
        raise

async def uploadText(client, text, filePath):
    try:
        textBytes = text.encode('utf-8')
        upload = client.storage.from_(bucketName).upload(
            filePath,
            textBytes,
            {"content-type": "text/plain"},
        )
        logger.info(f"Text file uploaded successfully to {bucketName}/{filePath}")
    except Exception as e:
        logger.error(f"Unexpected error while uploading text file: {e}")
        raise

async def uploadJson(client, data, filePath):
    try:
        jsonBytes = json.dumps(data, indent=2).encode('utf-8')
        upload = client.storage.from_(bucketName).upload(
            filePath,
            jsonBytes,
            {"content-type": "application/json"},
        )
        logger.info(f"JSON file uploaded successfully to {bucketName}/{filePath}") 
    except Exception as e:
        logger.error(f"Unexpected error while uploading JSON file: {e}")
        raise

async def getResume(client, filePath, email):
    try:
        files = client.storage.from_(bucketName).list(filePath)
        resume = next((f for f in files if f['name'].lower().endswith('.pdf')), None)
        fileName = resume['name']
        resume_bytes = client.storage.from_(bucketName).download(f"{email}/resume/{fileName}")
        resumeBase64 = base64.b64encode(resume_bytes).decode('utf-8')
        logger.info(f"Resume downloaded successfully from {bucketName}/{email}/resume/{fileName}")
        return (fileName, resumeBase64)
    except Exception as e:
        logger.error(f"Unexpected error while downloading resume: {e}")
        raise

async def getLinkedInText(client, filePath):
    try:
        download = client.storage.from_(bucketName).download(filePath)
        linkedinBytes = download
        linkedinText = linkedinBytes.decode('utf-8')
        logger.info(f"LinkedIn text downloaded successfully from {bucketName}/{filePath}")
        return linkedinText
    except Exception as e:
        logger.error(f"Unexpected error while downloading LinkedIn text: {e}")
        raise

async def deleteFile(client, filePath: str):
    """Delete a file from Supabase Storage"""
    try:
        client.storage.from_(bucketName).remove(filePath)
        logger.info(f"Deleted file: {filePath}")
    except Exception as e:
        logger.warning(f"Could not delete {filePath}: {str(e)}")
        # Don't fail the whole operation if file doesn't exist

async def deleteResume(client, filePath, email):
    try:
        files = client.storage.from_(bucketName).list(filePath)
        resume = next((f for f in files if f['name'].lower().endswith('.pdf')), None)
        fileName = resume['name']
        client.storage.from_(bucketName).remove(f"{email}/resume/{fileName}")
        logger.info(f"Resume deleted successfully from {bucketName}/{email}/resume/{fileName}")
    except Exception as e:
        logger.error(f"Unexpected error while deleting resume: {e}")

async def downloadJson(client, filePath: str):
    """Download and parse JSON file from Supabase Storage"""
    try:
        response = client.storage.from_(bucketName).download(filePath)
        return json.loads(response.decode('utf-8'))
    except Exception as e:
        logger.error(f"Error downloading {filePath}: {str(e)}")
        raise

def getLLM():
    """Returns a shared LLM instance"""
    global _llm
    if _llm is None:
        apiKey = os.getenv("GEMINI_KEY")
        if not apiKey:
            raise ValueError("Missing GEMINI_KEY in .env file")
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=apiKey,
            temperature=0.0
        )
        logger.info("LLM initialized")  
    return _llm

def getEmbeddingConfig():
    """Configure the genai API with key"""
    global _embeddingconfig
    if _embeddingconfig is None:
        apiKey = os.getenv("VOYAGE_KEY")
        if not apiKey:  
            raise ValueError("Missing VOYAGE_KEY in .env file") 
        _embeddingconfig = VoyageClient(api_key=apiKey)  
        logger.info("Embedding config initialized")
    return _embeddingconfig

def getTavilyClient():
    global _tavilyClient
    if _tavilyClient is None:
        apiKey = os.getenv("TAVILY_KEY")
        if not apiKey:
            raise ValueError("Missing TAVILY_KEY in .env file") 
        _tavilyClient = TavilySearch(
            tavily_api_key=apiKey,
            max_results=10,
            search_depth="advanced",
            include_answer=True,
            include_domains=None,
            exclude_domains=None,
            topic="general",
            time_range="month"
        )
        logger.info("Tavily client initialized")
    return _tavilyClient

async def queryEmbedder(query: str, embedder: VoyageClient):
    logger.info(f"Generating query embedding for: {query}")

    result = embedder.embed(
        texts=[query],  # ← Must be a list! Changed from query to [query]
        model="voyage-3.5",
        input_type="query",  # Correct - use "query" for search queries
        output_dimension=1024,
        output_dtype="float"
    )
    
    embeddings = result.embeddings[0]  # ← Get first embedding since we only sent one query
    
    return embeddings




