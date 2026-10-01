from mcp.server.fastmcp import FastMCP


mcp = FastMCP("demo-search")


@mcp.tool()
def search(
    query: str,
    limit: int = 3,
) -> list[dict[str, str]]:
    results = [
        {
            "title": "LangGraph documentation",
            "url": "https://example.com/langgraph",
            "snippet": "Graph-based agent workflows.",
        },
        {
            "title": "Agent orchestration",
            "url": "https://example.com/orchestration",
            "snippet": "Patterns for coordinating agents.",
        },
        {
            "title": "Typed tool interfaces",
            "url": "https://example.com/tools",
            "snippet": "Typed boundaries improve reliability.",
        },
    ]

    return results[:limit]


if __name__ == "__main__":
    mcp.run()