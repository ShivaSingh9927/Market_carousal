from langchain_community.tools import DuckDuckGoSearchResults
from langchain.tools import tool

@tool
def robust_web_search(query: str) -> str:
    """
    Performs structured market intelligence search.
    Gathers:
    - Current trends
    - Competitor positioning
    - Community pain points
    - Recent news
    
    Returns structured output optimized for strategic analysis.
    """
    try:
        search = DuckDuckGoSearchResults(num_results=8)

        trend_query = f"{query} trends insights in one line"
        competitor_query = f"{query} competitors alternatives comparison in one line"
        pain_query = f"{query} problems complaints reddit discussion in one line"
        news_query = f"{query} recent news updates in one line"

        trends = search.run(trend_query)
        competitors = search.run(competitor_query)
        pain_points = search.run(pain_query)
        news = search.run(news_query)

        structured_output = f"""
        === MARKET TRENDS ===
        {trends}

        === COMPETITOR LANDSCAPE ===
        {competitors}

        === USER PAIN POINTS ===
        {pain_points}

        === RECENT NEWS / MOVEMENTS ===
        {news}
        """

        return structured_output.strip()

    except Exception as e:
        return f"Search Error: {str(e)}"
