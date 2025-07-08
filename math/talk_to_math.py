#!/usr/bin/env python3
import asyncio
import json
import requests
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class OllamaMCPClient:
    def __init__(self, ollama_model="llama3.2", ollama_host="http://localhost:11434"):
        self.ollama_model = ollama_model
        self.ollama_host = ollama_host
        self.mcp_session = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str, cwd: str):
        command = "uv" if server_script_path.endswith(".py") else "node"
        args = ["run", server_script_path] if command == "uv" else [server_script_path]
        server_params = StdioServerParameters(
            command=command,
            args=args,
            cwd=cwd
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.mcp_session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.mcp_session.initialize()
        tools = await self.mcp_session.list_tools()
        print("✅ Connected to MCP. Available tools:")
        for tool in tools.tools:
            print(f"  • {tool.name}: {tool.description}")

    async def call_ollama(self, prompt, system_prompt=None):
        def _make_request():
            url = f"{self.ollama_host}/api/generate"
            data = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False
            }
            if system_prompt:
                data["system"] = system_prompt
            response = requests.post(url, json=data)
            if response.status_code == 200:
                return response.json()["response"]
            return f"[Ollama Error] Status code {response.status_code}"
        return await asyncio.to_thread(_make_request)

    async def call_mcp_tool(self, tool_name, args):
        if not self.mcp_session:
            return "[MCP Error] MCP session not started"
        try:
            result = await self.mcp_session.call_tool(tool_name, args)
            return result.content
        except Exception as e:
            return f"[MCP Exception] {e}"

    async def process_math_request(self, user_query):
        print(f"📥 User query: {user_query}")

        system_prompt = """
You are a super smart math and physics units assistant. 
- You can solve arithmetic, fractions, exponents, roots, and complex expressions.
- You automatically handle and simplify units: you know that 1N = 1 kg·m/s² and can carry out unit math (e.g. 5N * 8kg = 40 m·kg²/s²).
- If the user asks for a conversion, use the convert_answer tool.
- For unit simplification, use simplify_units.
- For pure calculation, use evaluate.
- Always parse and calculate the user's intent, even from natural language, and provide TOOL and ARGS only.

ALWAYS respond in this format:

TOOL: <tool_name>
ARGS: {<json dictionary>}

Examples:
TOOL: evaluate
ARGS: {"expr": "5N * 8kg"}

TOOL: convert_answer
ARGS: {"expr": "40 m*kg^2/s^2", "to_unit": "N"}

TOOL: evaluate
ARGS: {"expr": "sqrt(225) + (2/3)"}

TOOL: simplify_units
ARGS: {"expr": "N*kg"}

Never output anything except the TOOL and ARGS blocks, no explanations or descriptions.
"""

        llm_response = await self.call_ollama(user_query, system_prompt)
        print(f"🧠 LLM suggested:\n{llm_response}")

        tool_name, args = None, {}
        for line in llm_response.splitlines():
            if line.startswith("TOOL:"):
                tool_name = line.split("TOOL:")[1].strip()
            elif line.startswith("ARGS:"):
                try:
                    args = json.loads(line.split("ARGS:")[1].strip())
                except json.JSONDecodeError:
                    return "[Parse Error] Could not decode ARGS."

        if not tool_name or not args:
            return "[Error] Could not parse tool or arguments."

        print(f"🔧 Calling MCP tool: {tool_name} with args {args}")
        mcp_result = await self.call_mcp_tool(tool_name, args)
        print(f"📦 MCP returned:\n{mcp_result}")

        final_prompt = f"""User asked: {user_query}

Tool result: {mcp_result}

Respond in plain, natural English, showing all math and units clearly, and explain how the units were combined or simplified if needed.
"""
        final_response = await self.call_ollama(final_prompt)
        return final_response

    async def chat_loop(self):
        print("🤖 Math & Units Assistant ready. Type 'quit' to exit.\n")
        await self.connect_to_server("math_server.py", cwd="/Users/jakubpierog/Documents/newton_forces_mcp/math")

        while True:
            user_input = input("🧮 Ask any math, unit, or physics equation: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Exiting. Keep calculating!")
                break
            if not user_input:
                continue
            try:
                response = await self.process_math_request(user_input)
                print(f"\n🗣️ Assistant: {response}\n")
            except Exception as e:
                print(f"[Error] {e}")

async def main():
    client = OllamaMCPClient()
    await client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())
