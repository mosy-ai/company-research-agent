from langchain_core.messages import AIMessage
from typing import Dict, Any
from ...classes import ResearchState
from .base import BaseResearcher

class PartnerAnalyzer(BaseResearcher):
    def __init__(self) -> None:
        super().__init__()
        self.analyst_type = "partners"  # Make sure this matches the category name used in curator.py

    async def analyze(self, state: ResearchState) -> Dict[str, Any]:
        company = state.get('company', 'Unknown Company')
        partners = state.get('partners', '')
        msg = [f"🤝 Partner Analyzer analyzing {company}"]
        
        # Generate more specific partnership queries
        queries = await self.generate_queries(state, f"""
        Generate detailed research queries about {company}'s partnerships, focusing on:
        1. Strategic partnerships with {partners if partners else 'key companies'}
        2. Technical integrations and how they work together
        3. Joint ventures and business alliances
        4. Distribution or reseller partnerships
        5. Partnership benefits and success metrics
        
        Create queries that will discover HOW these partnerships function, not just who the partners are.
        """)

        subqueries_msg = "🔍 Subqueries for partnership analysis:\n" + "\n".join([f"• {query}" for query in queries])
        messages = state.get('messages', [])
        messages.append(AIMessage(content=subqueries_msg))
        state['messages'] = messages
        
        # Send queries through WebSocket
        websocket_manager = state.get('websocket_manager')
        job_id = state.get('job_id')
        if websocket_manager and job_id:
            await websocket_manager.send_status_update(
                job_id=job_id,
                status="processing",
                message=f"Partner analysis queries generated",
                result={
                    "step": "Searching",
                    "analyst_type": "partners",  # Use "partners" to match the category name
                    "queries": queries
                }
            )
        
        partners_data = {}
        
        # If we have site_scrape data, include it first
        if site_scrape := state.get('site_scrape'):
            msg.append("\n📊 Including site scrape data in partner analysis...")
            company_url = state.get('company_url', 'company-website')
            partners_data[company_url] = {
                'title': state.get('company', 'Unknown Company'),
                'raw_content': site_scrape,
                'query': f'Partnerships and integrations for {company}'
            }
        
        # Perform research
        try:
            for query in queries:
                documents = await self.search_documents(state, [query])
                if documents:
                    for url, doc in documents.items():
                        doc['query'] = query
                        partners_data[url] = doc
            
            msg.append(f"\n✓ Found {len(partners_data)} documents")
            if websocket_manager and job_id:
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Used Tavily Search to find {len(partners_data)} documents",
                    result={
                        "step": "Searching",
                        "analyst_type": "partners",  # Use "partners" to match the category name
                        "queries": queries
                    }
                )
        except Exception as e:
            msg.append(f"\n⚠️ Error during research: {str(e)}")
        
        # Update state with our findings
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        state['partners_data'] = partners_data
        
        return {
            'message': msg,
            'partners_data': partners_data
        }

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        return await self.analyze(state)