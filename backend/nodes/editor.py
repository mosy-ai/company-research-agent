from langchain_core.messages import AIMessage
from typing import Dict, Any
from openai import AsyncOpenAI
import os
import logging

logger = logging.getLogger(__name__)

from ..classes import ResearchState
from ..utils.references import format_references_section

class Editor:
    """Compiles individual section briefings into a cohesive final report."""
    
    def __init__(self) -> None:
        self.openai_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Configure OpenAI
        self.openai_client = AsyncOpenAI(api_key=self.openai_key)
        
        # Initialize context dictionary for use across methods
        self.context = {
            "company": "Unknown Company",
            "industry": "Unknown",
            "hq_location": "Unknown"
        }

    async def compile_briefings(self, state: ResearchState) -> ResearchState:
        """Compile individual briefing categories from state into a final report."""
        company = state.get('company', 'Unknown Company')
        
        # Update context with values from state
        self.context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }
        
        # Send initial compilation status
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message=f"Starting report compilation for {company}",
                    result={
                        "step": "Editor",
                        "substep": "initialization"
                    }
                )

        context = {
            "company": company,
            "industry": state.get('industry', 'Unknown'),
            "hq_location": state.get('hq_location', 'Unknown')
        }
        
        msg = [f"📑 Compiling final report for {company}..."]
        
        # Pull individual briefings from dedicated state keys
        briefing_keys = {
            'company': 'company_briefing',
            'industry': 'industry_briefing',
            'financial': 'financial_briefing',
            'news': 'news_briefing',
            'partners': 'partners_briefing'  # Add this line to include partners
        }

        # Send briefing collection status
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="processing",
                    message="Collecting section briefings",
                    result={
                        "step": "Editor",
                        "substep": "collecting_briefings"
                    }
                )

        individual_briefings = {}
        for category, key in briefing_keys.items():
            if content := state.get(key):
                individual_briefings[category] = content
                msg.append(f"Found {category} briefing ({len(content)} characters)")
            else:
                msg.append(f"No {category} briefing available")
                logger.error(f"Missing state key: {key}")
        
        if not individual_briefings:
            msg.append("\n⚠️ No briefing sections available to compile")
            logger.error("No briefings found in state")
        else:
            try:
                compiled_report = await self.edit_report(state, individual_briefings, context)
                if not compiled_report or not compiled_report.strip():
                    logger.error("Compiled report is empty!")
                else:
                    logger.info(f"Successfully compiled report with {len(compiled_report)} characters")
            except Exception as e:
                logger.error(f"Error during report compilation: {e}")
        state.setdefault('messages', []).append(AIMessage(content="\n".join(msg)))
        return state
    
    async def edit_report(self, state: ResearchState, briefings: Dict[str, str], context: Dict[str, Any]) -> str:
        """Compile section briefings into a final report and update the state."""
        try:
            company = self.context["company"]
            
            # Step 1: Initial Compilation
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message="Compiling initial research report",
                        result={
                            "step": "Editor",
                            "substep": "compilation"
                        }
                    )

            edited_report = await self.compile_content(state, briefings, company)
            if not edited_report:
                logger.error("Initial compilation failed")
                return ""

            # Step 2: Deduplication and Cleanup
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message="Cleaning up and organizing report",
                        result={
                            "step": "Editor",
                            "substep": "cleanup"
                        }
                    )

            # Step 3: Formatting Final Report
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="processing",
                        message="Formatting final report",
                        result={
                            "step": "Editor",
                            "substep": "format"
                        }
                    )
            final_report = await self.content_sweep(state, edited_report, company)
            
            final_report = final_report or ""
            
            logger.info(f"Final report compiled with {len(final_report)} characters")
            if not final_report.strip():
                logger.error("Final report is empty!")
                return ""
            
            logger.info("Final report preview:")
            logger.info(final_report[:500])
            
            # Update state with the final report in two locations
            state['report'] = final_report
            state['status'] = "editor_complete"
            if 'editor' not in state or not isinstance(state['editor'], dict):
                state['editor'] = {}
            state['editor']['report'] = final_report
            logger.info(f"Report length in state: {len(state.get('report', ''))}")
            
            if websocket_manager := state.get('websocket_manager'):
                if job_id := state.get('job_id'):
                    await websocket_manager.send_status_update(
                        job_id=job_id,
                        status="editor_complete",
                        message="Research report completed",
                        result={
                            "step": "Editor",
                            "report": final_report,
                            "company": company,
                            "is_final": True,
                            "status": "completed"
                        }
                    )
            
            return final_report
        except Exception as e:
            logger.error(f"Error in edit_report: {e}")
            return ""
    
    async def compile_content(self, state: ResearchState, briefings: Dict[str, str], company: str) -> str:
        """Initial compilation of research sections."""
        
        # Get all briefing sections
        company_briefing = briefings.get('company', '')
        industry_briefing = briefings.get('industry', '')
        financial_briefing = briefings.get('financial', '')
        news_briefing = briefings.get('news', '')
        partners_briefing = briefings.get('partners', '')  # Make sure partners section is included
    
        # Create a prompt for LLM with partners section included
        prompt = f"""Compile this research into a professional company research report on {company}.

## Company Overview
{company_briefing}

## Industry Overview
{industry_briefing}

## Financial Overview
{financial_briefing}

## Partnership Overview
{partners_briefing}

## News
{news_briefing}

Return the report in clean markdown format. No explanations or commentary."""
    
        # Initialize combined_content variable before the try block
        combined_content = ""
    
        try:
            # Your existing code for calling the LLM
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-mini", 
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert business analyst that creates comprehensive research reports."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
            )
        
            combined_content = response.choices[0].message.content
            return combined_content.strip()
        except Exception as e:
            logger.error(f"Error in initial compilation: {e}")
            return (combined_content or "").strip()
        
    async def content_sweep(self, state: ResearchState, content: str, company: str) -> str:
        """Sweep the content for any redundant information."""
        
        # Process references from search results
        from ..utils.references import process_references_from_search_results, format_references_section
        
        # Get references from search results
        top_reference_urls, reference_titles, reference_info = process_references_from_search_results(state)
        
        # Format references section
        references_section = format_references_section(top_reference_urls, reference_info, reference_titles)
        
        # If no references were found, add a placeholder
        if not references_section:
            references_section = "\n## References\n* No references found."
    
        prompt = f"""Clean up and refine this company research report on {company}.

{content}

{references_section}

Critical rules:
1. The document MUST start with "# {company} Research Report"
2. The document MUST ONLY use these exact ## headers in this order:
   - ## Company Overview
   - ## Industry Overview 
   - ## Partnership Overview
   - ## Financial Overview
   - ## News
   - ## References
3. Preserve the References section exactly as provided.
"""
    
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4.1-mini", 
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert markdown formatter that ensures consistent document structure."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                stream=True
            )
            
            accumulated_text = ""
            buffer = ""
            
            async for chunk in response:
                if chunk.choices[0].finish_reason == "stop":
                    websocket_manager = state.get('websocket_manager')
                    if websocket_manager and buffer:
                        job_id = state.get('job_id')
                        if job_id:
                            await websocket_manager.send_status_update(
                                job_id=job_id,
                                status="report_chunk",
                                message="Formatting final report",
                                result={
                                    "chunk": buffer,
                                    "step": "Editor"
                                }
                            )
                    break
                    
                chunk_text = chunk.choices[0].delta.content
                if chunk_text:
                    accumulated_text += chunk_text
                    buffer += chunk_text
                    
                    if any(char in buffer for char in ['.', '!', '?', '\n']) and len(buffer) > 10:
                        if websocket_manager := state.get('websocket_manager'):
                            if job_id := state.get('job_id'):
                                await websocket_manager.send_status_update(
                                    job_id=job_id,
                                    status="report_chunk",
                                    message="Formatting final report",
                                    result={
                                        "chunk": buffer,
                                        "step": "Editor"
                                    }
                                )
                        buffer = ""
            
            return (accumulated_text or "").strip()
        except Exception as e:
            logger.error(f"Error in formatting: {e}")
            return (content or "").strip()

    async def run(self, state: ResearchState) -> ResearchState:
        """Run the editor process."""
        # Get company name from state
        company = state.get('company', 'Unknown Company')
        
        # Get briefings dictionary
        briefings = state.get('briefings', {})
        
        # Make sure we have all briefings
        if not briefings:
            logger.warning("No briefings found in state")
            briefings = {}
        
        # Compile content from briefings
        compiled_content = await self.compile_content(state, briefings, company)
        
        # Final editing pass
        final_report = await self.content_sweep(state, compiled_content, company)
        
        # Save the report to state
        state['report'] = final_report
        
        # Also add a flag showing completion
        state['report_generated'] = True
        
        # Send a status update via WebSocket
        if websocket_manager := state.get('websocket_manager'):
            if job_id := state.get('job_id'):
                await websocket_manager.send_status_update(
                    job_id=job_id,
                    status="completed",
                    message="Research report generated",
                    result={
                        "step": "Complete",
                        "report": final_report
                    }
                )
        
        logger.info("Editor completed processing")
        return state
