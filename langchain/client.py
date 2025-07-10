import asyncio
from langchain_ollama.chat_models import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

async def interactive_chat(agent, system_message):
    print("\n" + "="*70)
    print("🤖 Newton Forces Assistant ready!")
    print("Ask about vectors, diagrams, forces, conversions, SI, or math.")
    print("Type 'quit' to exit.")
    print("="*70 + "\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q', 'bye']:
                print("👋 Goodbye!")
                break
            if not user_input:
                continue
            print("🤖 Thinking...")
            response = await agent.ainvoke({
                "messages": [
                    SystemMessage(content=system_message),
                    ("human", user_input)
                ]
            }, config={"recursion_limit": 8})
            print(f"\nAssistant: {response['messages'][-1].content}\n")
            print("-" * 50)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")

async def main():
    client = MultiServerMCPClient({
        "conversions": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/jakubpierog/Documents/newton_forces_mcp/conversions",
                "run", "conversions.py"
            ],
            "transport": "stdio",
        },
        "forces": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/jakubpierog/Documents/newton_forces_mcp/forces",
                "run", "forces.py"
            ],
            "transport": "stdio",
        },
        "diagram": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/jakubpierog/Documents/newton_forces_mcp/diagram",
                "run", "diagram.py"
            ],
            "transport": "stdio",
        },
        "math": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/jakubpierog/Documents/newton_forces_mcp/math",
                "run", "math_server.py"
            ],
            "transport": "stdio",
        },
        "vectors": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/jakubpierog/Documents/newton_forces_mcp/vectors",
                "run", "vectors.py"
            ],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()
    print(f"🔧 Connected to {len(tools)} MCP tools:")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")
    print()

    llm = ChatOllama(
        model="llama3.2",  # or your Ollama model name
        temperature=0,
    )

    system_message = """
You are a Newtonian physics assistant with access to these tools:
- conversions: units conversion, SI breakdowns, smart force, simplify expressions
- forces: weight, friction, tension, net force, normal, force breakdowns, applied force
- diagram: draw free body diagrams, net force, smart diagrams
- math_server: evaluate and simplify math or physics expressions (with or without units)
- vectors: add/subtract vectors, convert between components and polar

**INSTRUCTIONS:**
- Use the correct tool for the user's question—you have all tools available.
- For vector math, use 'vectors'.
- For diagrams, use 'diagram'.
- For force calculations, use 'forces'.
- For unit conversion, SI, or smart force, use 'conversions'.
- For evaluating/simplifying math, use 'math_server'.
- Always respond in natural, clear English and explain units or conversions if you perform them.
- Show all calculations and units in your response.

Examples:
- "Add [3,4] N and [0,5] N" → Use vectors/add_vectors
- "Convert 2500g to kg, then calculate the weight." → Use conversions/convert_units then forces/weight
- "Draw a free body diagram for a block on a table." → Use diagram/free_body
- "What is (5 N * 2 m) / (10 s) in SI base units?" → Use math_server/evaluate and math_server/simplify_units
"""

    agent = create_react_agent(llm, tools)
    print("🚀 Starting Multi-MCP Newton Forces Assistant...")
    await interactive_chat(agent, system_message)

if __name__ == "__main__":
    asyncio.run(main())


