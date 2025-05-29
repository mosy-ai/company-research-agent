from typing import TypedDict, NotRequired, Required, Dict, List, Any
from backend.services.websocket_manager import WebSocketManager

#Define the input state
class InputState(TypedDict, total=False):
    company: Required[str]
    company_url: NotRequired[str]
    hq_location: NotRequired[str]
    industry: NotRequired[str]
    partners: NotRequired[str]  # Add this line
    websocket_manager: NotRequired[WebSocketManager]
    job_id: NotRequired[str]

class ResearchState(InputState):
    site_scrape: Dict[str, Any]
    messages: List[Any]
    financial_data: Dict[str, Any]
    news_data: Dict[str, Any]
    industry_data: Dict[str, Any]
    company_data: Dict[str, Any]
    curated_financial_data: Dict[str, Any]
    curated_news_data: Dict[str, Any]
    curated_industry_data: Dict[str, Any]
    curated_company_data: Dict[str, Any]
    partners_data: Dict[str, Any]              # Add this line
    curated_partners_data: Dict[str, Any]      # Add this line
    financial_briefing: str
    news_briefing: str
    industry_briefing: str
    company_briefing: str
    partners_briefing: str                     # Add this line
    references: List[str]
    briefings: Dict[str, Any]
    report: str