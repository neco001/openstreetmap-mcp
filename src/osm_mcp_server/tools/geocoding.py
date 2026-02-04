from typing import List, Dict
from mcp.server.fastmcp import Context
from osm_mcp_server.instance import mcp

@mcp.tool()
async def geocode_address(address: str, ctx: Context) -> List[Dict]:
    """
    Convert an address or place name to geographic coordinates with detailed location information.
    
    This tool takes a text description of a location (such as an address, landmark name, or
    place of interest) and returns its precise geographic coordinates along with rich metadata.
    The results can be used for mapping, navigation, location-based analysis, and as input to
    other geospatial tools.
    
    Args:
        address: The address, place name, landmark, or description to geocode (e.g., "Empire State Building", 
                "123 Main St, Springfield", "Golden Gate Park, San Francisco")
        
    Returns:
        List of matching locations with:
        - Geographic coordinates (latitude/longitude)
        - Formatted address
        - Administrative boundaries (city, state, country)
        - OSM type and ID
        - Bounding box (if applicable)
        - Importance ranking
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    results = await osm_client.geocode(address)
    
    # Enhance results with additional context
    for result in results:
        if "lat" in result and "lon" in result:
            result["coordinates"] = {
                "latitude": float(result["lat"]),
                "longitude": float(result["lon"])
            }
    
    return results

@mcp.tool()
async def reverse_geocode(latitude: float, longitude: float, ctx: Context) -> Dict:
    """
    Convert geographic coordinates to a detailed address and location description.
    
    This tool takes a specific point on Earth (latitude and longitude) and returns 
    comprehensive information about that location, including its address, nearby landmarks,
    administrative boundaries, and other contextual information. Useful for translating
    GPS coordinates into human-readable locations.
    
    Args:
        latitude: The latitude coordinate (decimal degrees, WGS84)
        longitude: The longitude coordinate (decimal degrees, WGS84)
        
    Returns:
        Detailed address and location information including:
        - Formatted address
        - Building, street, city, state, country
        - Administrative hierarchy
        - OSM metadata
        - Postal code and other relevant identifiers
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    return await osm_client.reverse_geocode(latitude, longitude)
