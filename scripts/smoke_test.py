"""API 키 없이 MCP stdio 연결과 BM25 검색 도구를 검증한다."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "server.py")],
        cwd=ROOT,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("MCP handshake: OK")

            tools = await session.list_tools()
            print("Tools:", ", ".join(tool.name for tool in tools.tools))

            query = "MRR과 nDCG는 언제 사용해?"
            print("Call: search_documents")
            print("Query:", query)
            result = await session.call_tool(
                "search_documents",
                arguments={"query": query},
            )
            for block in result.content:
                text = getattr(block, "text", None)
                if text:
                    print(text)
                else:
                    print(json.dumps(block.model_dump(), ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
