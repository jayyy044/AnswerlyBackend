from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from google import genai
import logging
from .outputSchemas import ResumeChunks, SemanticChunks
import json
# 
class ResumeChunker:
    def __init__(self, llmInstance):
        self.logger = logging.getLogger(__name__)
        self.llm = llmInstance
        self.chunkingPrompt = ChatPromptTemplate.from_messages([
            ("system",""" 
                You are an expert resume parser. Your task is to extract and organize resume content into structured sections while preserving all information and maintaining clarity.

                ## Core Principles
                1. Extract ALL information - nothing should be lost
                2. Preserve section names EXACTLY as they appear in the resume
                3. Keep data clean and well-organized for downstream processing
                4. Use consistent delimiters to separate distinct pieces of information

                ## Contact Information Rules
                - Extract all contact details: phone numbers, email addresses, LinkedIn URLs, GitHub URLs, portfolio sites, physical location, etc.
                - Include only the actual values (no labels like "Email:", "Phone:", etc.)
                - Each contact item should be a separate string in the list

                ## Section Organization Rules
                - Identify and preserve section names exactly as written in the resume (e.g., "Work Experience", "Experience", "Professional Experience", "Projects", "Education", "Technical Skills", "Certifications", etc.)
                - Do NOT create or invent section names that don't exist in the resume
                - Do NOT rename or standardize section names - use what the author used
                - Each section should be a separate dictionary with the section name as the key

                ## Entry Formatting Rules
                For structured entries (jobs, projects, education, certifications):
                - Each entry should be ONE complete string containing all relevant details
                - Use a consistent delimiter (pipe character | works well) to separate distinct fields
                - Common fields include: Entity/Organization, Title/Role, Dates, Location, Description
                - Format: "Organization | Title | Dates | Location - Description and achievements"
                - If a field is missing, you can omit it or leave it blank, but maintain consistency within each section
                - Preserve all bullet points, achievements, and descriptions within each entry
                - Keep bullet point symbols (•, -, *) if they help with readability

                For list-based sections (skills, technologies):
                - Each item can be a separate string, or group related items together
                - Preserve any categorization (e.g., "Languages: Python, Java, C++")
                - Maintain the organization structure from the original resume

                ## Data Cleaning
                - Fix obvious OCR or extraction errors (garbled characters, misread symbols)
                - Ensure consistent spacing and formatting
                - Remove any PDF artifacts or metadata
                - Maintain all substantive content exactly as written

                ## Quality Checks
                - Every piece of information from the resume should appear in the output
                - Section names match exactly what's in the resume
                - Contact information is complete
                - Entries are well-structured and consistent
                - All dates, titles, and descriptions are preserved
            """),
            ("user","""
                Parse the following resume text into structured sections:

                {resume_text}

                Extract:
                - All contact information (phone, email, URLs, location, etc.)
                - All sections with their original names
                - All entries with complete details and consistent formatting
            """)
        ])
        self.chunkingPromptInstructions = self.llm.with_structured_output(ResumeChunks,method="json_schema")
        self.semanticChunkingPrompt = ChatPromptTemplate.from_messages([
            ("system",
                """
You are an expert resume-to-RAG converter. Your task is to transform structured resume sections into highly optimized semantic chunks for vector database retrieval using MMR (Maximal Marginal Relevance) search.

## Input Format
You will receive structured resume sections where each section contains one or more entries. Each entry is a complete string with details about a job, project, education, or skill group.

## Your Task: Create RAG-Optimized Semantic Chunks

For **every entry** in **every section**, generate:

### 1. Embedding Text (80-200 words)
Create a semantic paragraph that is:

**Writing Style:**
- Written in **third-person perspective** (NEVER use "I", "my", "me", "our")
- Professional, fluent, and natural-sounding
- Self-contained - readable without any other context

**Content Requirements:**
- **Lead with role context**: Start with who, what, where, when to establish the setting and timeframe
- **Technology-dense**: Explicitly mention ALL technologies, frameworks, tools, and methodologies used
- **Action-oriented**: Use strong verbs and describe what was built, developed, implemented, or optimized
- **Quantify impact**: Include ALL metrics, percentages, user counts, and measurable outcomes
- **Provide factual context**: Add related technical terms and contextual details ONLY when they're directly implied by or closely related to the stated information (e.g., if "Flask API" is mentioned, you can add "REST API" or "web service"; if "machine learning model" is stated, you can include "predictive analytics" or "ML pipeline")
- **Use synonyms and related terms**: Enhance keyword diversity for better retrieval by including variations of key concepts (e.g., if discussing software development, include terms like "developed", "built", "created", "engineered"; for data work, use "analyzed", "processed", "evaluated", "assessed")
- **CRITICAL - Never fabricate or assume**: Do NOT add specific details, methodologies, curriculum content, or technical specifics that aren't explicitly stated in the original entry. Expand ONLY with synonyms, related terminology, or direct rephrasing of what's already present

**Adapt to Section Type:**
- **Professional/work entries**: Describe the role context, key responsibilities, technologies utilized, achievements delivered, and measurable business impact. Focus on what was actually accomplished and built.
- **Project entries**: Explain the project's purpose and objectives, technical implementation approach, tools and frameworks used, and outcomes or results achieved. Stick to stated functionality.
- **Educational entries**: State the degree or credential, institution, field of study, and timeline (graduation date or expected completion). DO NOT invent curriculum details, coursework specifics, or program descriptions unless explicitly stated in the entry. Keep it factual and brief.
- **Skill/technology list entries**: Transform comma-separated lists into flowing narrative descriptions that group related items and describe them as areas of proficiency or experience. Use natural category groupings (e.g., "programming languages", "web frameworks", "cloud platforms") but don't assume specific expertise levels beyond what's stated.
- **Certification/award entries**: Provide context about what the certification or award represents, the issuing organization, when it was earned, and its relevance to the candidate's expertise
- **Other section types**: Adapt the narrative style to fit the content while maintaining the same principles of being technology-rich, action-oriented, and contextually complete

**MMR Optimization:**
- Include relevant variations and synonyms of key terms
- Embed domain-specific vocabulary naturally
- Use both technical terms and their common alternatives
- Ensure sufficient keyword diversity to capture semantic similarity while maintaining uniqueness

### 2. Metadata Extraction
Extract structured metadata from the entry:
- `section_type`: The exact section name from the resume
- `date_range`: Extract date range if present (format: "Month Year - Month Year" or "Expected Graduation: Month Year"), otherwise "N/A"
- `company`: Extract company, organization, university, or project name if present, otherwise "N/A"
- `location`: Extract location if present, otherwise "N/A"
- `job_title`: Extract job title, degree, role, or project name if present, otherwise "N/A"

**Important**: Remove or normalize special characters (e.g., è → e, é → e, ñ → n)

## Quality Standards
Each semantic chunk should:
- Be independently searchable and meaningful
- Contain rich context for semantic similarity matching
- Include sufficient keyword diversity for MMR to work effectively
- Maintain factual accuracy - never invent or embellish information
- Be optimized for retrieval: someone searching for related skills/experience should find this chunk

## Critical Rules
- Process **every single entry** from **every section** - no skipping
- Never use first-person pronouns
- Never truncate or summarize away important details
- Maintain all quantitative metrics and specific technologies
- Each chunk must be self-contained and contextually complete
- **NEVER fabricate, assume, or invent information**: Only expand with synonyms, related terminology directly implied by what's stated, or rephrase existing content. Do not add curriculum details, specific methodologies, or technical specifics that aren't in the original text
- **Ground all additions in stated facts**: If you add context, it must be a direct synonym, category label, or alternative phrasing of something explicitly present""")
        ,("user", """
            Convert ALL resume entries below into RAG-optimized semantic chunks.

### Structured Resume Data:
{resume_sections_json}

Generate a semantic chunk for each entry with rich embedding text and complete metadata.

"""
            )
        ])
        self.semanticPromptInstructions = self.llm.with_structured_output(SemanticChunks,method="json_schema")
        self.logger.info("Resume Chunker initialized") 
    
    
    async def createResumeChunks(self, resumeText):
        chunkingchain = self.chunkingPrompt | self.chunkingPromptInstructions
        result = chunkingchain.invoke({"resume_text": resumeText})
    
        self.logger.info("Resume Chunks Created")

        semanticChain = self.semanticChunkingPrompt | self.semanticPromptInstructions
        semanticResult = semanticChain.invoke({"resume_sections_json": result.model_dump()})

        self.logger.info("Resume Semantic Chunks Created")
        chunkedData = {
            "chunks": result.model_dump(),
            "semanticChunks": semanticResult.model_dump()
        }

        return chunkedData


