import google.generativeai as genai
from typing import Dict, Any, Union, List
import os
import logging
from ..classes import ResearchState
import asyncio

logger = logging.getLogger(__name__)

class Briefing:
    """Creates briefings for each research category and updates the ResearchState."""
    
    def __init__(self) -> None:
        self.max_doc_length = 8000  # Maximum document content length
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        # Configure Gemini
        genai.configure(api_key=self.gemini_key)
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')

    async def generate_category_briefing(
        self, docs: Union[Dict[str, Any], List[Dict[str, Any]]], 
        category: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        company = context.get('company', 'Unknown')
        industry = context.get('industry', 'Unknown')
        hq_location = context.get('hq_location', 'Unknown')
        logger.info(f"Generating {category} briefing for {company} using {len(docs)} documents")

        # Send category start status
        if websocket_manager := context.get('websocket_manager'):
            if job_id := context.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="briefing_start",
                    message=f"Generating {category} briefing",
                    result={
                        "step": "Briefing",
                        "category": category,
                        "total_docs": len(docs)
                    }
                )

        prompts = {
            'company': f"""Create a focused company briefing for {company}, a {industry} company based in {hq_location}.
Key requirements:
1. Start with: "{company} is a [what] that [does what] for [whom]"
2. Structure using these exact headers and bullet points:

### Core Product/Service
* List distinct products/features
* Include only verified technical capabilities

### Leadership Team
* List key leadership team members
* Include their roles and expertise

### Target Market
* List specific target audiences
* List verified use cases
* List confirmed customers/partners

### Key Differentiators
* List unique features
* List proven advantages

### Business Model
* Discuss product / service pricing
* List distribution channels

3. Each bullet must be a single, complete fact
4. Never mention "no information found" or "no data available"
5. No paragraphs, only bullet points
6. Provide only the briefing. No explanations or commentary.""",

            'industry': f"""Create a focused industry briefing for {company}, a {industry} company based in {hq_location}.
Key requirements:
1. Structure using these exact headers and bullet points:

### Market Overview
* State {company}'s exact market segment
* List market size with year
* List growth rate with year range

### Direct Competition
* List named direct competitors
* List specific competing products
* List market positions

### Competitive Advantages
• List unique technical features
• List proven advantages

### Market Challenges
• List specific verified challenges

2. Each bullet must be a single, complete news event.
3. No paragraphs, only bullet points
4. Never mention "no information found" or "no data available"
5. Provide only the briefing. No explanation.""",

            'financial': f"""Create a focused financial briefing for {company}, a {industry} company based in {hq_location}.
Key requirements:
1. Structure using these headers and bullet points:

### Funding & Investment
* Total funding amount with date
* List each funding round with date
* List named investors

### Revenue Model
* Discuss product / service pricing if applicable

2. Include specific numbers when possible
3. No paragraphs, only bullet points
4. Never mention "no information found" or "no data available"
5. NEVER repeat the same round of funding multiple times. ALWAYS assume that multiple funding rounds in the same month are the same round.
6. NEVER include a range of funding amounts. Use your best judgement to determine the exact amount based on the information provided.
6. Provide only the briefing. No explanation or commentary.""",

            'news': f"""Create a focused news briefing for {company}, a {industry} company based in {hq_location}.
Key requirements:
1. Structure into these categories using bullet points:

### Major Announcements
* Product / service launches
* New initiatives

### Partnerships
* Integrations
* Collaborations

### Recognition
* Awards
* Press coverage

2. Sort newest to oldest
3. One event per bullet point
4. Do not mention "no information found" or "no data available"
5. Never use ### headers, only bullet points
6. Provide only the briefing. Do not provide explanations or commentary.""",

            'partners': f"""Create a comprehensive partnership briefing for {company}, a {industry} company based in {hq_location}.

Key requirements:
1. Structure using these exact headers and bullet points:

### Key Strategic Partnerships
* Detail each major strategic partnership
* Explain the nature of collaboration and integration
* Describe specific joint initiatives or products
* Note the business value or outcomes of each partnership

### Technical Integrations
* List important technical integrations or API connections
* Explain how these integrations function
* Describe the customer benefits from these integrations
* Include any metrics about integration success

### Distribution and Sales Alliances
* Detail major distribution or reseller partnerships
* Explain how these partnerships extend market reach
* Note any exclusive or preferred partner arrangements
* Include information about joint go-to-market strategies

2. Each bullet must provide specific details about HOW the partnerships work
3. Include only factual information from the research
4. Focus on quality of information rather than quantity of bullets
5. Provide only the briefing with bullet points. No explanations or commentary.
""",
        }
        
        # Normalize docs to a list of (url, doc) tuples
        items = list(docs.items()) if isinstance(docs, dict) else [
            (doc.get('url', f'doc_{i}'), doc) for i, doc in enumerate(docs)
        ]

        # Use a safer sorting approach
        sorted_items = []
        for url, doc in items:
            score = 0
            if isinstance(doc, dict) and 'evaluation' in doc:
                if isinstance(doc['evaluation'], dict) and 'overall_score' in doc['evaluation']:
                    try:
                        score = float(doc['evaluation']['overall_score'])
                    except (ValueError, TypeError):
                        score = 0
            sorted_items.append((url, doc, score))

        # Sort by the extracted score
        sorted_items.sort(key=lambda x: x[2], reverse=True)

        # Convert back to the format expected by subsequent code
        sorted_items = [(url, doc) for url, doc, _ in sorted_items]
        
        doc_texts = []
        total_length = 0
        for _ , doc in sorted_items:
            title = doc.get('title', '')
            content = doc.get('raw_content') or doc.get('content', '')
            if len(content) > self.max_doc_length:
                content = content[:self.max_doc_length] + "... [content truncated]"
            doc_entry = f"Title: {title}\n\nContent: {content}"
            if total_length + len(doc_entry) < 120000:  # Keep under limit
                doc_texts.append(doc_entry)
                total_length += len(doc_entry)
            else:
                break
        
        separator = "\n" + "-" * 40 + "\n"
        prompt = f"""{prompts.get(category, 'Create a focused, informative and insightful research briefing on the company: {company} in the {industry} industry based on the provided documents.')}

Analyze the following documents and extract key information. Provide only the briefing, no explanations or commentary:

{separator}{separator.join(doc_texts)}{separator}

"""
        
        try:
            logger.info("Sending prompt to LLM")
            response = self.gemini_model.generate_content(prompt)
            content = response.text.strip()
            if not content:
                logger.error(f"Empty response from LLM for {category} briefing")
                return {'content': ''}

            # Send completion status
            if websocket_manager := context.get('websocket_manager'):
                if job_id := context.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="briefing_complete",
                        message=f"Completed {category} briefing",
                        result={
                            "step": "Briefing",
                            "category": category
                        }
                    )

            return {'content': content}
        except Exception as e:
            logger.error(f"Error generating {category} briefing: {e}")
            return {'content': ''}

    async def process_briefing(self, docs: Union[Dict[str, Any], List[Dict[str, Any]]], 
                               category: str, context: Dict[str, Any], state: ResearchState) -> Dict[str, str]:
        """Process a single category briefing."""
        # Add websocket_manager and job_id to context if they exist in state
        if websocket_manager := state.get('websocket_manager'):
            context['websocket_manager'] = websocket_manager
        if job_id := state.get('job_id'):
            context['job_id'] = job_id
        
        try:
            # Generate the briefing for this category
            result = await self.generate_category_briefing(docs, category, context)
            content = result.get('content', '')
            
            return {
                'category': category,
                'content': content
            }
        except Exception as e:
            logger.error(f"Error processing {category} briefing: {str(e)}")
            return {
                'category': category,
                'content': ''  # Return empty content on error
            }

    async def create_briefings(self, state: ResearchState) -> Dict[str, Any]:
        """Create briefings for all categories in parallel."""
        company = state.get('company', 'Unknown Company')
        industry = state.get('industry', 'Unknown Industry')
        hq_location = state.get('hq_location', 'Unknown Location')
        
        # Create context dictionary for briefings
        context = {
            'company': company,
            'industry': industry,
            'hq_location': hq_location,
        }
        
        # Ensure correct data structures for each category
        curated_company_data = state.get('curated_company_data', {})
        curated_industry_data = state.get('curated_industry_data', {})
        curated_financial_data = state.get('curated_financial_data', {})
        curated_news_data = state.get('curated_news_data', {})
        curated_partners_data = state.get('curated_partners_data', {})  # Make sure this is included
        
        # Make sure all data structures are dictionaries, not strings
        if not isinstance(curated_company_data, dict):
            curated_company_data = {}
        if not isinstance(curated_industry_data, dict):
            curated_industry_data = {}
        if not isinstance(curated_financial_data, dict):
            curated_financial_data = {}
        if not isinstance(curated_news_data, dict):
            curated_news_data = {}
        if not isinstance(curated_partners_data, dict):
            curated_partners_data = {}
        
        # Process briefings in parallel
        results = await asyncio.gather(*[
            self.process_briefing(curated_company_data, 'company', context, state),
            self.process_briefing(curated_industry_data, 'industry', context, state),
            self.process_briefing(curated_financial_data, 'financial', context, state),
            self.process_briefing(curated_news_data, 'news', context, state),
            self.process_briefing(curated_partners_data, 'partners', context, state),  # Include partners
        ])
        
        # Store results in state
        for result in results:
            state[f"{result['category']}_briefing"] = result['content']
        
        # Store all briefings in a structured format
        state['briefings'] = {
            'company': state.get('company_briefing', ''),
            'industry': state.get('industry_briefing', ''),
            'financial': state.get('financial_briefing', ''),
            'news': state.get('news_briefing', ''),
            'partners': state.get('partners_briefing', ''),  # Include partners
        }
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        return await self.create_briefings(state)