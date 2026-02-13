from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from ratelimit import limits, sleep_and_retry

MAX_RESULTS = 5
AUTO_PARAMETERS = True
RATE_LIMIT_CALLS = 100
RATE_LIMIT_PERIOD_SECONDS = 60
RELEVANCE_SCORE_THRESHOLD = 0

def _get_search_tool(
    max_results: int = MAX_RESULTS,
    auto_parameters: bool = AUTO_PARAMETERS,
) -> TavilySearch:
    """Get a search tool with the given parameters."""
    kwargs = {
        "max_results": max_results,
        "auto_parameters": auto_parameters,
        "include_raw_content": False,
        "include_answer": False,
    }
    return TavilySearch(**kwargs)

def format_results_markdown(results: dict) -> str:
    """Format search results as loose markdown for LLM input."""
    # Grab the results and query from the results dictionary
    items = results.get("results", [])
    query = results.get("query", "")
    header = f"## Search results for: {query}\n"
    lines = [header]

    # Format the results as LLM Friendly markdown
    for index, item in enumerate(items, start=1):
        title = item.get("title", "")
        url = item.get("url", "")
        lines.append(f"{index}. [{title}]({url})")
        content = item.get("content", "")
        if content:
            lines.append(f"\t- {content}\n")

    return "\n".join(lines)

@sleep_and_retry
@limits(calls=RATE_LIMIT_CALLS, period=RATE_LIMIT_PERIOD_SECONDS)
@tool
def internet_search(query: str) -> str:
    """Run a Tavily web search and return markdown formatted results."""
    # Instantiate the search tool
    search_tool = _get_search_tool()

    # Run the search
    try:
        results = search_tool.invoke({"query": query})
    except Exception as e:
        return f"Error running search: {e}"

    # Filter the results based on the relevance score threshold
    raw_results = results.get("results", [])
    results["results"] = [
        r for r in raw_results if r.get("score", 0) >= RELEVANCE_SCORE_THRESHOLD
    ]

    # Return in markdown format
    return format_results_markdown(results)