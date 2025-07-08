from typing import Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("forces")

GRAVITY = 9.8  # m/s^2

@mcp.tool()
def weight(mass_kg: float, gravity: float = GRAVITY) -> float:
    """Calculate weight force (N) as mass * gravity."""
    return mass_kg * gravity


@mcp.tool()
def friction(normal_force: float, coefficient: float) -> float:
    """Calculate friction force (N) as μ * normal force."""
    return normal_force * coefficient

@mcp.tool()
def applied_force(force: float) -> float:
    """Returns the applied force value (N)."""
    return force

@mcp.tool()
def tension(weight: float = None, mass: float = None, gravity: float = GRAVITY) -> float:
    """Calculate tension in a rope for a hanging mass (N)."""
    if weight is not None:
        return weight
    if mass is not None:
        return mass * gravity
    return 0.0

@mcp.tool()
def normal_force(mass: float, gravity: float = GRAVITY, incline_angle_deg: float = 0) -> float:
    """Calculate normal force (N). For flat surface, normal = weight. For incline, normal = mg*cos(theta)."""
    import math
    theta = math.radians(incline_angle_deg)
    return mass * gravity * (1 if incline_angle_deg == 0 else math.cos(theta))

@mcp.tool()
def net_force(forces: list[float]) -> float:
    """Calculate net force (N) as the sum of all forces (positive for right/up, negative for left/down)."""
    return sum(forces)

@mcp.tool()
def force_breakdown(situation: str) -> str:
    """Given a situation, describe the force relationships (e.g., 'In equilibrium, tension=weight')."""
    situation = situation.lower()
    if "hanging" in situation or "elevator" in situation:
        return "If at rest or moving at constant velocity, Tension = Weight = m * g"
    if "block on table" in situation:
        return "Normal force = Weight, Friction = μ * Normal force"
    return "Describe your situation with objects, surfaces, and directions for a breakdown."

if __name__ == "__main__":
    mcp.run(transport="stdio")
