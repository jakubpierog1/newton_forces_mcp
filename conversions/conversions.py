import pint
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("conversions")
ureg = pint.UnitRegistry()

@mcp.tool(description="Convert a value with units to another unit. Example: 100 grams to kilograms, or 15 cm to meters.")
async def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    try:
        qty = value * ureg(from_unit)
        converted = qty.to(to_unit)
        return f"{value} {from_unit} = {converted.magnitude:.6g} {to_unit}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool(description="Simplify or break down a unit into base SI units (e.g., N to kg·m/s^2).")
async def simplify_unit(unit_expr: str) -> str:
    try:
        unit = ureg(unit_expr)
        base = unit.to_base_units()
        return f"{unit_expr} = {base:~}"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool(description="Smart physics conversion: e.g., if you want force from mass in grams and acceleration in m/s², will handle conversions and calculate the result.")
async def smart_force(mass_value: float, mass_unit: str, accel_value: float, accel_unit: str = "meter/second**2") -> str:
    try:
        mass = (mass_value * ureg(mass_unit)).to("kilogram")
        accel = (accel_value * ureg(accel_unit)).to("meter/second**2")
        force = mass * accel
        # Also show in base units
        base = force.to_base_units()
        return f"Force = {mass.magnitude:.4g} kg × {accel.magnitude:.4g} m/s² = {force.magnitude:.4g} N\n(Simplified: {base:~})"
    except Exception as e:
        return f"Error: {e}"

@mcp.tool(description="Cancel or simplify units in an expression, e.g., simplify (kg*m/s^2)/(N) or (g/cm^3) to SI units.")
async def simplify_expression(expr: str) -> str:
    try:
        qty = ureg.parse_expression(expr)
        base = qty.to_base_units()
        return f"{expr} = {base:~}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
