import math
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("vectors")

def from_magnitude_angle(magnitude: float, angle_deg: float) -> List[float]:
    """Convert magnitude/angle (deg) to x/y components."""
    angle_rad = math.radians(angle_deg)
    x = magnitude * math.cos(angle_rad)
    y = magnitude * math.sin(angle_rad)
    return [x, y]

def to_magnitude_angle(x: float, y: float) -> Dict[str, float]:
    """Convert x/y components to magnitude and angle (deg from x axis, CCW)."""
    magnitude = math.hypot(x, y)
    angle = math.degrees(math.atan2(y, x))
    if angle < 0:
        angle += 360  # Always report angle as 0-360
    return {"magnitude": magnitude, "angle_deg": angle}

def vector_display(components: List[float]) -> str:
    mag_angle = to_magnitude_angle(components[0], components[1])
    return (
        f"Components: ({components[0]:.2f} N, {components[1]:.2f} N)\n"
        f"Magnitude: {mag_angle['magnitude']:.2f} N\n"
        f"Direction: {mag_angle['angle_deg']:.2f}° CCW from +x axis"
    )

@mcp.tool(description="Add two force vectors. Each can be given as components (x, y) in Newtons, or as {'magnitude': value, 'angle_deg': value} with angle in degrees (CCW from x).")
async def add_vectors(vector1: Any, vector2: Any) -> str:
    v1 = vector1
    v2 = vector2
    # Convert to [x, y] if given as magnitude/angle
    if isinstance(v1, dict) and 'magnitude' in v1 and 'angle_deg' in v1:
        v1 = from_magnitude_angle(v1['magnitude'], v1['angle_deg'])
    if isinstance(v2, dict) and 'magnitude' in v2 and 'angle_deg' in v2:
        v2 = from_magnitude_angle(v2['magnitude'], v2['angle_deg'])
    if not (isinstance(v1, list) and isinstance(v2, list) and len(v1) == 2 and len(v2) == 2):
        return "Error: Each vector must be components [x, y] (in N), or dict with 'magnitude' and 'angle_deg'."
    result = [v1[0] + v2[0], v1[1] + v2[1]]
    return f"Sum of vectors:\n{vector_display(result)}"

@mcp.tool(description="Subtract vector2 from vector1. Each can be given as components (x, y) in Newtons, or as {'magnitude': value, 'angle_deg': value} with angle in degrees (CCW from x).")
async def subtract_vectors(vector1: Any, vector2: Any) -> str:
    v1 = vector1
    v2 = vector2
    # Convert to [x, y] if given as magnitude/angle
    if isinstance(v1, dict) and 'magnitude' in v1 and 'angle_deg' in v1:
        v1 = from_magnitude_angle(v1['magnitude'], v1['angle_deg'])
    if isinstance(v2, dict) and 'magnitude' in v2 and 'angle_deg' in v2:
        v2 = from_magnitude_angle(v2['magnitude'], v2['angle_deg'])
    if not (isinstance(v1, list) and isinstance(v2, list) and len(v1) == 2 and len(v2) == 2):
        return "Error: Each vector must be components [x, y] (in N), or dict with 'magnitude' and 'angle_deg'."
    result = [v1[0] - v2[0], v1[1] - v2[1]]
    return f"Difference of vectors:\n{vector_display(result)}"

@mcp.tool(description="Convert a force vector from magnitude/angle (deg) to x/y components (in N).")
async def to_components(magnitude: float, angle_deg: float) -> str:
    comp = from_magnitude_angle(magnitude, angle_deg)
    return f"Components: ({comp[0]:.2f} N, {comp[1]:.2f} N)"

@mcp.tool(description="Convert a force vector from components (x, y) in N to magnitude and angle (degrees, CCW from x axis).")
async def to_polar(x: float, y: float) -> str:
    mag_angle = to_magnitude_angle(x, y)
    return (
        f"Magnitude: {mag_angle['magnitude']:.2f} N\n"
        f"Direction: {mag_angle['angle_deg']:.2f}° CCW from +x axis"
    )

if __name__ == "__main__":
    mcp.run(transport="stdio")
