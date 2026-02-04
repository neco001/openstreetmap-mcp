from typing import Dict, Any, List
from mcp.server.fastmcp import Context
from osm_mcp_server.instance import mcp

@mcp.tool()
async def find_nearby_places(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: float = 1000,  # meters
    categories: List[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Discover points of interest and amenities near a specific location.
    
    This tool performs a comprehensive search around a geographic point to identify
    nearby establishments, amenities, and points of interest. Results are organized by
    category and subcategory, making it easy to find specific types of places. Essential
    for location-based recommendations, neighborhood analysis, and proximity-based decision making.
    
    Args:
        latitude: Center point latitude (decimal degrees)
        longitude: Center point longitude (decimal degrees)
        radius: Search radius in meters (defaults to 1000m/1km)
        categories: List of OSM categories to search for (e.g., ["amenity", "shop", "tourism"]).
                   If omitted, searches common categories.
        limit: Maximum number of total results to return
        
    Returns:
        Structured dictionary containing:
        - Original query parameters
        - Total count of places found
        - Results grouped by category and subcategory
        - Each place includes name, coordinates, and associated tags
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    # Set default categories if not provided
    if not categories:
        categories = ["amenity", "shop", "tourism", "leisure"]
    
    ctx.info(f"Searching for places within {radius}m of ({latitude}, {longitude})")
    places = await osm_client.get_nearby_pois(latitude, longitude, radius, categories)
    
    # Group results by category
    results_by_category = {}
    
    for place in places[:limit]:
        tags = place.get("tags", {})
        
        # Find the matching category
        for category in categories:
            if category in tags:
                subcategory = tags[category]
                if category not in results_by_category:
                    results_by_category[category] = {}
                
                if subcategory not in results_by_category[category]:
                    results_by_category[category][subcategory] = []
                
                # Add place to appropriate category and subcategory
                place_info = {
                    "id": place.get("id"),
                    "name": tags.get("name", "Unnamed"),
                    "latitude": place.get("lat"),
                    "longitude": place.get("lon"),
                    "tags": tags
                }
                
                results_by_category[category][subcategory].append(place_info)
    
    # Calculate total count
    total_count = sum(
        len(places)
        for category_data in results_by_category.values()
        for places in category_data.values()
    )
    
    return {
        "query": {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius
        },
        "categories": results_by_category,
        "total_count": total_count
    }

@mcp.tool()
async def search_category(
    category: str,
    min_latitude: float,
    min_longitude: float,
    max_latitude: float,
    max_longitude: float,
    ctx: Context,
    subcategories: List[str] = None
) -> Dict[str, Any]:
    """
    Search for specific types of places within a defined geographic area.
    
    This tool allows targeted searches for places matching specific categories within
    a rectangular geographic region. It's particularly useful for filtering places by type
    (restaurants, schools, parks, etc.) within a neighborhood or city district. Results include
    complete location details and metadata about each matching place.
    
    Args:
        category: Main OSM category to search for (e.g., "amenity", "shop", "tourism", "building")
        min_latitude: Southern boundary of search area (decimal degrees)
        min_longitude: Western boundary of search area (decimal degrees)
        max_latitude: Northern boundary of search area (decimal degrees)
        max_longitude: Eastern boundary of search area (decimal degrees)
        subcategories: Optional list of specific subcategories to filter by (e.g., ["restaurant", "cafe"])
        
    Returns:
        Structured results including:
        - Query parameters
        - Count of matching places
        - List of matching places with coordinates, names, and metadata
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    bbox = (min_longitude, min_latitude, max_longitude, max_latitude)
    
    ctx.info(f"Searching for {category} in bounding box")
    features = await osm_client.search_features_by_category(bbox, category, subcategories)
    
    # Process results
    results = []
    for feature in features:
        tags = feature.get("tags", {})
        
        # Get coordinates based on feature type
        coords = {}
        if feature.get("type") == "node":
            coords = {
                "latitude": feature.get("lat"),
                "longitude": feature.get("lon")
            }
        # For ways and relations, use center coordinates if available
        elif "center" in feature:
            coords = {
                "latitude": feature.get("center", {}).get("lat"),
                "longitude": feature.get("center", {}).get("lon")
            }
        
        # Only include features with valid coordinates
        if coords:
            results.append({
                "id": feature.get("id"),
                "type": feature.get("type"),
                "name": tags.get("name", "Unnamed"),
                "coordinates": coords,
                "category": category,
                "subcategory": tags.get(category),
                "tags": tags
            })
    
    return {
        "query": {
            "category": category,
            "subcategories": subcategories,
            "bbox": {
                "min_latitude": min_latitude,
                "min_longitude": min_longitude,
                "max_latitude": max_latitude,
                "max_longitude": max_longitude
            }
        },
        "results": results,
        "count": len(results)
    }
