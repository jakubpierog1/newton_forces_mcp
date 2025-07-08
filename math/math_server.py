import sympy as sp
import pint
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("math_server")
ureg = pint.UnitRegistry()

def evaluate_expression(expr: str) -> str:
    try:
        # Try evaluating with pint first (handles units)
        result = ureg.parse_expression(expr)
        base = result.to_base_units()
        return f"{expr} = {result:~} = {base:~}"
    except Exception as pint_exc:
        try:
            # Try sympy (symbolic, no units)
            val = sp.sympify(expr)
            return f"{expr} = {sp.simplify(val)}"
        except Exception as sympy_exc:
            return f"Error: Could not evaluate expression. (Pint: {pint_exc}; SymPy: {sympy_exc})"

@mcp.tool(description="Evaluate math expressions, with or without units. Example: '5N * 8kg', 'sqrt(16)', '(3/4) * (2/5)', or complex expressions with units.")
async def evaluate(expr: str) -> str:
    return evaluate_expression(expr)

@mcp.tool(description="Convert an answer to a different unit. Example: '2000 g' to 'kg', or '40 m kg2 / s2' to 'N'.")
async def convert_answer(expr: str, to_unit: str) -> str:
    try:
        qty = ureg.parse_expression(expr)
        converted = qty.to(to_unit)
        return f"{expr} = {converted.magnitude:.6g} {to_unit}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool(description="Simplify units in an expression, expressing them in SI base units.")
async def simplify_units(expr: str) -> str:
    try:
        qty = ureg.parse_expression(expr)
        base = qty.to_base_units()
        return f"{expr} = {base:~}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
