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

    async def process_conversion_request(self, user_query):
        print(f"📥 User query: {user_query}")

        system_prompt = """
You are a smart physics and units conversion assistant. 
- If the user gives values in the "wrong" units for a calculation (e.g., mass in grams for F = m·a), automatically convert and explain.
- You know that 1 N = 1 kg·m/s², and you can simplify and break down units.
- You have these tools:
1. convert_units(value, from_unit, to_unit): converts between units (e.g., grams to kg, cm to m, Pa to N/m^2).
2. simplify_unit(unit_expr): writes a unit as SI base units (e.g., N as kg·m/s²).
3. smart_force(mass_value, mass_unit, accel_value, accel_unit): computes force, converting units if needed.
4. simplify_expression(expr): simplifies compound unit expressions.

Always extract needed numbers and units from the user's question, fill in the tool arguments, and respond in clear, natural English.

Examples:
TOOL: convert_units
ARGS: {"value": 1500, "from_unit": "g", "to_unit": "kg"}

TOOL: smart_force
ARGS: {"mass_value": 300, "mass_unit": "g", "accel_value": 2.5, "accel_unit": "m/s^2"}

TOOL: simplify_unit
ARGS: {"unit_expr": "N"}

TOOL: simplify_expression
ARGS: {"expr": "(kg*m/s^2)/(N)"}
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

Respond naturally, explain any automatic conversions, simplifications, or SI relationships you used.
"""
        final_response = await self.call_ollama(final_prompt)
        return final_response

    async def chat_loop(self):
        print("🤖 Conversions Assistant ready. Type 'quit' to exit.\n")
        await self.connect_to_server("conversions.py", cwd="/Users/jakubpierog/Documents/newton_forces_mcp/conversions")

        while True:
            user_input = input("🔄 Ask any unit, physics, or simplification question: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Exiting. Stay curious about units!")
                break
            if not user_input:
                continue
            try:
                response = await self.process_conversion_request(user_input)
                print(f"\n🗣️ Assistant: {response}\n")
            except Exception as e:
                print(f"[Error] {e}")

async def main():
    client = OllamaMCPClient()
    await client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())
