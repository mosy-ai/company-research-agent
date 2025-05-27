import os
import pytest
# from dotenv import load_dotenv
from backend.nodes.researchers.news import NewsScanner
from backend.classes import ResearchState

# Load environment variables from .env file
# load_dotenv()

@pytest.mark.asyncio
async def test_news_scanner_analysis():
    # Initialize test state
    state = ResearchState({
        'company': 'Tesla',
        'company_url': 'https://www.tesla.com',
        'site_scrape': 'Tesla is accelerating the world\'s transition to sustainable energy.',
        'messages': [],
        'job_id': 'test-job-123'
    })
    
    # Initialize NewsScanner
    scanner = NewsScanner()
    
    # Run analysis
    result = await scanner.analyze(state)
    
    # Verify results
    assert isinstance(result, dict)
    assert 'message' in result
    assert 'news_data' in result
    assert isinstance(result['news_data'], dict)
    
    # Verify state updates
    assert 'news_data' in state
    assert 'messages' in state
    assert len(state['messages']) > 0
    
    # Verify news data structure
    print(result['news_data'].keys())
    print(result['news_data'])
