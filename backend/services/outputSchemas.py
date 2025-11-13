from typing import List, Dict, Any, TypedDict, Optional
from pydantic import BaseModel, Field

#Resume Chunker 
class ResumeSection(BaseModel):
    """A single resume section."""
    section_name: str = Field(description="The exact section name from the resume")
    entries: List[str] = Field(description="Complete entry strings for this section")

class ResumeChunks(BaseModel):
    """Structured resume sections."""
    contact: List[str] = Field(
        description="Raw contact values without labels"
    )
    sections: List[ResumeSection] = Field(
        description="List of resume sections"
    )

#Linkedin Chunker 
class ChunkMetadata(BaseModel):
    section_type: str = Field(description="The section name from the resume (e.g., 'Experience', 'Projects', 'Education', 'Technical Skills')")
    date_range: str = Field(description="Date range if present (e.g., 'May 2016 - September 2020'), otherwise 'N/A'")
    company: str = Field(description="Company/organization/university name if present, otherwise 'N/A'")
    location: str = Field(description="Location if present (e.g., 'Edmonton, AB'), otherwise 'N/A'")
    job_title: str = Field(description="Job title, degree, or project name if present, otherwise 'N/A'")

class SemanticChunk(BaseModel):
    embedding_text: str = Field(description="80-200 word third-person narrative paragraph optimized for semantic search, rich in keywords and context")
    metadata: ChunkMetadata

class SemanticChunks(BaseModel):
    chunks: List[SemanticChunk] = Field(description="List of all semantic chunks generated from the resume sections")


class LinkedInSection(BaseModel):
    sectionName: str = Field(description="The exact section name from the LinkedIn profile")
    entries: List[str] = Field(description="Complete entry strings for this section")

class LinkedInChunks(BaseModel):
    profile_header: List[str] = Field(
        description="Basic profile information including name, headline, location, and about section"
    )
    sections: List[LinkedInSection] = Field(
        description="List containing all the sections and their data from the LinkedIn profile"
    )


class FilteredLinkedInProfile(BaseModel):
    relevant_sections: List[LinkedInSection] = Field(
        description="Sections containing concrete professional evidence, accomplishments, and organizational involvement"
    )
    auxiliary_sections: List[LinkedInSection] = Field(
        description="Sections that are derivative or summary-level (e.g., About, Skills lists)"
    )

#Sorting Chunks
class ExperienceMetadata(BaseModel):
    """Metadata for an experience entry"""
    section_type: str = Field(description="Type of section (e.g., Experience, Projects, Volunteering)")
    date_range: str = Field(description="Date range of the experience")
    company: str = Field(description="Company or organization name")
    location: str = Field(description="Location of the experience")
    job_title: str = Field(description="Job title or role")

class ExperienceEntry(BaseModel):
    """A single experience entry with embedding text and metadata"""
    embedding_text: str = Field(description="The text description of the experience")
    metadata: ExperienceMetadata = Field(description="Structured metadata about the experience")

class DeduplicationResult(BaseModel):
    """Result of deduplication analysis"""
    similar: List[List[ExperienceEntry]] = Field(
        default=[],
        description="Groups of similar/duplicate entries. Each inner list contains 2+ entries that describe the same experience"
    )
    unsimilar: List[ExperienceEntry] = Field(
        default=[],
        description="Entries that are truly unique with no duplicates"
    )

#Merging Chunks
class UnifiedSemanticChunk(BaseModel):
    embedding_text: str = Field(
        description=(
            "Unified, deduplicated, and RAG-optimized semantic summary. "
            "Fluent, third-person, self-contained summary rich in keywords (100–250 words). "
            "Must consolidate all overlapping details from resume + LinkedIn. "
            "Include role, organization(s), timeframe, location(s), key actions, technologies, "
            "and impact. Avoid redundancy, bullet points, or markdown. "
            "Result should reflect the most detailed understanding of the user’s experience."
        )
    )
    metadata: Dict[str, Any] = Field(
        description=(
            "Merged structured metadata for filtering and context. "
            "Include: date_range (or multiple ranges if conflicting), "
            "company (string or list if multiple values, if applicable), "
            "section_type (Experience/Education/Project/etc. provided in existing metadata), "
            "location (string or list if multiple values, if applicable), "
            "job_title (string or list if multiple values, if applicable)."
        )
    )

class UnifiedSemanticChunks(BaseModel):
    chunks: List[UnifiedSemanticChunk] = Field(
        description="List of deduplicated, merged chunks ready for embedding and retrieval"
    )


#Response State
class JobApplicationState(TypedDict):
    # Initial inputs
    jobTitle: str
    companyName: str
    question: str
    email: str
    
    # Step outputs
    companyResearchDecision: bool
    collectedCompanyData: Optional[str]
    jobdescriptionData: str
    retrievedUserData: list[str]
    finalResponse: str

#Company Research Decision
class CompanyResearchDecision(BaseModel):
    """Output schema for the decision"""
    companyResearchDecision: bool = Field(
        description="True if company information is needed to answer the question"
    )

class SearchQuery(BaseModel):
    search_query: str

class OptimalQuery(BaseModel):
    optimized_query: str = Field(description="Rephrased and expanded query optimized for RAG retrieval")
    Keyadditions : List[str] = Field(description="List of key terms or phrases added to enhance retrieval effectiveness")

class ResponseOutput(BaseModel):
    """Generated response to interview question"""
    response: str = Field(
        description="Complete 3-sentence response (60-75 words)"
    )


