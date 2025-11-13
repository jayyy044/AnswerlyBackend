from dotenv import load_dotenv
import os

from google import genai
from .textExtractor import TextExtractor
from .resumeChunker import ResumeChunker
from .linkedinChunker import LinkedinChunker
import json
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

from langchain_core.documents import Document
from typing import List, Dict, Any

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from .outputSchemas import UnifiedSemanticChunks, OptimalQuery, DeduplicationResult
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime


import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import shutil
import logging
from collections import defaultdict

load_dotenv()



class ProcessUserData:

    def __init__(self, llm, embedder):
        self.logger = logging.getLogger(__name__)
        self.modelName = "gemini-2.5-flash-lite"

        self.llm = llm
        self.embedder = embedder
     
        
        self._resumeExtractor = None
        self._resumeChunker = None
        self._linkedinChunker = None

        logging.info("Data Processor Initialized")
    
    #The @property makes it so when you call its like calling an attribute not a function 
    #extractor = procesuserdata.resumeExtractor no ()
    @property
    def resumeExtractor(self):
        if self._resumeExtractor is None:
            self._resumeExtractor = TextExtractor(self.modelName)
        return self._resumeExtractor

    async def extractResume(self, uploadedPdf):
        try:
            self.logger.info(f"Starting resume extraction for: {uploadedPdf.filename}")
            extracted_text = await self._resumeExtractor.extractFromPdf(uploadedPdf)
            self.logger.info(f"Resume extraction completed successfully for: {uploadedPdf.filename}")
            return extracted_text
            
        except ValueError as ve:
            # Validation errors - log and re-raise
            self.logger.error(f"Resume validation error: {ve}")
            raise
            
        except Exception as e:
            # Other errors - log with context and re-raise
            self.logger.error(
                f"Resume text extraction failed for '{uploadedPdf.filename}': {type(e).__name__}: {e}",
                exc_info=True
            )
            raise Exception(f"Resume extraction error: {e}") from e
    
    @property
    def resumeChunker(self):
        if self._resumeChunker is None:
            self._resumeChunker = ResumeChunker(self.llm)
        return self._resumeChunker 

    async def chunkResume(self, resumeText):
        return await self._resumeChunker.createResumeChunks(resumeText)


    @property
    def linkedinChunker(self):
        if self._linkedinChunker is None:
            self._linkedinChunker = LinkedinChunker(self.llm)
        return self._linkedinChunker
    
    async def chunkLinkedin(self, linkedinText):
        return await self._linkedinChunker.createLinkedinChunks(linkedinText)


    def fuzzy_match(self, str1, str2, threshold=0.85):
        """
        Check if two strings should be grouped together.
        Returns True if:
        1. String similarity >= threshold, OR
        2. One string is contained within the other
        """
        from difflib import SequenceMatcher
        
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()
        
        # First check: fuzzy string matching
        similarity = SequenceMatcher(None, s1, s2).ratio()
        if similarity >= threshold:
            return True
        
        # Second check: substring containment
        if s1 in s2 or s2 in s1:

            return True
        
        # Neither condition met
        return False

    def filterSimilarChunks(self, validChunks):
        
        similar = []
        unsimilar = []
        
        # Step 1: Group by section_type
        section_groups = defaultdict(list)
        for chunk in validChunks:
            section_type = chunk["metadata"].get("section_type", "Other")
            section_groups[section_type].append(chunk)
        
        # Step 2: Process each section separately
        for section_type, section_chunks in section_groups.items():
            # Step 2a: Group by similar company names within this section
            company_groups = []
            used_indices = set()
            
            for i, chunk in enumerate(section_chunks):
                if i in used_indices:
                    continue
                
                company1 = chunk["metadata"].get("company", "").strip()
                company_group = [chunk]
                used_indices.add(i)
                
                # Find chunks with similar company names
                for j in range(i + 1, len(section_chunks)):
                    if j in used_indices:
                        continue
                    
                    company2 = section_chunks[j]["metadata"].get("company", "").strip()

                    # Check company similarity (fuzzy + substring)
                    if self.fuzzy_match(company1, company2):
                        company_group.append(section_chunks[j])
                        used_indices.add(j)
                
                company_groups.append(company_group)
            
            # Step 2b: Within each company group, group by similar job titles
            for company_group in company_groups:
                if len(company_group) == 1:
                    # Single chunk in this company group
                    unsimilar.append(company_group[0])
                    continue
                
                # For Education section, group all chunks from same company together
                # since they're likely different degree variations
                if section_type == "Education":
                    similar.append(company_group)
                    continue
                
                # Group by job title similarity for non-Education sections
                job_used_indices = set()
                
                for i, chunk in enumerate(company_group):
                    if i in job_used_indices:
                        continue
                    
                    job_title1 = chunk["metadata"].get("job_title", "").strip()
                    if not job_title1:
                        unsimilar.append(chunk)
                        job_used_indices.add(i)
                        continue
                    
                    job_group = [chunk]
                    job_used_indices.add(i)
                    
                    # Find chunks with similar job titles
                    for j in range(i + 1, len(company_group)):
                        if j in job_used_indices:
                            continue
                        
                        job_title2 = company_group[j]["metadata"].get("job_title", "").strip()
                        if not job_title2:
                            continue
                        
                        # Check job title similarity (fuzzy + substring)
                        if self.fuzzy_match(job_title1, job_title2, threshold=0.80):
                            job_group.append(company_group[j])
                            job_used_indices.add(j)
                    
                    # Add to appropriate list
                    if len(job_group) > 1:
                        similar.append(job_group)
                    else:
                        unsimilar.append(job_group[0])
        
        return similar, unsimilar

    def filterChunks(self, combinedChunks):
        unnecessaryChunks = []
        naCompanyChunks = []
        validChunks = []
        
        for chunk in combinedChunks:
            sec = chunk["metadata"].get("section_type", "Other")
            sec_lower = str(sec).lower() if sec else ""
            
            # Filter 1: Check if section contains 'skills' or 'about'
            if "skills" in sec_lower or "about" in sec_lower:
                unnecessaryChunks.append(chunk)
                continue
            
            # Filter 2: Check if company is N/A or missing
            company = chunk["metadata"].get("company", "").strip()
            if not company or company.upper() == "N/A":
                naCompanyChunks.append(chunk)
                continue
            
            # Passed all filters - it's valid
            validChunks.append(chunk)

        # Process N/A company chunks
        naCompanyGrouped = {
            "similar": [],
            "unsimilar": []
        }
        section_groups = defaultdict(list)
        for chunk in naCompanyChunks:
            section_type = chunk["metadata"].get("section_type", "Other")
            section_groups[section_type].append(chunk)
        
        # Now within each section, group by job_title
        for section_type, chunks in section_groups.items():
            job_title_groups = defaultdict(list)
            
            for chunk in chunks:
                job_title = chunk["metadata"].get("job_title", "").strip()
                if job_title:
                    job_title_groups[job_title].append(chunk)
                else:
                    # No job title, goes directly to unsimilar
                    naCompanyGrouped["unsimilar"].append(chunk)
            
            # Check each job_title group
            for job_title, group in job_title_groups.items():
                if len(group) > 1:
                    # Multiple chunks with same section_type + job_title = similar
                    naCompanyGrouped["similar"].append(group)
                else:
                    # Only one chunk with this section_type + job_title = unsimilar
                    naCompanyGrouped["unsimilar"].append(group[0])
        
        # Process valid chunks
        validChunksGrouped = {
            "similar": [],
            "unsimilar": []
        }
        similar, unsimilar = self.filterSimilarChunks(validChunks)
        validChunksGrouped["similar"] = similar
        validChunksGrouped["unsimilar"] = unsimilar
        
        # Debug output
    
        return {
            "validChunks": validChunksGrouped,
            "naCompanyChunks": naCompanyGrouped,
            # "unnecessaryChunks": unnecessaryChunks
        }


    async def sortChunks(self, unsimilarChunks):
        self.logger.info(f"Starting LLM validation chunks {len(unsimilarChunks) }")
        sortingPrompt = ChatPromptTemplate.from_messages([
                ("system", 
                    """You are an expert at analyzing professional experience data to identify duplicates and similar entries.

        Your task is to carefully review a list of experience/project entries and determine which ones describe the SAME experience (just worded differently) versus which ones are TRULY UNIQUE experiences.

        **Criteria for considering entries as SIMILAR/DUPLICATES:**
        Two entries are duplicates ONLY if ALL of these conditions are true:
        1. Same company/organization name (accounting for minor variations in naming)
        2. Overlapping or identical date ranges
        3. Same or equivalent job title/role describing the same position
        4. Same or equivalent location
        5. Describing the same core responsibilities and accomplishments (even if worded differently)

        **Criteria for considering entries as UNIQUE:**
        Entries are UNIQUE if ANY of these conditions are true:
        - Different companies/organizations
        - Non-overlapping time periods
        - Different job titles or roles at the SAME company (multiple positions at one organization are separate experiences)
        - Different locations for the same company
        - Different projects or initiatives
        - Different sets of responsibilities and accomplishments

        **IMPORTANT DISTINCTIONS:**
        - Multiple distinct roles at the SAME organization = SEPARATE experiences (not duplicates)
        - Different positions held simultaneously or sequentially at same org = NOT duplicates
        - Leadership role vs individual contributor role at same org = different experiences
        - Different departments/teams at same company = typically different experiences

        **CRITICAL OUTPUT RULES:**
        1. A group in "similar" MUST contain EXACTLY 2 or more entries describing the IDENTICAL experience
        2. If an entry has NO duplicates, it MUST go in "unsimilar"
        3. NEVER create single-item groups in "similar"
        4. Be conservative - when uncertain whether two entries represent the same experience, treat them as unique
        5. Focus on whether entries describe the same position/role, not just the same organization

        Return your analysis in JSON format with "similar" and "unsimilar" keys."""
                ),
                ("user", """Please analyze the following list of experience entries and identify which ones are duplicates/similar (describing the same experience) versus which are truly unique.

        **Entries to analyze:**
        {entries_json}

        Carefully compare each entry. Remember:
        - Same organization + different roles/titles = UNIQUE entries (not duplicates)
        - Only group entries if they describe the EXACT SAME position/role with different wording
        - Multiple positions at one company should remain separate

        Return the result with:
        - "similar": List of lists, where each inner list contains 2+ entries describing the IDENTICAL experience/position
        - "unsimilar": List of entries that have no duplicates and are truly unique experiences

        Be conservative - if there's any doubt whether two entries represent the same position, treat them as unique.""")
            ])
        structured_llm = self.llm.with_structured_output(DeduplicationResult)
        chain = sortingPrompt | structured_llm
        
        result = chain.invoke({
            "entries_json": json.dumps(unsimilarChunks, indent=2, ensure_ascii=False)
        })

        sortedResponse = result.model_dump()
        self.logger.info(f"After LLM validation, {len(sortedResponse['similar'])} groups of similar chunks and {len(sortedResponse['unsimilar'])} unsimilar chunks remain.")
        return sortedResponse

    async def mergeChunks(self, similarChunks):
        deDuplicateSchema = PydanticOutputParser(pydantic_object=UnifiedSemanticChunks)
        deDuplicateSchemaInstructions = deDuplicateSchema.get_format_instructions()
        deDuplicatePrompt = ChatPromptTemplate.from_messages([
            ("system" , 
                """
                    You are a chunk consolidation assistant. 
                    - Your task is to merge groups of similar text chunks into one standardized chunk. 
                    - Each of the chunks you have merge are contained in list and these chunks that are about the same experience, skill, project or entity.
                    - Each group of similar chunks is seperated by lists.
                    Follow these rules strictly:

                        1. Combine the "embedding_text" values in each group summarizing it into a single coherent description.
                            - Preserve all essential details such as responsibilities, impact, metrics, tools, and outcomes.
                            - Eliminate redundancy but do not remove unique information.
                            - Keep the summary professional, third-person, and concise do not change the tone or format of how the text is written.
                            - Each summary should be between 100-250 words.
                            - Do not include bullet points or markdown.
                        2. Merge the "metadata" dictionaries in each group:
                            - "date_range": Use the most specific or precise date range available (prefer explicit months and years over broad ranges).
                            - "company": Use the most complete and standardized company name available. If multiple companies are present, list them all.
                            - "job_title": Use the most descriptive or senior-sounding title from the group.
                            - "location": Use the most detailed form of the location.
                            - "section_type": Keep consistent with the group (Experience, Education, Projects, Skills, etc).
                            - "chunk_id": Omit this field in the final output.
                        3. Do not invent new details — only merge and rephrase information present in the group.
                        4. Ensure the final output is valid JSON with the structure:
                        {format_instructions}
                        5. Do not include any extra commentary or text outside the JSON object.
            """
            ),
            ("user" ,"""
                Here are groups of chunks that were validated as similar:

                Groups:
                {similar_chunks_json}

            """)
        ])
        deDuplicateMessage = deDuplicatePrompt.format_messages(similar_chunks_json=similarChunks, format_instructions=deDuplicateSchemaInstructions)
        deDuplicateLLMResponse = self.llm.invoke(
            deDuplicateMessage)
        deDuplicateResponse = deDuplicateSchema.parse(deDuplicateLLMResponse.content)
        deDuplicateResponse = deDuplicateResponse.model_dump()
        self.logger.info(f"Merged into {len(deDuplicateResponse['chunks'])} unified chunks after de-duplication.")
        return deDuplicateResponse
    
    def DocsEmbedder(self, texts: list[str]):
        self.logger.info(f"Generating {len(texts)} document embeddings")

        result = self.embedder.embed(
            texts=texts,
            model="voyage-3.5",
            input_type="document",      # Use "document" for chunks
            output_dimension=1024,
            output_dtype="float"
        )
        
        # FIX: Use .embeddings (attribute) not ['embedding'] (dict key)
        embeddings = result.embeddings  # Changed from result['embedding']
        
        return embeddings

    async def generateEmbeddings(self, client, userEmail: str, userProfile: list) -> dict:
        try:
            self.logger.info(f"Starting to embed {len(userProfile)} chunks for {userEmail}")
            
            # Delete existing embeddings for this user (for updates)
            client.table('user_profile_embeddings')\
                .delete()\
                .eq('user_email', userEmail)\
                .execute()
            
            self.logger.info(f"Deleted existing embeddings for {userEmail}")
            
            # Extract all texts first for batch embedding
            texts = [chunk['embedding_text'] for chunk in userProfile]
            
            # Generate ALL embeddings at once (much faster!)
            self.logger.info(f"Generating {len(texts)} embeddings in batch...")
            all_embeddings = self.DocsEmbedder(texts)  
            
            # Verify dimension
            if all_embeddings and len(all_embeddings[0]) != 1024:
                raise ValueError(f"Expected 1024 dimensions but got {len(all_embeddings[0])}")
            
            # Combine embeddings with metadata
            embeddings_to_insert = []
            for i, chunk in enumerate(userProfile):
                embeddings_to_insert.append({
                    'user_email': userEmail,
                    'embedding_text': chunk['embedding_text'],
                    'embedding': all_embeddings[i],  # Use pre-generated embedding
                    'metadata': chunk['metadata']
                })
                self.logger.info(f"Prepared embedding {i+1}/{len(userProfile)}")
            
            # Batch insert all embeddings
            response = client.table('user_profile_embeddings')\
                .insert(embeddings_to_insert)\
                .execute()
            
            self.logger.info(f"Successfully stored {len(embeddings_to_insert)} embeddings for {userEmail}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error storing embeddings for {userEmail}: {e}", exc_info=True)
            raise

