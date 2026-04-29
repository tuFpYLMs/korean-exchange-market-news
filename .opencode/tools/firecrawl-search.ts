import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Search the web using Firecrawl and return structured content from search results. Combines web search with content scraping.",
  args: {
    query: tool.schema.string().describe("Search query to find relevant web content"),
    limit: tool.schema.number().optional().describe("Number of results to return (default: 5, max: 10)"),
  },
  async execute(args, context) {
    const apiKey = process.env.FIRECRAWL_API_KEY
    if (!apiKey) {
      throw new Error("FIRECRAWL_API_KEY environment variable is not set")
    }

    const limit = args.limit || 5

    const response = await fetch("https://api.firecrawl.dev/v2/search", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: args.query,
        limit: limit,
        sources: ["web"],
        scrapeOptions: {
          formats: ["markdown"],
          onlyMainContent: true,
          maxAge: 86400, // 24 hours
          timeout: 30000,
        },
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Firecrawl search failed: ${response.status} - ${error}`)
    }

    const data = await response.json()
    
    // Format results for LLM consumption
    const results = data.data?.map((result: any, index: number) => {
      return `### Result ${index + 1}: ${result.title}\n**URL:** ${result.url}\n**Content:**\n${result.markdown || result.description || "No content available"}\n---`
    }).join("\n\n") || "No results found"

    return `## Firecrawl Search Results for: "${args.query}"\n\n${results}`
  },
})
