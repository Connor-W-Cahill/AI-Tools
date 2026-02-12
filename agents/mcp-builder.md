# MCP Builder

Guide for creating MCP (Model Context Protocol) servers that enable LLMs to interact with external services.

## When to Use
- Building MCP servers to integrate external APIs
- Designing tools for AI agent workflows
- Evaluating or improving existing MCP servers

## Supported Languages
- **Python**: FastMCP / MCP Python SDK
- **TypeScript**: MCP TypeScript SDK

## Design Principles
- Build for workflows, not just API endpoints
- Optimize for limited context windows (return high-signal data)
- Design actionable error messages that guide agents
- Follow natural task subdivisions
- Use evaluation-driven development

## Process
1. **Research**: Study API docs, understand MCP protocol (`https://modelcontextprotocol.io/llms-full.txt`)
2. **Plan**: Select tools, design input/output schemas, plan error handling
3. **Implement**: Core infrastructure first, then tools systematically
4. **Review**: DRY, composability, consistency, type safety, documentation
5. **Evaluate**: Create 10 realistic test questions, verify answers

## Quality Checklist
- Pydantic (Python) or Zod (TypeScript) for input validation
- Comprehensive docstrings/descriptions on every tool
- Tool annotations (readOnlyHint, destructiveHint, etc.)
- Async/await for all I/O
- Character limits and truncation strategies
- Multiple response formats (JSON and Markdown)
