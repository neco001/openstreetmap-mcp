from typing import Dict, Any, List
import math
import aiohttp
from mcp.server.fastmcp import Context
from osm_mcp_server.instance import mcp  # Changed from ..instance based on user feedback/runtime context
from osm_mcp_server.utils import haversine

# Note: These are extra tools that are not imported by default in server.py
# To enable them, import this module in server.py

@mcp.tool()
async def find_schools_nearby(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: float = 2000,
    education_levels: List[str] = None
) -> Dict[str, Any]:
    """
    Locate educational institutions near a specific location, filtered by education level.
    
    This specialized search tool identifies schools, colleges, and other educational institutions
    within a specified distance from a location. Results can be filtered by education level
    (elementary, middle, high school, university, etc.). Essential for families evaluating
    neighborhoods or real estate purchases with education considerations.
    
    Args:
        latitude: Center point latitude (decimal degrees)
        longitude: Center point longitude (decimal degrees)
        radius: Search radius in meters (defaults to 2000m/2km)
        education_levels: Optional list of specific education levels to filter by
                         (e.g., ["elementary", "secondary", "university"])
        
    Returns:
        List of educational institutions with:
        - Name and type
        - Distance from search point
        - Education levels offered
        - Contact information if available
        - Other relevant metadata
    """
    # Convert radius to bounding box (approximate)
    lat_delta = radius / 111000
    lon_delta = radius / (111000 * math.cos(math.radians(latitude)))
    
    bbox = (
        longitude - lon_delta,
        latitude - lat_delta,
        longitude + lon_delta,
        latitude + lat_delta
    )
    
    # Build Overpass query for educational institutions
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Create query for amenity=school and other education-related tags
    education_filters = [
        'node["amenity"="school"]({{bbox}});',
        'way["amenity"="school"]({{bbox}});',
        'node["amenity"="university"]({{bbox}});',
        'way["amenity"="university"]({{bbox}});',
        'node["amenity"="kindergarten"]({{bbox}});',
        'way["amenity"="kindergarten"]({{bbox}});',
        'node["amenity"="college"]({{bbox}});',
        'way["amenity"="college"]({{bbox}});'
    ]
    
    query = f"""
    [out:json];
    (
        {" ".join(education_filters)}
    );
    out body;
    """
    
    query = query.replace("{bbox}", f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(overpass_url, data={"data": query}) as response:
            if response.status == 200:
                data = await response.json()
                schools = data.get("elements", [])
            else:
                raise Exception(f"Failed to find schools: {response.status}")
    
    # Process and filter results
    results = []
    for school in schools:
        tags = school.get("tags", {})
        school_type = tags.get("school", "")
        
        # Filter by education level if specified
        if education_levels and school_type and school_type not in education_levels:
            continue
        
        # Get coordinates based on feature type
        coords = {}
        if school.get("type") == "node":
            coords = {
                "latitude": school.get("lat"),
                "longitude": school.get("lon")
            }
        elif "center" in school:
            coords = {
                "latitude": school.get("center", {}).get("lat"),
                "longitude": school.get("center", {}).get("lon")
            }
        
        # Skip if no valid coordinates
        if not coords:
            continue
        
        distance = haversine(latitude, longitude, coords["latitude"], coords["longitude"])
        
        results.append({
            "id": school.get("id"),
            "name": tags.get("name", "Unnamed School"),
            "amenity_type": tags.get("amenity", ""),
            "school_type": school_type,
            "education_level": tags.get("isced", ""),
            "coordinates": coords,
            "distance": round(distance, 1),
            "address": {
                "street": tags.get("addr:street", ""),
                "housenumber": tags.get("addr:housenumber", ""),
                "city": tags.get("addr:city", ""),
                "postcode": tags.get("addr:postcode", "")
            },
            "tags": tags
        })
    
    # Sort by distance
    results.sort(key=lambda x: x["distance"])
    
    return {
        "query": {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "education_levels": education_levels
        },
        "schools": results,
        "count": len(results)
    }

@mcp.tool()
async def find_ev_charging_stations(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: float = 5000,
    connector_types: List[str] = None,
    min_power: float = None
) -> Dict[str, Any]:
    """
    Locate electric vehicle charging stations near a specific location.
    
    This specialized search tool identifies EV charging infrastructure within a specified
    distance from a location. Results can be filtered by connector type (Tesla, CCS, CHAdeMO, etc.)
    and minimum power delivery. Essential for EV owners planning trips or evaluating potential
    charging stops.
    
    Args:
        latitude: Center point latitude (decimal degrees)
        longitude: Center point longitude (decimal degrees)
        radius: Search radius in meters (defaults to 5000m/5km)
        connector_types: Optional list of specific connector types to filter by
                        (e.g., ["type2", "ccs", "tesla"])
        min_power: Minimum charging power in kW
        
    Returns:
        List of charging stations with:
        - Location name and operator
        - Available connector types
        - Charging speeds
        - Number of charging points
        - Access restrictions
        - Other relevant metadata
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    # Convert radius to bounding box
    lat_delta = radius / 111000
    lon_delta = radius / (111000 * math.cos(math.radians(latitude)))
    
    bbox = (
        longitude - lon_delta,
        latitude - lat_delta,
        longitude + lon_delta,
        latitude + lat_delta
    )
    
    # Build Overpass query for EV charging stations
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    query = f"""
    [out:json];
    (
        node["amenity"="charging_station"]({{bbox}});
        way["amenity"="charging_station"]({{bbox}});
    );
    out body;
    """
    
    query = query.replace("{bbox}", f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(overpass_url, data={"data": query}) as response:
            if response.status == 200:
                data = await response.json()
                stations = data.get("elements", [])
            else:
                raise Exception(f"Failed to find charging stations: {response.status}")
    
    # Process and filter results
    results = []
    for station in stations:
        tags = station.get("tags", {})
        
        # Get coordinates based on feature type
        coords = {}
        if station.get("type") == "node":
            coords = {
                "latitude": station.get("lat"),
                "longitude": station.get("lon")
            }
        elif "center" in station:
            coords = {
                "latitude": station.get("center", {}).get("lat"),
                "longitude": station.get("center", {}).get("lon")
            }
        
        # Skip if no valid coordinates
        if not coords:
            continue
        
        # Extract connector information
        connectors = []
        for key, value in tags.items():
            if key.startswith("socket:"):
                connector_type = key.split(":", 1)[1]
                connectors.append({
                    "type": connector_type,
                    "count": value if value.isdigit() else 1
                })
        
        # Filter by connector type if specified
        if connector_types:
            has_matching_connector = False
            for connector in connectors:
                if connector["type"] in connector_types:
                    has_matching_connector = True
                    break
            if not has_matching_connector:
                continue
        
        # Extract power information
        power = None
        if "maxpower" in tags:
            try:
                power = float(tags["maxpower"])
            except ValueError:
                pass
        
        # Filter by minimum power if specified
        if min_power is not None and (power is None or power < min_power):
            continue
        
        distance = haversine(latitude, longitude, coords["latitude"], coords["longitude"])
        
        results.append({
            "id": station.get("id"),
            "name": tags.get("name", "Unnamed Charging Station"),
            "operator": tags.get("operator", "Unknown"),
            "coordinates": coords,
            "distance": round(distance, 1),
            "connectors": connectors,
            "capacity": tags.get("capacity", "Unknown"),
            "power": power,
            "fee": tags.get("fee", "Unknown"),
            "access": tags.get("access", "public"),
            "opening_hours": tags.get("opening_hours", "Unknown"),
            "address": {
                "street": tags.get("addr:street", ""),
                "housenumber": tags.get("addr:housenumber", ""),
                "city": tags.get("addr:city", ""),
                "postcode": tags.get("addr:postcode", "")
            },
            "tags": tags
        })
    
    # Sort by distance
    results.sort(key=lambda x: x["distance"])
    
    return {
        "query": {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "connector_types": connector_types,
            "min_power": min_power
        },
        "stations": results,
        "count": len(results)
    }

@mcp.tool()
async def find_parking_facilities(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: float = 1000,
    parking_type: str = None  # e.g., "surface", "underground", "multi-storey"
) -> Dict[str, Any]:
    """
    Locate parking facilities near a specific location.
    
    This tool finds parking options (lots, garages, street parking) near a specified location.
    Results can be filtered by parking type and include capacity information where available.
    Useful for trip planning, city navigation, and evaluating parking availability in urban areas.
    
    Args:
        latitude: Center point latitude (decimal degrees)
        longitude: Center point longitude (decimal degrees)
        radius: Search radius in meters (defaults to 1000m/1km)
        parking_type: Optional filter for specific types of parking facilities
                     ("surface", "underground", "multi-storey", etc.)
        
    Returns:
        List of parking facilities with:
        - Name and type
        - Capacity information if available
        - Fee structure if available
        - Access restrictions
        - Distance from search point
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    # Convert radius to bounding box
    lat_delta = radius / 111000
    lon_delta = radius / (111000 * math.cos(math.radians(latitude)))
    
    bbox = (
        longitude - lon_delta,
        latitude - lat_delta,
        longitude + lon_delta,
        latitude + lat_delta
    )
    
    # Build Overpass query for parking facilities
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    query = f"""
    [out:json];
    (
        node["amenity"="parking"]({{bbox}});
        way["amenity"="parking"]({{bbox}});
        relation["amenity"="parking"]({{bbox}});
    );
    out body;
    """
    
    query = query.replace("{bbox}", f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(overpass_url, data={"data": query}) as response:
            if response.status == 200:
                data = await response.json()
                parking_facilities = data.get("elements", [])
            else:
                raise Exception(f"Failed to find parking facilities: {response.status}")
    
    # Process and filter results
    results = []
    for facility in parking_facilities:
        tags = facility.get("tags", {})
        
        # Filter by parking type if specified
        if parking_type and tags.get("parking", "") != parking_type:
            continue
        
        # Get coordinates based on feature type
        coords = {}
        if facility.get("type") == "node":
            coords = {
                "latitude": facility.get("lat"),
                "longitude": facility.get("lon")
            }
        elif "center" in facility:
            coords = {
                "latitude": facility.get("center", {}).get("lat"),
                "longitude": facility.get("center", {}).get("lon")
            }
        
        # Skip if no valid coordinates
        if not coords:
            continue
        
        distance = haversine(latitude, longitude, coords["latitude"], coords["longitude"])
        
        results.append({
            "id": facility.get("id"),
            "name": tags.get("name", "Unnamed Parking"),
            "type": tags.get("parking", "surface"),
            "coordinates": coords,
            "distance": round(distance, 1),
            "capacity": tags.get("capacity", "Unknown"),
            "fee": tags.get("fee", "Unknown"),
            "access": tags.get("access", "public"),
            "opening_hours": tags.get("opening_hours", "Unknown"),
            "levels": tags.get("levels", "1"),
            "address": {
                "street": tags.get("addr:street", ""),
                "housenumber": tags.get("addr:housenumber", ""),
                "city": tags.get("addr:city", ""),
                "postcode": tags.get("addr:postcode", "")
            },
            "tags": tags
        })
    
    # Sort by distance
    results.sort(key=lambda x: x["distance"])
    
    return {
        "query": {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "parking_type": parking_type
        },
        "parking_facilities": results,
        "count": len(results)
    }

@mcp.tool()
async def suggest_meeting_point(
    locations: List[Dict[str, float]],
    ctx: Context,
    venue_type: str = "cafe"
) -> Dict[str, Any]:
    """
    Find the optimal meeting place for multiple people coming from different locations.
    
    This tool calculates a central meeting point based on the locations of multiple individuals,
    then recommends suitable venues near that central point. Ideal for planning social gatherings,
    business meetings, or any situation where multiple people need to converge from different
    starting points.
    
    Args:
        locations: List of dictionaries, each containing the latitude and longitude of a person's location
                  Example: [{"latitude": 37.7749, "longitude": -122.4194}, {"latitude": 37.3352, "longitude": -121.8811}]
        venue_type: Type of venue to suggest as a meeting point. Options include:
                   "cafe", "restaurant", "bar", "library", "park", etc.
        
    Returns:
        Meeting point recommendations including:
        - Calculated center point coordinates
        - List of suggested venues with names and details
        - Total number of matching venues in the area
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    if len(locations) < 2:
        raise ValueError("Need at least two locations to suggest a meeting point")
    
    # Calculate the center point (simple average)
    avg_lat = sum(loc.get("latitude", 0) for loc in locations) / len(locations)
    avg_lon = sum(loc.get("longitude", 0) for loc in locations) / len(locations)
    
    ctx.info(f"Calculating center point for {len(locations)} locations: ({avg_lat}, {avg_lon})")
    
    # Search for venues around this center point
    venues = await osm_client.get_nearby_pois(
        avg_lat, avg_lon, 
        radius=500,  # Search within 500m of center
        categories=["amenity"]
    )
    
    # Filter venues by type
    matching_venues = []
    for venue in venues:
        tags = venue.get("tags", {})
        if tags.get("amenity") == venue_type:
            matching_venues.append({
                "id": venue.get("id"),
                "name": tags.get("name", "Unnamed Venue"),
                "latitude": venue.get("lat"),
                "longitude": venue.get("lon"),
                "tags": tags
            })
    
    # If no venues found, expand search
    if not matching_venues:
        ctx.info(f"No {venue_type} found within 500m, expanding search to 1000m")
        venues = await osm_client.get_nearby_pois(
            avg_lat, avg_lon, 
            radius=1000,
            categories=["amenity"]
        )
        
        for venue in venues:
            tags = venue.get("tags", {})
            if tags.get("amenity") == venue_type:
                matching_venues.append({
                    "id": venue.get("id"),
                    "name": tags.get("name", "Unnamed Venue"),
                    "latitude": venue.get("lat"),
                    "longitude": venue.get("lon"),
                    "tags": tags
                })
    
    # Return the result
    return {
        "center_point": {
            "latitude": avg_lat,
            "longitude": avg_lon
        },
        "suggested_venues": matching_venues[:5],  # Top 5 venues
        "venue_type": venue_type,
        "total_options": len(matching_venues)
    }
