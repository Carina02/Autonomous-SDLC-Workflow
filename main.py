import os
import asyncio
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

# Import the latest MCP adapters
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools


# ==========================================
# 1. Shared Scratchpad (State): Keep only essential fields
# ==========================================
class SDLCState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    draft_code: str
    feedback: str
    retry_count: int


# ==========================================
# 2. Global Configuration: Claude 3.5 Sonnet
# Note: ANTHROPIC_API_KEY must be configured in the environment variables
# ==========================================
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)


# ==========================================
# 3. Nodes and Routing Logic
# ==========================================
async def developer_node(state: SDLCState):
    """Developer Agent: Loads Filesystem MCP Server on demand to read local files and write code"""
    current_retry = state.get('retry_count', 0)
    print(f"\n-> [Developer] Generating code (Attempt {current_retry + 1})...")

    # Mount Filesystem MCP Server (Example: restricting access to the current directory)
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Convert MCP tools to standard LangChain Tools
            mcp_tools = await load_mcp_tools(session)

            # Bind tools to the LLM
            llm_with_tools = llm.bind_tools(mcp_tools)

            sys_msg = SystemMessage(
                content="You are a senior Python developer. You can use the mounted filesystem tools to read the required context. Please output pure Python code only."
            )

            current_messages = [sys_msg] + state["messages"]
            if state.get("feedback"):
                current_messages.append(HumanMessage(
                    content=f"Static code review failed. Feedback:\n{state['feedback']}\nPlease fix the code."
                ))

            # In a production environment, this might involve multiple ToolMessage loops.
            # For this PoC, we directly extract the result.
            response = await llm_with_tools.ainvoke(current_messages)

            return {
                "draft_code": str(response.content),
                "retry_count": current_retry + 1
            }


async def tester_node(state: SDLCState):
    """Tester/Critic Agent: Pure static analysis, no code execution"""
    print("-> [Tester] Performing static vulnerability analysis...")

    analysis_prompt = f"""
    As a code audit expert, perform a static review of the following Python code. 
    Focus on: unhandled exceptions, edge cases, and performance bottlenecks.

    ```python
    {state['draft_code']}
    ```

    If there are absolutely no issues, reply with strictly "PASS". 
    If you find issues, explicitly point out the logical flaws.
    """
    response = await llm.ainvoke([HumanMessage(content=analysis_prompt)])
    return {"feedback": response.content}


def critic_router(state: SDLCState) -> Literal["developer", "__end__"]:
    """Evaluate forced termination condition and routing"""
    feedback = state.get("feedback", "").strip().upper()
    retry_count = state.get("retry_count", 0)

    # Exit condition: Max retries reached and still not passing
    if retry_count >= 3 and "PASS" not in feedback:
        print(
            f"-> [Critic] Exception: Max retries ({retry_count}) reached. Workflow suspended, manual intervention required.")
        raise RuntimeError(f"Workflow interrupted. Exceeded max retries. Last Feedback: {feedback}")

    if "PASS" in feedback:
        print("-> [Status] Static analysis passed. Workflow complete.")
        return "__end__"
    else:
        print("-> [Status] Defects found. Routing back to Developer.")
        return "developer"


# ==========================================
# 4. Graph Compilation and Execution
# ==========================================
def build_graph():
    builder = StateGraph(SDLCState)
    builder.add_node("developer", developer_node)
    builder.add_node("tester", tester_node)

    builder.add_edge(START, "developer")
    builder.add_edge("developer", "tester")
    builder.add_conditional_edges("tester", critic_router)

    return builder.compile()


async def run_poc():
    graph = build_graph()

    # Simulated input: Requesting a safe parsing script for a local config file
    initial_state = {
        "messages": [HumanMessage(
            content="Please write a safe script to parse config.json in this directory. It must degrade gracefully even if the file is missing or the JSON is corrupted.")],
        "retry_count": 0
    }

    try:
        async for output in graph.astream(initial_state):
            pass  # Suppress underlying state stream output to keep the console clean
    except RuntimeError as e:
        print(f"\n[Blocking Exception] {e}")


if __name__ == "__main__":
    asyncio.run(run_poc())