from langchain_tavily import TavilySearch

MAX_RESULTS = 5
AUTO_PARAMETERS = True
RELEVANCE_SCORE_THRESHOLD = 0.7
TOOL_DESCRIPTION = """Internet Search Tool, takes in a natural language query and returns back relevant results + snippets from the web.
Usage guidelines:
1. Use Natural Language - The search tool is designed to handle semantic queries, avoid search engine operators or specific syntax.
2. Be Specific - Avoid broad, multi-topic queries. Call this tool multiple times for different topics.
"""


def build_tavily_tool(
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
    tool = TavilySearch(**kwargs)
    tool.name = "internet_search"
    tool.description = TOOL_DESCRIPTION
    return tool


def process_search_results(results: dict) -> str:
    """Filter out low-relevance results and format the rest as markdown for LLM input."""
    items = [
        item
        for item in results.get("results", [])
        if item.get("score", 0) >= RELEVANCE_SCORE_THRESHOLD
    ]
    query = results.get("query", "")
    lines = [f"## Search results for: {query}\n"]

    for index, item in enumerate(items, start=1):
        title = item.get("title", "")
        url = item.get("url", "")
        lines.append(f"{index}. [{title}]({url})")
        content = item.get("content", "")
        if content:
            lines.append(f"\t- {content}\n")

    return "\n".join(lines)