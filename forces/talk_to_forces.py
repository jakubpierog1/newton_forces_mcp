import asyncio
import json
import requests
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Update this to your actual Ollama model if needed
OLLAMA_MODEL = "llama3"

SYSTEM_PROMPT = """
You are a physics forces assistant. You have access to these tools:
1. applied_force(mass_kg, acceleration)
2. weight(mass_kg)
3. friction(normal_force, coefficient)
4. tension(weight, mass)
5. normal_force(mass, gravity, incline_angle_deg)
6. net_force(forces)
7. force_breakdown(situation)

Given a user request, respond ONLY in this format:

TOOL: <tool_name>
ARGS: <JSON args>

Examples:
User: What is the applied force if the mass is 5kg and acceleration is 2m/s^2?
TOOL: applied_force
ARGS: {"mass_kg": 5, "acceleration": 2}

User: Calculate the weight of a 10kg object.
TOOL: weight
ARGS: {"mass_kg": 10}
"""

def call_ollama(user_query, system_prompt=SYSTEM_PROMPT):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": OLLAMA_MODEL,
        "prompt": user_query,
        "stream": False,
        "system": system_prompt
    }
    print("📡 Calling Ollama to parse your request...")
    resp = requests.post(url, json=data)
    if resp.status_code == 200:
        return resp.json()["response"]
    else:
        print(f"[Ollama error] {resp.text}")
        return None

class ForcesMCPClient:
    def __init__(self):
        self.mcp_session = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str, cwd: str):
        server_params = StdioServerParameters(
            command="uv",
            args=["run", server_script_path],
            cwd=cwd
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.mcp_session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.mcp_session.initialize()
        tools = await self.mcp_session.list_tools()
        print("✅ Connected to Forces MCP. Tools:")
        for tool in tools.tools:
            print(f"  • {tool.name}: {tool.description}")

    async def call_mcp_tool(self, tool_name, args):
        if not self.mcp_session:
            return "[MCP Error] MCP session not started"
        try:
            result = await self.mcp_session.call_tool(tool_name, args)
            return result.content
        except Exception as e:
            return f"[MCP Exception] {e}"

    async def chat_loop(self):
        print("🤖 Forces Assistant ready. Type 'quit' to exit.\n")
        await self.connect_to_server("forces.py", cwd="/Users/jakubpierog/Documents/newton_forces_mcp/forces")


        while True:
            user_input = input("\nAsk about forces (type 'quit' to exit): ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("👋 Exiting. Stay strong!")
                break
            if not user_input:
                continue

            # 1. Parse the user input using Ollama LLM
            llm_response = call_ollama(user_input, SYSTEM_PROMPT)
            print(f"\n🧠 LLM parsed:\n{llm_response.strip()}")

            # 2. Extract tool name and args
            tool_name, args = None, {}
            for line in llm_response.splitlines():
                if line.startswith("TOOL:"):
                    tool_name = line.split("TOOL:")[1].strip()
                elif line.startswith("ARGS:"):
                    try:
                        args = json.loads(line.split("ARGS:")[1].strip())
                    except Exception as e:
                        print(f"❌ Error decoding JSON: {e}")
                        continue

            if not tool_name or not args:
                print("❌ Could not parse tool name/arguments. Try asking differently.")
                continue

            # 3. Call the MCP tool
            response = await self.call_mcp_tool(tool_name, args)
            print(f"\n🗣️ Assistant: {response}\n")

async def main():
    client = ForcesMCPClient()
    await client.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())
