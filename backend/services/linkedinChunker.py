from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from google import genai
import logging
import json
from .outputSchemas import LinkedInChunks, FilteredLinkedInProfile, SemanticChunks

class LinkedinChunker:
    def __init__(self, llmInstance):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = llmInstance
        self.linkedinChunkingPrompt = ChatPromptTemplate.from_messages([
    ("system", 
        """You are an expert LinkedIn profile parser that extracts structured information from raw text exports.

**Your Task:** Analyze the raw LinkedIn text to identify sections, deduplicate content, and organize information into a clean, structured format.

## Section Detection Strategy

**1. Identifying Section Headers:**
- Look for repeated words (e.g., "ExperienceExperience" → "Experience")
- Detect title-cased labels followed by content blocks
- Common sections include: About, Experience, Education, Projects, Volunteering, Skills, Certifications
- Headers appear BEFORE their content, never embedded within entries
- There should be no duplication of headers in final output

**2. Distinguishing Headers from Content:**
- NOT headers: company names, job titles, locations, dates, skill names, connection counts
- Headers are labels that organize content, not the content itself
- When uncertain, check if text is followed by multiple sub-entries (indicates header)

## Content Processing Rules

**3. Grouping Content:**
- Assign all text lines to the most recently detected section header
- Keep content together until the next valid header appears
- Each bullet point or description stays within its parent entry

**4. Deduplication:**
- Remove exact duplicate sentences that appear consecutively
- LinkedIn exports often repeat bullet points—merge them into single instances
- Preserve all unique information even if similar

**5. Entry Separation:**
- Within sections, separate distinct entries (different jobs, projects, etc.)
- Each entry should be ONE complete string containing all its details
- Use " | " (space-pipe-space) to separate distinct attributes within an entry
- Format: "Title | Organization | Date | Location | Description points"

**6. Text Cleanup:**
- Fix obvious line-break errors (e.g., "simulatio" → "simulation")  
- Preserve original dates, numbers, and proper nouns exactly
- Keep technical terms and acronyms unchanged
- Remove bullet point symbols (•, -, numbers) from the start of description lines
- Preserve all other punctuation and formatting
- Keep the content of each point, just remove the bullet marker


## Special Handling

**7. Profile Header:**
Extract these elements into profile_header (if present):
- Full name
- Pronouns
- Current role/headline
- Educational institution (current)
- Location
- Contact information (email, phone, LinkedIn URL)
Only include what explicitly appears at the profile's beginning.
Each element in profile headers should be comma separated.
**Exclude:** Connection counts, badges, "Contact info" labels, or other LinkedIn UI metadata.


**8. Skills Section:**
- If a "Skills" section exists, create a dedicated global Skills entry
- List all skills with their context if provided (e.g., "Python | Machine Learning Intern at Company")
- DO NOT duplicate skills within individual experience/project entries
- If no clear Skills section exists, omit it entirely

**9. Contact Information:**
- Only include if explicitly present in the profile
- Look for: email addresses, phone numbers, portfolio URLs, GitHub links
- Do NOT repurpose job locations or organizations as contact info
- If none found, omit the contact section

## Output Format

Return a JSON structure with:
- `profile_header`: List of strings with basic profile info
- `sections`: List of objects, each containing:
  - `sectionName`: Exact header name from profile (de-duplicated)
  - `entries`: List of complete entry strings

**Critical:** Use the EXACT section names from the source text. Do not standardize, translate, or rename them."""
    ),
    ("user", 
        """Parse this raw LinkedIn profile text into the structured format:

{linkedin_data}

**Remember:**
- Let the text structure guide you—no assumptions about what sections exist
- Deduplicate repeated content thoroughly  
- Clean up obvious text errors
- Separate distinct entries within each section
- Only include sections that actually appear in the profile"""
    )
])
        self.linkedinChunkingInstructions = self.llm.with_structured_output(LinkedInChunks,method="json_schema")

        self.sortingPrompt = ChatPromptTemplate.from_messages([
            ("system", 
                """
                You are a data curator specialized in extracting actionable professional experience from LinkedIn profiles. Your role is to organize sections by identifying which contain concrete accomplishments and which are derivative or summary content.

CLASSIFICATION PRINCIPLE:
A section is RELEVANT if it:
- Documents specific actions, achievements, or contributions the person took
- Describes roles, responsibilities, or outcomes at organizations/projects
- Provides evidence of skills applied in real contexts
- Shows collaboration, leadership, or problem-solving
- Contains measurable results or time-bound commitments

A section is AUXILIARY if it:
- Summarizes or abstracts information found elsewhere (e.g., "About" sections, skill lists)
- Is derivative of concrete experience entries (e.g., a "Skills" list extracted from jobs/projects)
- Serves as metadata or context rather than substance
- Lacks actionable detail or specific evidence

FILTERING STRATEGY:
1. Examine each section by its semantic purpose, not its name
2. Assess whether removing it would lose unique, concrete professional evidence
3. Prioritize sections where a person *does something* over sections that *describe them*
4. Retain only sections that will add value when semantically embedded and searched later

IMPORTANT: Do not modify, change, or alter any data. Only organize existing sections into the two categories
                """
            ),
            ("user", 
                """
Analyze the provided LinkedIn profile and separate its sections into two categories: RELEVANT and AUXILIARY.

Do NOT modify or change any data. Only organize the existing sections based on whether they contain concrete professional evidence or are derivative/summary content.

INPUT:
{linkedin_json}

Return the reorganized sections in JSON format only, no commentary.
                """
            )
        ])
        self.sortingInstructions = self.llm.with_structured_output(FilteredLinkedInProfile) 

        self.sematicChunkingPrompt = ChatPromptTemplate.from_messages([
            ("system",
                """
            Objective:            
                Create self-contained, keyword-rich paragraphs optimized for semantic similarity matching and Maximum Marginal Relevance (MMR) retrieval.

            Opening Line:
                Front-load key information: role, company, dates, location.
                Format concisely using separators like pipes or dashes.
                Aim for 10-20 words maximum.
            Body Content:
                Write detailed third-person narratives rich in technical terms, achievements, and context.
                Incorporate active voice for clear attribution.
                Cover all aspects mentioned, including technologies, methodologies, and metrics.
            Metadata Extraction:
                Extract structured fields: section_type, date_range, company, location, job_title.
                Format dates as “Month YYYY - Month YYYY” or “YYYY - Present”.
            Ensure semantic search optimization:
                Ensure most important keywords are front-loaded.
                Include relevant technical terms and metrics.
                Maintain clarity and coherence throughout the chunk.
                Validate metadata accuracy.
            """
            ),  ("user","""
The input data provided below should be processed into semantic chunks according to these instructions:
{linkedin_experience_data}

Return ONLY the JSON structure.

"""
                )
        ])
        self.semanticChunkInstructions = self.llm.with_structured_output(SemanticChunks,method="json_schema")
        self.logger.info("Linkedin Chunker initialized")
    

    def separateSections(self, original_data: dict, filtered_data: dict) -> dict:
            
        # Create lookup dictionaries from original data for easy comparison
        original_sections_map = {
            section['sectionName']: section 
            for section in original_data.get('sections', [])
        }
        
        # Initialize output structure
        result = {
            'relevant_sections': [],
            'auxiliary_sections': []
        }
        
        # ========== STEP 1: Process relevant_sections ==========
        for filtered_section in filtered_data.get('relevant_sections', []):
            section_name = filtered_section['sectionName']
            
            # Check if this section exists in original
            if section_name in original_sections_map:
                original_section = original_sections_map[section_name]
                
                # Compare entries: if they match, use filtered; if not, use original
                if filtered_section['entries'] == original_section['entries']:
                    result['relevant_sections'].append(filtered_section)
                else:
                    # Mismatch detected - use original to avoid data loss
                    result['relevant_sections'].append(original_section)
            else:
                # Section in filtered but not in original (shouldn't happen, but keep it)
                result['relevant_sections'].append(filtered_section)
        
        # ========== STEP 2: Process auxiliary_sections ==========
        for filtered_section in filtered_data.get('auxiliary_sections', []):
            section_name = filtered_section['sectionName']
            
            # Check if this section exists in original
            if section_name in original_sections_map:
                original_section = original_sections_map[section_name]
                
                # Compare entries: if they match, use filtered; if not, use original
                if filtered_section['entries'] == original_section['entries']:
                    result['auxiliary_sections'].append(filtered_section)
                else:
                    # Mismatch detected - use original to avoid data loss
                    result['auxiliary_sections'].append(original_section)
            else:
                # Section in filtered but not in original (could be profile_header)
                result['auxiliary_sections'].append(filtered_section)
        
        # ========== STEP 3: Ensure profile_header is in auxiliary ==========
        # Check if profile_header exists in original data
        if 'profile_header' in original_data and original_data['profile_header']:
            # Check if profile_header is already in auxiliary_sections
            profile_header_exists = any(
                section['sectionName'] == 'profile_header' 
                for section in result['auxiliary_sections']
            )
            
            if not profile_header_exists:
                # Add profile_header to auxiliary_sections
                result['auxiliary_sections'].insert(0, {
                    'sectionName': 'profile_header',
                    'entries': original_data['profile_header']
                })
        
        return result

    async def createLinkedinChunks(self, linkedinText: str):
        chunkingChain = self.linkedinChunkingPrompt | self.linkedinChunkingInstructions
        result = chunkingChain.invoke({"linkedin_data": linkedinText})
        linkedinChunksJSON = result.model_dump()
        self.logger.info("LinkedIn Chunks Created")

        # sortingChain = self.sortingPrompt | self.sortingInstructions
        # result = sortingChain.invoke({"linkedin_json": json.dumps(linkedinChunksJSON)})
        
        # with open("filteredLinkedInProfile.json", "w", encoding="utf-8") as f:
        #     json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)

        # filteredData = self.separateSections(linkedinChunksJSON, result.model_dump())
        # self.logger.info("LinkedIn Data Separated")
        
        semanticChain = self.sematicChunkingPrompt | self.semanticChunkInstructions
        result = semanticChain.invoke({"linkedin_experience_data": linkedinChunksJSON})
        linkedinSemanticChunksJSON = result.model_dump()

        chunkedData = {
            "chunks": linkedinChunksJSON,
            "semanticChunks": linkedinSemanticChunksJSON,
        }

        self.logger.info("LinkedIn Semantic Chunks Created")
        return chunkedData

    



    
    
