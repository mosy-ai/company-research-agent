from langchain_core.messages import AIMessage
from ..classes import ResearchState

class Collector:
    """Collects and organizes all research data before curation."""

    async def collect(self, state: ResearchState) -> ResearchState:
        """Collect and verify all research data is present."""
        company = state.get('company', 'Unknown Company')
        msg = [f"📦 Collecting research data for {company}:"]

        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Collecting research data for {company}",
                    result={"step": "Collecting"}
                )
        
        # Check each type of research data
        research_types = {
            'financial_data': '💰 Financial',
            'news_data': '📰 News',
            'industry_data': '🏭 Industry',
            'company_data': '🏢 Company'
        }
        
        for data_field, label in research_types.items():
            data = state.get(data_field, {})
            if data:
                msg.append(f"• {label}: {len(data)} documents collected")
            else:
                msg.append(f"• {label}: No data found")
        
        # Update state with collection message
        messages = state.get('messages', [])
        messages.append(AIMessage(content="\n".join(msg)))
        state['messages'] = messages
        
        return state

    async def run(self, state: ResearchState) -> ResearchState:
        # Collect research data
        await self.collect(state)
        
        # Make sure partners_data is included
        partners_data = state.get('partners_data', {})
        
        # Return with partners_data included
        return {
            'financial_data': state.get('financial_data', {}),
            'news_data': state.get('news_data', {}),
            'industry_data': state.get('industry_data', {}),
            'company_data': state.get('company_data', {}),
            'partners_data': partners_data,  # Make sure this is included
        }