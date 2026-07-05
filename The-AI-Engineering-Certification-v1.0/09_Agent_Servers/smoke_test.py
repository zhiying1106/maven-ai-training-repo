import asyncio

from langgraph_sdk import get_client


async def main() -> None:
    client = get_client(url="http://localhost:2024")

    async for chunk in client.runs.stream(
        None,
        "simple_agent",
        input={"messages": [{"role": "human", "content": "How often should I deworm my cat?"}]},
        stream_mode="updates",
    ):
        print(chunk)


if __name__ == "__main__":
    asyncio.run(main())