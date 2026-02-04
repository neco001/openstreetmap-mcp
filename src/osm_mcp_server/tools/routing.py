from typing import Dict, Any, List
from mcp.server.fastmcp import Context
from osm_mcp_server.instance import mcp

@mcp.tool()
async def get_route_directions(
    from_latitude: float,
    from_longitude: float,
    to_latitude: float,
    to_longitude: float,
    ctx: Context,
    mode: str = "car",
    steps: bool = False,
    overview: str = "simplified",
    annotations: bool = False
) -> Dict[str, Any]:
    """
    Calculate detailed route directions between two geographic points.
    
    This tool provides comprehensive routing information between two locations using OpenStreetMap/OSRM.
    The output can be minimized using the steps, overview, and annotations parameters to reduce the response size.
    
    Args:
        from_latitude: Starting point latitude (decimal degrees)
        from_longitude: Starting point longitude (decimal degrees)
        to_latitude: Destination latitude (decimal degrees)
        to_longitude: Destination longitude (decimal degrees)
        ctx: Context (provided internally by MCP)
        mode: Transportation mode ("car", "bike", "foot")
        steps: Turn-by-turn instructions (True/False, Default: False)
        overview: Geometry output ("full", "simplified", "false"; Default: "simplified")
        annotations: Additional segment info (True/False, Default: False)
    
    Returns:
        Dictionary with routing information (summary, directions, geometry, waypoints)

    Example:
        {
          "from_latitude": 51.3334193,
          "from_longitude": 9.4540423,
          "to_latitude": 51.3295516,
          "to_longitude": 9.4576721,
          "mode": "car",
          "steps": false,
          "overview": "simplified",
          "annotations": false
        }
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    # Validate transportation mode
    valid_modes = ["car", "bike", "foot"]
    if mode not in valid_modes:
        ctx.warning(f"Invalid mode '{mode}'. Using 'car' instead.")
        mode = "car"
    
    ctx.info(f"Calculating {mode} route from ({from_latitude}, {from_longitude}) to ({to_latitude}, {to_longitude})")
    
    # Get route from OSRM
    route_data = await osm_client.get_route(
        from_latitude, from_longitude,
        to_latitude, to_longitude,
        mode,
        steps=steps,
        overview=overview,
        annotations=annotations
    )
    
    # Process and simplify the response
    if "routes" in route_data and len(route_data["routes"]) > 0:
        route = route_data["routes"][0]
        
        # Extract turn-by-turn directions
        steps_list = []
        if "legs" in route:
            for leg in route["legs"]:
                for step in leg.get("steps", []):
                    steps_list.append({
                        "instruction": step.get("maneuver", {}).get("instruction", ""),
                        "distance": step.get("distance"),
                        "duration": step.get("duration"),
                        "name": step.get("name", "")
                    })
        
        return {
            "summary": {
                "distance": route.get("distance"),  # meters
                "duration": route.get("duration"),  # seconds
                "mode": mode
            },
            "directions": steps_list,
            "geometry": route.get("geometry"),
            "waypoints": route_data.get("waypoints", [])
        }
    else:
        raise Exception("No route found")

@mcp.tool()
async def analyze_commute(
    home_latitude: float,
    home_longitude: float,
    work_latitude: float,
    work_longitude: float,
    ctx: Context,
    modes: List[str] = ["car", "foot", "bike"],
    depart_at: str = None  # Time in HH:MM format, e.g. "08:30"
) -> Dict[str, Any]:
    """
    Perform a detailed commute analysis between home and work locations.
    
    This advanced tool analyzes commute options between two locations (typically home and work),
    comparing multiple transportation modes and providing detailed metrics for each option.
    Includes estimated travel times, distances, turn-by-turn directions, and other commute-relevant
    data. Essential for real estate decisions, lifestyle planning, and workplace relocation analysis.
    
    Args:
        home_latitude: Home location latitude (decimal degrees)
        home_longitude: Home location longitude (decimal degrees)
        work_latitude: Workplace location latitude (decimal degrees)
        work_longitude: Workplace location longitude (decimal degrees)
        modes: List of transportation modes to analyze (options: "car", "foot", "bike")
        depart_at: Optional departure time (format: "HH:MM") for time-sensitive routing
        
    Returns:
        Comprehensive commute analysis with:
        - Summary comparing all transportation modes
        - Detailed route information for each mode
        - Total distance and duration for each option
        - Turn-by-turn directions
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    # Get address information for both locations
    home_info = await osm_client.reverse_geocode(home_latitude, home_longitude)
    work_info = await osm_client.reverse_geocode(work_latitude, work_longitude)
    
    # Get commute information for each mode
    commute_options = []
    
    for mode in modes:
        ctx.info(f"Calculating {mode} route for commute analysis")
        
        # Get route from OSRM
        try:
            route_data = await osm_client.get_route(
                home_latitude, home_longitude,
                work_latitude, work_longitude,
                mode
            )
            
            if "routes" in route_data and len(route_data["routes"]) > 0:
                route = route_data["routes"][0]
                
                # Extract directions
                steps = []
                if "legs" in route:
                    for leg in route["legs"]:
                        for step in leg.get("steps", []):
                            steps.append({
                                "instruction": step.get("maneuver", {}).get("instruction", ""),
                                "distance": step.get("distance"),
                                "duration": step.get("duration"),
                                "name": step.get("name", "")
                            })
                
                commute_options.append({
                    "mode": mode,
                    "distance_km": round(route.get("distance", 0) / 1000, 2),
                    "duration_minutes": round(route.get("duration", 0) / 60, 1),
                    "directions": steps
                })
        except Exception as e:
            ctx.warning(f"Error getting {mode} route: {str(e)}")
            commute_options.append({
                "mode": mode,
                "error": str(e)
            })
    
    # Sort by duration (fastest first)
    commute_options.sort(key=lambda x: x.get("duration_minutes", float("inf")))
    
    return {
        "home": {
            "coordinates": {
                "latitude": home_latitude,
                "longitude": home_longitude
            },
            "address": home_info.get("display_name", "Unknown location")
        },
        "work": {
            "coordinates": {
                "latitude": work_latitude,
                "longitude": work_longitude
            },
            "address": work_info.get("display_name", "Unknown location")
        },
        "commute_options": commute_options,
        "fastest_option": commute_options[0]["mode"] if commute_options else None,
        "depart_at": depart_at
    }
