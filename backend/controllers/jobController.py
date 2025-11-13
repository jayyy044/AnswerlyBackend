from services.dependencies import getLLM, getSupabaseClient, getEmbeddingConfig, getTavilyClient, queryEmbedder
from fastapi.responses import JSONResponse
import requests.exceptions
import logging
from services.outputSchemas import JobApplicationState, CompanyResearchDecision, SearchQuery, OptimalQuery, ResponseOutput
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

async def createFinalResponse(state: JobApplicationState, model) -> JobApplicationState:
    prompt = None
    if state["companyResearchDecision"]:
        prompt = ChatPromptTemplate.from_messages([
    ("system",
        """
        Write 3 sentences (60-75 words) explaining why they're interested in this company/role.
        
        Sentence 1: One specific thing they learned from their work
        Sentence 2: How the company's specific product/feature reflects that
        Sentence 3: What aspect of the work interests them
        
        Banned words: your, you're, eager, passionate, excited, innovative, cutting-edge, resonates, aligns, opportunity, impactful, solutions, benefit
        
        Keep it conversational. Reference actual product names. Focus on the work, not career growth.
        Under 75 words.
        """
    ),            
    ("user",
        """
        Question: {question}
        Company: {company_data}
        Background: {user_data}
        Job: {job_title}
        
        Write 3 short sentences (60-75 words). Conversational tone. Specific products. No banned words.
        """
    )
])
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
                """
                   You are a career coach helping candidates sound authentic in interviews. Your job is to help them connect their genuine interests and past work to a role they're excited about—without sounding rehearsed or like they're reading from a resume.

                    ## Your Approach:
                    This is about showing the hiring manager: "Here's who I am, here's what I've learned matters to me, here's why this specific role excites me."

                    ## The Response (3-4 sentences):
                    This should feel like a natural answer—it reads like they're explaining their thinking to a colleague, not pitching themselves.

                    ### Structure Pattern:
                    ✅ "I realized through [type of work] that I really enjoy [what they discovered]. This role's focus on [specific responsibility from job description] appeals to me for exactly that reason. I'm drawn to the opportunity to [concrete thing they'd do], and I'm particularly interested in learning how [aspect of role or company approach] works."

                    ✅ "What I've learned matters to me is [genuine insight from their background]. When I looked at this role, I saw that [specific job responsibility] is a core part of the work, which aligns perfectly with where I want to take my career. I want to keep building [type of work], especially in environments where [what appeals to them about the role or company]."

                    ### What NOT to do:
                    ❌ "I have skills in X, Y, and Z. I've done projects with A and B. I think I'd be a good fit." (Just listing skills and tech)

                    ❌ "I'm passionate about software engineering and excited about this opportunity." (Generic, says nothing real)

                    ❌ List specific metrics or achievements - only mention them if they explain why the role matters to them

                    ## Critical Rules:
                    1. **Tell the story behind the interest** - Why do they actually want this role, not just what they can do
                    2. **Use ONE concrete example from their work** - Make it real and specific, grounded in actual experience
                    3. **Connect it naturally to the job** - Don't force the connection, let it flow logically
                    4. **Avoid listing technologies or achievements** - Mention them only if they explain why the role matters
                    5. **Sound like yourself** - Conversational, genuine, natural pacing
                    6. **Focus on what excites them about THIS role** - Not the company, but the actual work they'd do
                    7. **Express authentic curiosity or growth interest** - What do they want to learn? What problem appeals to them?
                    8. **Never sound rehearsed** - Write like they're explaining their thinking, not delivering a speech
                    9. **Show thoughtfulness about the job itself** - Demonstrate you understand what the role actually involves
                """
            ),
            ("user", 
                """

                    Here's the context:

                    ## Question:
                    {question}

                    ## Job Title & Description:
                    {job_title}
                    {job_description}

                    ## Their relevant background (resume + LinkedIn):
                    {user_data}

                    ---

                    ## Your task:
                    Craft 3-4 sentences that sound like a genuine explanation of why this role appeals to them.

                    ### Think through this BEFORE writing:
                    1. What's ONE responsibility or aspect of this role that genuinely fits their interests or strengths?
                    2. What's ONE real experience from their background that shows why that matters to them?
                    3. How do those naturally connect?
                    4. What do they want to learn or explore in this role?

                    ### Then write (in this order):
                    - Sentence 1: Start with what they've discovered matters to them from their background
                    - Sentence 2: Connect that to a specific responsibility from the job description
                    - Sentence 3: Explain why that combination excites them
                    - Sentence 4 (optional): End with what they hope to learn or contribute
                    - Keep it conversational throughout—like explaining their thinking

                    Remember: They're explaining their thinking to someone, not selling themselves. Focus on why the role matters to them, not why they're perfect for it.
                """
            )
        ])
    
    structured_model = model.with_structured_output(ResponseOutput)

    if state["companyResearchDecision"]:
        result = structured_model.invoke(prompt.invoke({
            "question": state["question"],
            "job_title": state["jobTitle"],
            "job_description": state["jobdescriptionData"],
            "company_data": state["collectedCompanyData"] or "No company data available.",
            "user_data": state["retrievedUserData"] or "No user data available."
        }))
    else:
        result = structured_model.invoke(prompt.invoke({
            "question": state["question"],
            "job_title": state["jobTitle"],
            "job_description": state["jobDescription"],
            "user_data": state["retrievedUserData"] or "No user data available."
        }))
    state["finalResponse"] = result.response
    logger.info(f"Final Response:{result.response}")
    return 


async def searchUserProfile(queryEmbeddings: list, email: str, client, state, match_count: int = 4):
    try:
        logger.info(f"Searching embeddings for {email} with MMR")
        
        # Call the Supabase RPC function
        response = client.rpc(
            'search_user_profiles_mmr',
            {
                'query_embedding': queryEmbeddings,  # Your 1024-dim vector
                'filter_user_email': email,      # User email
                'match_count': match_count,           # How many results (k)
                'fetch_count': 15,                    # Initial candidates (fetch_k)
                'lambda_mult': 0.8,                   # Diversity vs relevance
                'match_threshold': 0.45                # Minimum similarity threshold
            }
        ).execute()
        
        logger.info(f"Found {len(response.data)} matching chunks")
        for res in response.data:
            state["retrievedUserData"].append(res['embedding_text'])
        return 
        
    except Exception as e:
        logger.error(f"Error searching embeddings: {e}", exc_info=True)
        raise

async def queryoptimizer(query: str, model) -> str:
    structuredModel = model.with_structured_output(OptimalQuery)
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
            """

                You are a **Query Optimization Specialist** in a Retrieval-Augmented Generation (RAG) system.

                Purpose in the Pipeline:
                - Your optimized query will be used to search a **LinkedIn+Resume profile dataset** (structured resume-style chunks including work experience, projects, education, skills, and achievements etc.).
                - The retriever uses your optimized query to fetch the most relevant profile documents.
                - These documents will then be passed to another LLM, which answers the user’s question.
                - Therefore: your job is not to answer the user, but to create the best possible **search query** for the data.

                Core Responsibilities:
                - Always interpret queries in the context of **personal/professional history** (roles, projects, internships, education, skills, certifications, achievements).
                - Expand vague terms like "experience" into retrievable resume-related concepts (roles, projects, internships, responsibilities, achievements, skills).
                - Rephrase, expand, and clarify the query without changing the fundamental meaning.
                - Add synonyms and variations likely to appear in LinkedIn profile text (e.g., “job”, “role”, “responsibilities”, “accomplishments”).
                - Incorporate temporal cues like “most recent”, “latest”, “current” when relevant to timelines.
                - Decompose multi-part queries into clearer sub-queries if needed.
                - Remove filler, politeness, and irrelevant words.

                Ambiguity Handling:
                - If the query is vague but still has **enough retrievable meaning**, assume the most likely **resume/LinkedIn interpretation**.
                - Do **not** default to general industry trends, methods, or research papers unless explicitly stated by the user (e.g., “industry trends”, “state of the art”).

                Important Guardrails:
                - Do **not** answer the query.
                - Do **not** add novel facts or make up experiences.
                - Preserve the user’s intent exactly while improving clarity and retrievability.
                - Match the phrasing and terminology likely used in LinkedIn documents.
                - Maintain neutrality and avoid injecting opinion or bias.

                Output Requirements:
                - Always return in the specified structured format

            """
        ),
        ("user", 
            """
                User Query: {user_query}
                Rules:  
                - Identify the core information need.  
                - Expand ambiguous terms into LinkedIn/resume-related concepts (roles, skills, projects, achievements, education).  
                - Add synonyms and related terminology for resume phrasing.  
                - Rephrase into an optimized search query suitable for semantic retrieval over LinkedIn + Resume data.  

                Final Output Format (must follow exactly): 
            """
        )
    ])
    response = structuredModel.invoke(prompt.invoke({
        "user_query": query,
    }))
    logger.info(f"Optimized Query: {response.optimized_query}")

    return response.optimized_query

async def companyResearch(state: JobApplicationState, tavily, model) -> JobApplicationState:
    prompt = ChatPromptTemplate.from_messages([
    ("system","""
        You are an expert at crafting search queries that retrieve rich, specific company information.
        
        Your goal: Generate ONE search query that will return substantive, recent information about what a company is actually doing—NOT generic company descriptions or careers pages.
        
        ## What Makes a Good Search Query:
        
        **Include these elements:**
        1. Company name (exact)
        2. 2-3 specific focus areas from the job description
        3. Time indicator ("2024" or "recent") to get fresh information
        4. Action-oriented terms that surface real initiatives
        
        **Search for substance, not fluff:**
        - Product launches, feature updates, or service expansions
        - Strategic initiatives, new programs, or business directions
        - Specific projects, partnerships, or organizational changes
        - Technical directions, methodologies, or approaches (if relevant)
        - Market positioning, customer focus, or business model
        
        **Prioritize specificity:**
        - Extract concrete nouns from job description: product names, technologies, methodologies, business areas
        - Use terms that appear in press releases, blog posts, and company announcements
        - Include industry-specific language that professionals in that field would use
        
        ## Query Construction Strategy:
        
        **Pattern:** [Company] + [Specific Focus Areas] + [Action/Update Terms] + [Time]
         **Examples across industries:**
        
        Tech company, engineering role:
        Job mentions: "machine learning models, recommendation systems"
        Query: "Netflix recommendation algorithms ML features 2024"
        
        Retail company, marketing role:
        Job mentions: "omnichannel customer experience, brand campaigns"
        Query: "Target omnichannel strategy brand campaigns customer experience 2024"
        
        Finance company, analyst role:
        Job mentions: "risk modeling, regulatory compliance"
        Query: "JPMorgan risk modeling compliance initiatives recent updates"
        
        Healthcare company, operations role:
        Job mentions: "patient care workflows, EHR systems"
        Query: "Kaiser patient care EHR workflow improvements 2024"
        
        Consulting firm, strategy role:
        Job mentions: "digital transformation, client solutions"
        Query: "McKinsey digital transformation solutions client approach recent"
        
        E-commerce company, product role:
        Job mentions: "checkout experience, payment processing"
        Query: "Shopify checkout payment infrastructure updates 2024"
        
        ## What to AVOID:
        
        ❌ Generic terms that return careers/HR pages:
        - "culture", "values", "mission", "working at", "careers", "jobs"
        - "overview", "about us", "company profile"
        - "internship", "hiring", "team", "employees"
        
        ❌ Terms too vague to be useful:
        - "innovative", "leading", "top", "best"
        - Just the company name alone
        - Just the job title
        
        ❌ Geographic specifics unless critical:
        - "Canada office", "Toronto location" (unless role is region-specific)
        
        ✅ Terms that surface real content:
        - Product/service names
        - Technologies, methodologies, frameworks
        - Business functions (not culture)
        - Strategic directions
        - Industry-specific terminology
        
        ## Query Length:
        - Aim for 6-10 words
        - Balance between specific enough to be useful and broad enough to return results
        - Include "2024", "recent", or "new" to get fresh information
        
        ## Quality Check:
        Before finalizing, ask:
        - Would this query return a press release, blog post, or product page? ✅
        - Would this query return a careers/jobs page? ❌
        - Does this include specific terms from the job description? ✅
        - Could this query work for 10 different companies? ❌
        
        Return ONLY the search query string, nothing else.
        
        """
        
        ),
        ("user",
            """
               Generate a single, focused search query to find specific, recent information about this company.
        
        Company Name: {company_name}
        
        Job Title: {job_title}
        
        Job Description: {job_description}
        
        ---
        
        Instructions:
        1. Identify 2-3 most important focus areas from the job description (products, technologies, business areas, methodologies)
        2. Construct query: [Company] + [Focus Areas] + time indicator
        3. Ensure query will return substantive content, not careers pages
        4. Keep to 6-10 words
        
        Return only the search query string.
            """
        )
    ])
    structuredModel = model.with_structured_output(SearchQuery)
    queryResult = structuredModel.invoke(prompt.invoke({
        "company_name": state["companyName"],
        "job_title": state["jobTitle"],
        "job_description": state["jobdescriptionData"],
    }))
    logger.info(f"Generated Search Query: {queryResult.search_query}")
    logger.info(f"Research required for {state['companyName']} — running Tavily search...")


    # ONE API CALL - Tavily handles the rest
    results = tavily.invoke(queryResult.search_query)
    state["collectedCompanyData"] = results.get("answer", str(results))
    return 

async def companyResearchDecision(state: JobApplicationState, model) -> JobApplicationState:

    prompt = ChatPromptTemplate.from_messages([
        ("system", 
            """
                You are an expert at analyzing job application questions.

                Determine if company-specific information (mission, values, culture, products, news, recent initiatives) 
                is needed to answer this question effectively.

                **Guidelines:**
                - Questions like "Why do you want to work here?", "What interests you about our company?", 
                "How do you align with our values?" ALWAYS need company research
                - Questions about the company's products, culture, or recent news need research
                - Questions about past experiences, technical skills, or hypothetical scenarios 
                usually DON'T need company info
                - Questions about "this role" might need company context if they ask about 
                contributing to company goals

                Be conservative: if company info would significantly improve the answer, mark as needed.
            """
        ),
        ("user", 
            """
                **Open-Ended Question:**
                {question}
                Does answering this question require researching company information?
            """
        )
    ])

    structured_model = model.with_structured_output(CompanyResearchDecision)
    result = structured_model.invoke(prompt.invoke({
        "question": state["question"],
    }))
    logger.info(f"Company Research Decision: {result.companyResearchDecision}")
    state["companyResearchDecision"] = result.companyResearchDecision
    
    return

async def convertJobDatatoQuery( state, model) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
            """
            You are a **Query Optimization Specialist** in a Retrieval-Augmented Generation (RAG) system.

            Purpose in the Pipeline:
            - Your optimized query will be used to search a **LinkedIn+Resume profile dataset** (structured resume-style chunks including work experience, projects, education, skills, and achievements).
            - The retriever uses your optimized query to fetch the most relevant profile documents that match the job requirements.
            - These documents will then be passed to another LLM, which determines if the candidate is qualified for the job.
            - Therefore: your job is not to evaluate the candidate, but to create the best possible **search query** to find relevant experiences in their profile.

            Core Responsibilities:
            - Analyze the job description and extract the most important qualifications, skills, and experiences required.
            - Transform these requirements into a search query that will match against **personal/professional history** (roles, projects, responsibilities, achievements, skills, certifications, education).
            - Expand technical acronyms and abbreviations (e.g., "ML" → "Machine Learning", "CI/CD" → "continuous integration continuous deployment").
            - Include both specific technical terms AND broader role-related concepts (e.g., "React developer" → "React JavaScript frontend development web applications").
            - Add synonyms and variations likely to appear in LinkedIn/Resume text (e.g., "built", "developed", "implemented", "created").
            - Capture implicit requirements from the job level (e.g., "Senior" → include leadership, mentoring, architecture).

            Query Construction Guidelines:
            - Create a natural language query (20-60 words) that combines:
            * Technical skills and tools mentioned in the job
            * Key responsibilities and job functions
            * Domain expertise and industry context
            * Experience level indicators (junior/mid/senior/lead)
            - Use phrasing that mirrors how people write about their experience in resumes
            - Prioritize high-signal terms that differentiate qualified candidates
            - Remove generic requirements that don't help retrieval (e.g., "good communication", "team player")

            Important Guardrails:
            - Do **not** answer questions about the job
            - Do **not** make up experiences or add information not in the job description
            - Focus solely on creating an optimized search query
            - Preserve the job's actual requirements while optimizing for retrieval

            What to Avoid:
            - Generic soft skills ("team player", "good communication", "fast learner")
            - Common filler words that don't add semantic value
            - Company-specific jargon or internal role names
            - Extremely niche terms that may be described differently
            - Redundant or overlapping phrases

            Output Requirements:
            - Always return in the specified structured format
            """
        ),
        ("user", 
            """
            Job Title: {job_title}
            
            Job Description: {job_description}
            
            Rules:  
            - Identify the core skills, technologies, and experiences required for this role
            - Extract key responsibilities and job functions
            - Determine the experience level and implied qualifications
            - Transform these into an optimized search query that will retrieve relevant experiences from a LinkedIn/Resume database
            - Include technical terms, action verbs, and domain-specific language that would appear in matching profile sections
            - Expand abbreviations and add related terminology for broader matching
            """
        )
    ])
    structured_model = model.with_structured_output(OptimalQuery)
    result = structured_model.invoke(prompt.invoke({
        "job_title": state["jobTitle"],
        "job_description": state["jobdescriptionData"],
    }))
    logger.info(f"Converted Job Description to Search Query: {result.optimized_query}")
    return result.optimized_query

async def generateAnswer(data):
    state: JobApplicationState = {
        "jobTitle": data.get("jobTitle"),
        "companyName": data.get("companyName"),
        "question": data.get("question"),
        "email": data.get("email"),
        "collectedCompanyData": "",
        "jobdescriptionData": data.get("jobDescription"),
        "companyResearchDecision": False,
        "retrievedUserData": [],
        "finalResponse": ""
    }

    if not all([state["email"], state["jobTitle"], state["companyName"], state["question"], state["jobdescriptionData"]]):
        logger.error("Missing required field")
        return JSONResponse(
            content={"error": "Missing required field(s)"},
            status_code=400
        )

    try:
        llm = getLLM(state["email"])
        tavily = getTavilyClient(state["email"])
        supabase = getSupabaseClient()
        embeddingConfig = getEmbeddingConfig()
        # Step 1: Determine if company research is needed
        await companyResearchDecision(state, llm)
        print(state)
        searchQuery = ""
        if state["companyResearchDecision"]:
            await companyResearch(state, tavily, llm)
            searchQuery = await convertJobDatatoQuery(state, llm)
        else:
            searchQuery = await queryoptimizer(state["question"], llm)

        searchQueryEmbedding = await queryEmbedder(searchQuery, embeddingConfig)
        await searchUserProfile(
            searchQueryEmbedding,
            state["email"],  # or wherever you get the email
            supabase,
            state,
            4  
        )
        logger.info(state["retrievedUserData"])
        logger.info(state["collectedCompanyData"])
        await createFinalResponse(state, llm)

        return JSONResponse(
            content={
                "message": "Answer generation pipeline executed successfully.",
                "finalResponse": state["finalResponse"]}, 
            status_code=200)
    except Exception as e:
        logger.error(f"Unexpected error during answer generation: {e}", exc_info=True)
        return JSONResponse(
            content={
                "error": "An unexpected error occurred while processing your request.",
            },
            status_code=500
        )






