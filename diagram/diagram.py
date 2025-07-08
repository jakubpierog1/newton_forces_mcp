import math
import sympy as sp
import pint
import svgwrite
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("diagram")
ureg = pint.UnitRegistry()

def parse_vector(vec: Any) -> List[float]:
    # Accepts: [x, y], {"magnitude": m, "angle_deg": a}, or "F=3N at 30 deg"
    if isinstance(vec, dict) and "magnitude" in vec and "angle_deg" in vec:
        angle_rad = math.radians(vec["angle_deg"])
        x = vec["magnitude"] * math.cos(angle_rad)
        y = vec["magnitude"] * math.sin(angle_rad)
        return [x, y]
    elif isinstance(vec, list) and len(vec) == 2:
        return [float(vec[0]), float(vec[1])]
    elif isinstance(vec, str):
        try:
            if "at" in vec:
                mag = float(vec.split("=")[1].split()[0])
                angle = float(vec.split("at")[1].split()[0])
                angle_rad = math.radians(angle)
                x = mag * math.cos(angle_rad)
                y = mag * math.sin(angle_rad)
                return [x, y]
        except Exception:
            pass
    return [0.0, 0.0]

def vector_label(vec: List[float], name: str = "", unit: str = "N") -> str:
    mag = math.hypot(vec[0], vec[1])
    angle = (math.degrees(math.atan2(vec[1], vec[0])) + 360) % 360
    return f"{name} ({mag:.2f} {unit} @ {angle:.1f}°)"

def draw_free_body(forces: List[Dict[str, Any]], object_name: str = "Body") -> str:
    dwg = svgwrite.Drawing(size=(400, 400))
    center = (200, 200)
    dwg.add(dwg.circle(center=center, r=20, fill="lightgrey", stroke="black", stroke_width=2))
    dwg.add(dwg.text(object_name, insert=(center[0] - 22, center[1] + 45), font_size="16px", fill="black"))

    color_cycle = ["red", "blue", "green", "purple", "orange", "brown", "darkcyan"]

    # Define the arrowhead marker ONCE and add it to defs
    arrow_marker = dwg.marker(insert=(10, 5), size=(10, 10), orient="auto", id="arrow")
    arrow_marker.add(dwg.polygon(points=[(0, 0), (10, 5), (0, 10)], fill="black"))
    dwg.defs.add(arrow_marker)

    for idx, force in enumerate(forces):
        vec = parse_vector(force["vector"])
        mag = math.hypot(vec[0], vec[1])
        angle = math.atan2(vec[1], vec[0])
        length = max(30, mag * 30)
        x2 = center[0] + length * math.cos(angle)
        y2 = center[1] - length * math.sin(angle)  # SVG y-axis is down
        color = color_cycle[idx % len(color_cycle)]

        # Draw the force arrow using the marker (FIXED!)
        dwg.add(
            dwg.line(
                start=center,
                end=(x2, y2),
                stroke=color,
                stroke_width=4,
                marker_end=arrow_marker.get_funciri()
            )
        )

        # Label the arrow
        label = force.get("label", vector_label(vec))
        label_x = (center[0] + x2) / 2 + 10
        label_y = (center[1] + y2) / 2 - 10
        dwg.add(dwg.text(label, insert=(label_x, label_y), font_size="12px", fill=color))

    return dwg.tostring()

@mcp.tool(description="Create a free body diagram (SVG) given a list of forces. Each force: {label, vector: [x, y] or {'magnitude': m, 'angle_deg': a}}.")
async def free_body(forces: List[Dict[str, Any]], object_name: str = "Body") -> str:
    svg = draw_free_body(forces, object_name)
    return svg

@mcp.tool(description="Given a list of force vectors, compute the net force (sum), with magnitude and direction (degrees).")
async def net_force(forces: List[Any]) -> str:
    net_x, net_y = 0, 0
    for f in forces:
        x, y = parse_vector(f)
        net_x += x
        net_y += y
    mag = math.hypot(net_x, net_y)
    angle = (math.degrees(math.atan2(net_y, net_x)) + 360) % 360
    return f"Net force: {mag:.2f} N at {angle:.1f}° (from +x axis, CCW)\nComponents: ({net_x:.2f} N, {net_y:.2f} N)"

@mcp.tool(description="Given math/physics equations or raw numbers for forces, compute magnitudes, directions, and create a free body diagram.")
async def smart_diagram(forces: List[Any], object_name: str = "Body") -> str:
    force_dicts = []
    for idx, f in enumerate(forces):
        if isinstance(f, dict) and "label" in f and "vector" in f:
            force_dicts.append(f)
        elif isinstance(f, dict) and "magnitude" in f and "angle_deg" in f:
            force_dicts.append({"label": f"F{idx+1}", "vector": f})
        elif isinstance(f, list) and len(f) == 2:
            force_dicts.append({"label": f"F{idx+1}", "vector": f})
        elif isinstance(f, str):
            try:
                mag = float(sp.sympify(f))
                force_dicts.append({"label": f"F{idx+1}", "vector": [mag, 0]})
            except Exception:
                pass
    svg = draw_free_body(force_dicts, object_name)
    return svg

if __name__ == "__main__":
    mcp.run(transport="stdio")
