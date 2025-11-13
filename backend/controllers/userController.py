import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI    
from langchain_tavily import TavilySearch
from fastapi.responses import JSONResponse
import requests.exceptions
from services.dependencies import getLLM, getSupabaseClient, uploadResume, uploadText, uploadJson, getEmbeddingConfig, getResume, getLinkedInText, deleteFile, deleteResume, downloadJson
from services.userDataProcessor import ProcessUserData
import json
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)





async def initializeAPIkeys(data):
    gemini_key = data.get("geminiKey")
    tavily_key = data.get("tavilyKey")
    
    if not gemini_key or not tavily_key:
        return JSONResponse(status_code=400, content={"error": "Missing API keys"})
    
    # Validate Gemini API key
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", api_key=gemini_key)
        response = llm.invoke("Hello Gemini!")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"There was an error connecting to Gemini API: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "Cannot reach Gemini API. Check your internet connection."}
        )
    except Exception as e:
        print(f"The gemini API key provided did not work: {e}")
        return JSONResponse(
            status_code=400, 
            content={"error": "Invalid Gemini API key"}
        )
    
    # Validate Tavily API key
    try:
        tavily_client = TavilySearch(tavily_api_key=tavily_key)
        result = tavily_client.invoke("test")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"There was an error connecting to Tavily API: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "Cannot reach Tavily API. Check your internet connection."}
        )
    except Exception as e:
        print(f"The tavily API key provided did not work: {e}")
        return JSONResponse(
            status_code=400, 
            content={"error": "Invalid Tavily API key"}
        )
    
    # Both keys are valid, save them
    env_path = os.path.join(os.getcwd(), ".env")
    
    existing_content = ""
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            existing_content = f.read()
    
    lines = existing_content.split("\n") if existing_content else []
    updated_lines = []
    gemini_found = False
    tavily_found = False
    
    for line in lines:
        if line.startswith("GEMINI_KEY="):
            updated_lines.append(f"GEMINI_KEY={gemini_key}")
            gemini_found = True
        elif line.startswith("TAVILY_KEY="):
            updated_lines.append(f"TAVILY_KEY={tavily_key}")
            tavily_found = True
        else:
            updated_lines.append(line)
    
    if not gemini_found:
        updated_lines.append(f"GEMINI_KEY={gemini_key}")
    if not tavily_found:
        updated_lines.append(f"TAVILY_KEY={tavily_key}")
    
    with open(env_path, "w") as f:
        f.write("\n".join(updated_lines))
    
    # Reload environment variables
    
    load_dotenv(override=True)
    
    return JSONResponse(
        status_code=200,
        content={"message": "API keys validated and saved successfully"}
    )

async def processUserData(linkedinText, resume, email):
    if not linkedinText or not linkedinText.strip() or not resume or not email:
        return JSONResponse(
            status_code=400,
            content={"error": "User data is missing or empty"}
        )
        
    # Validate resume is a PDF
    if resume.content_type != "application/pdf":
        return JSONResponse(
            status_code=400,
            content={"error": "Resume must be a PDF file"}
        )
    
    
    try:
        llm = getLLM()
        supabaseClient = getSupabaseClient()
        embeddingConfig = getEmbeddingConfig()


        userDataProcessor = ProcessUserData(llm, embeddingConfig)
        userDataProcessor.resumeExtractor
        resumeText = await userDataProcessor.extractResume(resume)

        await resume.seek(0)
        logger.info("Uploading resume to Supabase")
        await uploadResume(supabaseClient, resume, f"{email}/resume/{resume.filename}")
        
        logger.info("Uploading LinkedIn text to Supabase")
        await uploadText(supabaseClient, linkedinText, f"{email}/linkedin/linkedinData.txt")
        
        # Upload extracted text
        logger.info("Uploading extracted resume text")
        await uploadText(supabaseClient, resumeText, f"{email}/resume/resumeData.txt")


        userDataProcessor.resumeChunker
        resumeChunks = await userDataProcessor.chunkResume(resumeText)
        await uploadJson(supabaseClient, resumeChunks["chunks"], f"{email}/resume/resumeChunks.json")
        await uploadJson(supabaseClient, resumeChunks["semanticChunks"], f"{email}/resume/resumeSemanticChunks.json")
        logger.info("Uploading extracted resume chunks")

        userDataProcessor.linkedinChunker
        linkedinChunks = await userDataProcessor.chunkLinkedin(linkedinText)
        await uploadJson(supabaseClient, linkedinChunks["chunks"], f"{email}/linkedin/linkedinChunks.json")
        await uploadJson(supabaseClient, linkedinChunks["semanticChunks"], f"{email}/linkedin/linkedinSemanticChunks.json")
        logger.info("Uploading extracted LinkedIn chunks")
       
        fullUserData = []

        allChunks = linkedinChunks["semanticChunks"]["chunks"] + resumeChunks["semanticChunks"]["chunks"]
        await uploadJson(supabaseClient, allChunks, f"{email}/mergingData/unprocessedUserData.json")
        logger.info("Uploading unprocessed user data chunks")


        processedChunks = userDataProcessor.filterChunks(allChunks)
        await uploadJson(supabaseClient, processedChunks["validChunks"], f"{email}/mergingData/validChunks.json")
        await uploadJson(supabaseClient, processedChunks["naCompanyChunks"], f"{email}/mergingData/naCompanyChunks.json")
        logger.info("Uploading filtered user data chunks")
        
        hasValidDuplicates = bool(processedChunks["validChunks"]["similar"])
        hasNaDuplicates = bool(processedChunks["naCompanyChunks"]["similar"])

        if hasValidDuplicates:
            sortedValidChunks = await userDataProcessor.sortChunks(processedChunks["validChunks"]['unsimilar'])
            await uploadJson(supabaseClient, sortedValidChunks, f"{email}/mergingData/sortedValidChunks.json")
            if sortedValidChunks['similar']:
                processedChunks["validChunks"]['similar'].extend(sortedValidChunks['similar'])
            mergedValidChunks = await userDataProcessor.mergeChunks(processedChunks["validChunks"]['similar'])
            fullUserData.extend(mergedValidChunks['chunks'])
            
            
            fullUserData.extend(sortedValidChunks['unsimilar'])
        else:
            fullUserData.extend(processedChunks["validChunks"]["unsimilar"])
        logger.info(f"Merged valid duplicates. Total chunks so far: {len(fullUserData)}")

        if hasNaDuplicates:
            sortedNaChunks = await userDataProcessor.sortChunks(processedChunks["naCompanyChunks"]['unsimilar'])
            await uploadJson(supabaseClient, sortedNaChunks, f"{email}/mergingData/sortedNaChunks.json")
            if sortedNaChunks['similar']:
                processedChunks["naCompanyChunks"]['similar'].extend(sortedNaChunks['similar'])
            mergedNaChunks = await userDataProcessor.mergeChunks(processedChunks["naCompanyChunks"]['similar'])
            fullUserData.extend(mergedNaChunks['chunks'])
            
            fullUserData.extend(sortedNaChunks['unsimilar'])
        else:
            fullUserData.extend(processedChunks["naCompanyChunks"]["unsimilar"])
        logger.info(f"Merged N/A company duplicates. Total chunks so far: {len(fullUserData)}")

        logger.info(
            f"User profile construction complete: "
            f"{len(fullUserData)} total chunks "
        )
        await uploadJson(supabaseClient, fullUserData, f"{email}/fullUserProfile.json")
        logger.info("Uploading full user profile data")
        
        await userDataProcessor.generateEmbeddings(supabaseClient, email, fullUserData)
        logger.info("Generated and stored embeddings for user data")




        return JSONResponse(
            status_code=200,
            content={
                "message": "User data processed successfully",
            }
        )
        
    except ValueError as ve:
        # Validation errors (400 - Bad Request)
        logger.error(f"Validation error processing user data: {ve}", exc_info=True)
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation error processing user data"
            }
        )
    
    except Exception as e:
        # All other errors (500 - Internal Server Error)
        logger.error(f"Error processing user data for {email}: {type(e).__name__}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to process user data",
            }
        )

async def getUserProfile(data):
    email = data.get("email")
    if not email:
        return JSONResponse(
            status_code=400,
            content={"error": "Email not provided"}
        )

    try:
        supabaseClient = getSupabaseClient()
        logger.info(f"Retrieving user profile for {email}")
        linkedinText = await getLinkedInText(supabaseClient, f"{email}/linkedin/linkedinData.txt")
        fileName, resume = await getResume(supabaseClient, f"{email}/resume", email)
        return JSONResponse(
            status_code=200,
            content={
                "linkedinText": linkedinText,
                "resumeBase64": resume,  # ✅ Changed from "resume"
                "resumeFilename": fileName      # ✅ Changed from "fileName"
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving user profile for {email}: {type(e).__name__}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve user profile",
            }
        )

async def updateUserProfile(email, updateLinkedin, updateResume, linkedinText, resume):
    if not email:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required fields"}
        )
    try:
        supabaseClient = getSupabaseClient()
        llm = getLLM()
        embeddingConfig = getEmbeddingConfig()
        userDataProcessor = ProcessUserData(llm, embeddingConfig)

        if updateLinkedin:
            if not linkedinText:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Missing LinkedIn text"}
                )
            await deleteFile(supabaseClient, f"{email}/linkedin/linkedinData.txt")
            await deleteFile(supabaseClient, f"{email}/linkedin/linkedinChunks.json")
            await deleteFile(supabaseClient, f"{email}/linkedin/linkedinSemanticChunks.json")

            await uploadText(supabaseClient, linkedinText, f"{email}/linkedin/linkedinData.txt")
            userDataProcessor.linkedinChunker
            linkedinChunks = await userDataProcessor.chunkLinkedin(linkedinText)
            await uploadJson(supabaseClient, linkedinChunks["chunks"], f"{email}/linkedin/linkedinChunks.json")
            await uploadJson(supabaseClient, linkedinChunks["semanticChunks"], f"{email}/linkedin/linkedinSemanticChunks.json")
            logger.info("Uploading updated extracted Linkedin chunks")

        if updateResume:
            logger.info(f"Updating resume for {email}")
            
            # Validate resume is a PDF
            if resume.content_type != "application/pdf":
                return JSONResponse(
                    status_code=400,
                    content={"error": "Resume must be a PDF file"}
                )
            await deleteResume(supabaseClient, f"{email}/resume/", email)
            await deleteFile(supabaseClient, f"{email}/resume/resumeData.txt")
            await deleteFile(supabaseClient, f"{email}/resume/resumeChunks.json")
            await deleteFile(supabaseClient, f"{email}/resume/resumeSemanticChunks.json")
            userDataProcessor.resumeExtractor
            resumeText = await userDataProcessor.extractResume(resume)

            await resume.seek(0)
            logger.info("Uploading updated resume to Supabase")
            await uploadResume(supabaseClient, resume, f"{email}/resume/{resume.filename}")
            logger.info("Uploading updated extracted resume text")
            await uploadText(supabaseClient, resumeText, f"{email}/resume/resumeData.txt")


            userDataProcessor.resumeChunker
            resumeChunks = await userDataProcessor.chunkResume(resumeText)
            await uploadJson(supabaseClient, resumeChunks["chunks"], f"{email}/resume/resumeChunks.json")
            await uploadJson(supabaseClient, resumeChunks["semanticChunks"], f"{email}/resume/resumeSemanticChunks.json")
            logger.info("Uploading extracted resume chunks")

        resumeChunks = await downloadJson(supabaseClient, f"{email}/resume/resumeSemanticChunks.json")
        linkedinChunks = await downloadJson(supabaseClient, f"{email}/linkedin/linkedinSemanticChunks.json")

        await deleteFile(supabaseClient, f"{email}/mergingData/unprocessedUserData.json")
        await deleteFile(supabaseClient, f"{email}/mergingData/validChunks.json")
        await deleteFile(supabaseClient, f"{email}/mergingData/naCompanyChunks.json")
        await deleteFile(supabaseClient, f"{email}/mergingData/sortedValidChunks.json")
        await deleteFile(supabaseClient, f"{email}/mergingData/sortedNaChunks.json")
        await deleteFile(supabaseClient, f"{email}/fullUserProfile.json")

        fullUserData = []

        allChunks = linkedinChunks["chunks"] + resumeChunks["chunks"]
        await uploadJson(supabaseClient, allChunks, f"{email}/mergingData/unprocessedUserData.json")
        logger.info("Uploading unprocessed user data chunks")


        processedChunks = userDataProcessor.filterChunks(allChunks)
        await uploadJson(supabaseClient, processedChunks["validChunks"], f"{email}/mergingData/validChunks.json")
        await uploadJson(supabaseClient, processedChunks["naCompanyChunks"], f"{email}/mergingData/naCompanyChunks.json")
        logger.info("Uploading filtered user data chunks")
        
        hasValidDuplicates = bool(processedChunks["validChunks"]["similar"])
        hasNaDuplicates = bool(processedChunks["naCompanyChunks"]["similar"])

        if hasValidDuplicates:
            sortedValidChunks = await userDataProcessor.sortChunks(processedChunks["validChunks"]['unsimilar'])
            await uploadJson(supabaseClient, sortedValidChunks, f"{email}/mergingData/sortedValidChunks.json")
            if sortedValidChunks['similar']:
                processedChunks["validChunks"]['similar'].extend(sortedValidChunks['similar'])
            mergedValidChunks = await userDataProcessor.mergeChunks(processedChunks["validChunks"]['similar'])
            fullUserData.extend(mergedValidChunks['chunks'])
            
             
            fullUserData.extend(sortedValidChunks['unsimilar'])
        else:
            fullUserData.extend(processedChunks["validChunks"]["unsimilar"])
        logger.info(f"Merged valid duplicates. Total chunks so far: {len(fullUserData)}")

        if hasNaDuplicates:
            sortedNaChunks = await userDataProcessor.sortChunks(processedChunks["naCompanyChunks"]['unsimilar'])
            await uploadJson(supabaseClient, sortedNaChunks, f"{email}/mergingData/sortedNaChunks.json")
            if sortedNaChunks['similar']:
                processedChunks["naCompanyChunks"]['similar'].extend(sortedNaChunks['similar'])
            mergedNaChunks = await userDataProcessor.mergeChunks(processedChunks["naCompanyChunks"]['similar'])
            fullUserData.extend(mergedNaChunks['chunks'])
            
            fullUserData.extend(sortedNaChunks['unsimilar'])
        else:
            fullUserData.extend(processedChunks["naCompanyChunks"]["unsimilar"])
        logger.info(f"Merged N/A company duplicates. Total chunks so far: {len(fullUserData)}")

        logger.info(
            f"User profile construction complete: "
            f"{len(fullUserData)} total chunks "
        )
        await uploadJson(supabaseClient, fullUserData, f"{email}/fullUserProfile.json")
        logger.info("Uploading full user profile data")
        await userDataProcessor.generateEmbeddings(supabaseClient, email, fullUserData)
        logger.info("Generated and stored embeddings for user data")

        return JSONResponse(
            status_code=200,
            content={"message": "User profile updated successfully"}
        )

    except Exception as e:
        logger.error(f"Error processing user data for {email}: {type(e).__name__}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to update user profile"}
        )

    
