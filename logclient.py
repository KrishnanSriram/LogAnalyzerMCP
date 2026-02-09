import asyncio
import sys
from mcp import ClientSession
from mcp.client.sse import sse_client


async def list_tools(url):
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            for tool in tools.tools:
                print(f"{tool.name}: {tool.description}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
    asyncio.run(list_tools(url))

# import asyncio
# from fastmcp import Client
#
# client = Client("http://localhost:8000/mcp")
#
# async def call_tool(name: str):
#     async with client:
#         result = await client.call_tool("greet", {"name": name})
#         print(result)
#
# if __name__ == "__main__":
#     asyncio.run(call_tool("Ford"))
