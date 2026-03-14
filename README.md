# Autonomous SDLC Workflow: LangGraph + MCP (Proof of Concept)

## Overview
This repository contains a Proof of Concept (PoC) demonstrating an automated Software Development Life Cycle (SDLC) pipeline. It utilizes **LangGraph** for multi-agent orchestration and the **Model Context Protocol (MCP)** for secure, on-demand context injection. 

This architecture allows AI agents to read local project files directly without requiring a custom backend integration, representing a highly cost-effective and automated approach to AI-assisted development.

## Architecture

The workflow consists of a state graph with the following components:
* **Developer Agent:** Powered by Claude 3.5 Sonnet. It uses the `filesystem` MCP server to dynamically read local files as context, generating or refactoring code based on the injected knowledge.
* **Tester/Critic Agent:** Conducts purely static vulnerability analysis and logic review on the generated code.
* **Routing Logic:** Implements a feedback loop. If the static review fails, the workflow routes back to the Developer Agent with feedback. A hard limit of 3 retries is enforced to prevent infinite loops and manage API costs.

## Prerequisites
1.  **Python 3.10+**
2.  **Node.js & npm:** Required to run the Filesystem MCP Server via `npx`.
3.  **Anthropic API Key:** Claude 3.5 Sonnet is required for native MCP tool binding support.

## Installation

1. Clone the repository and navigate to the directory:
   ```bash
   # Add your clone command here
   cd your-directory
   ```
2. Install the required Python dependencies:
   ```bash
   pip install langgraph langchain-anthropic langchain-mcp-adapters mcp
   ```
3. Export your Anthropic API Key:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```
## Usage

Run the main asynchronous script to trigger the workflow:
```bash
python main.py
```
**Expected Output**
The console will output the state transitions.

The `[Developer]` node will attempt to generate the script.
The `[Tester]` node will evaluate the script.
The `[Status]` will indicate whether the code passed or was routed back for a retry.
The script terminates safely either upon a "PASS" signal or after 3 unsuccessful attempts.

## Limitations & Next Steps for Production

As a PoC, this script makes specific architectural trade-offs for rapid validation:

1. Static vs. Dynamic Testing: Currently, the Tester agent performs static code auditing. For a production environment, this node should be upgraded to execute the code in an isolated sandbox (e.g., Docker or E2B) to capture actual standard output and traceback logs.
2. Context Window Management: The current Filesystem MCP configuration allows the agent to read local files. In a larger codebase, guardrails must be implemented to prevent the agent from loading excessively large files and exceeding the LLM's token limit.
