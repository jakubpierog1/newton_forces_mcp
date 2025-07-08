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

    async def process_vector_request(self, user_query):
        print(f"📥 User query: {user_query}")

        system_prompt = """You are a careful physics assistant for vectors. You can add, subtract, or convert vectors.
ALWAYS be clear about units (Newtons), directions (degrees counterclockwise from +x axis), and vector format.
You have these tools:
1. add_vectors(vector1, vector2)
2. subtract_vectors(vector1, vector2)
3. to_components(magnitude, angle_deg)
4. to_polar(x, y)

Users may describe vectors by components ([x, y] in N), or magnitude/angle (N, degrees CCW from +x).

Sample tool calls:
TOOL: add_vectors
ARGS: {"vector1": {"magnitude": 10, "angle_deg": 30}, "vector2": [3, 4]}
TOOL: subtract_vectors
ARGS: {"vector1": [8, -2], "vector2": {"magnitude": 5, "angle_deg": 180}}
TOOL: to_components
ARGS: {"magnitude": 6, "angle_deg": 120}
TOOL: to_polar
ARGS: {"x": -4, "y": 7}

Always clarify direction, magnitude, and units in your answers.
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

Respond naturally and *always* state the magnitude in Newtons, direction in degrees (counterclockwise from +x axis), and vector form in components and polar form if possible.
"""
        final_response = await self.call_ollama(final_prompt)
        return final_response

    async def chat_loop(self):
        print("🤖 Vectors Assistant ready. Type 'quit' to exit.\n")
        await self.connect_to_server("vectors.py", cwd="/Users/jakubpierog/Documents/newton_forces_mcp/vectors")

        while True:
            user_input = input("➕ Ask about vector addition/subtraction (be specific about units and direction!): ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Exiting. Vectors are fun!")
                break
            if not user_input:
                continue
            try:
                response = await self.process_vector_request(user_input)
                print(f"\n🗣️ Assistant: {response}\n")
            except Exception as e:
                print(f"[Error] {e}")

async def main():
    client = OllamaMCPClient()
    await client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())
