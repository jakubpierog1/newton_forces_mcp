#!/usr/bin/env python3
import asyncio
import json
import requests
import os
import subprocess
from datetime import datetime
from contextlib import AsyncExitStack
import cairosvg  # <-- New import
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class OllamaMCPClient:
    def __init__(self, ollama_model="llama3", ollama_host="http://localhost:11434"):
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

    def maybe_save_svg(self, svg_string):
        """Save SVG to a file if it's valid SVG, auto-open in VS Code, convert to PDF, return the path or None."""
        if isinstance(svg_string, str) and svg_string.strip().startswith("<svg"):
            filename = f"diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(svg_string)
            print(f"\n🖼️ SVG Free Body Diagram saved as '{filename}'! Opening in VS Code...\n")
            try:
                subprocess.run(["code", filename])
            except Exception as e:
                print("Couldn't auto-open SVG in VS Code:", e)
            # Convert SVG to PDF
            pdf_filename = filename.replace(".svg", ".pdf")
            try:
                cairosvg.svg2pdf(url=filename, write_to=pdf_filename)
                print(f"📄 PDF version also saved as '{pdf_filename}'")
                try:
                    subprocess.run(["code", pdf_filename])
                except Exception as e:
                    print("Couldn't auto-open PDF in VS Code:", e)
            except Exception as e:
                print("Couldn't convert SVG to PDF:", e)
            return filename
        return None

    async def process_diagram_request(self, user_query):
        print(f"📥 User query: {user_query}")

        system_prompt = """
You are a physics free body diagram expert.
- If the user asks for a free body diagram, use the TOOL: free_body with a list of forces, each as {'label': 'Weight', 'vector': {'magnitude': 10, 'angle_deg': 270}} or as [x, y].
- If the user gives raw numbers or equations, use the smart_diagram tool and extract all necessary values.
- If the user asks for net force, use net_force.

Always respond in this format:

TOOL: <tool_name>
ARGS: {<json dictionary>}

Examples:
TOOL: free_body
ARGS: {"forces": [{"label": "Weight", "vector": {"magnitude": 10, "angle_deg": 270}}, {"label": "Normal", "vector": [0, 10]}], "object_name": "Box"}

TOOL: net_force
ARGS: {"forces": [[5, 3], {"magnitude": 10, "angle_deg": 180}]}

TOOL: smart_diagram
ARGS: {"forces": ["20", {"magnitude": 5, "angle_deg": 0}, [0, -8]], "object_name": "Cart"}

NEVER include explanations, just TOOL and ARGS.

Show the diagram in line.
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
                    print("[Parse Error] Could not decode ARGS.")
                    return "[Parse Error] Could not decode ARGS."

        if not tool_name or not args:
            print("[Error] Could not parse tool or arguments.")
            return "[Error] Could not parse tool or arguments."

        print(f"🔧 Calling MCP tool: {tool_name} with args {args}")
        mcp_result = await self.call_mcp_tool(tool_name, args)

        if isinstance(mcp_result, str) and mcp_result.strip().startswith("<svg"):
            self.maybe_save_svg(mcp_result)
        else:
            print(f"\n🗣️ Assistant: {mcp_result}\n")
        return mcp_result

    async def chat_loop(self):
        print("🤖 Diagram Assistant ready. Type 'quit' to exit.\n")
        await self.connect_to_server("diagram.py", cwd=os.getcwd())

        while True:
            user_input = input("📝 Describe your free body diagram scenario: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Exiting. Draw physics every day!")
                break
            if not user_input:
                continue
            try:
                await self.process_diagram_request(user_input)
            except Exception as e:
                print(f"[Error] {e}")

async def main():
    client = OllamaMCPClient()
    await client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())
