from typing import Dict, Any
import math
import aiohttp
from datetime import datetime
from mcp.server.fastmcp import Context
from osm_mcp_server.instance import mcp
from osm_mcp_server.utils import haversine

@mcp.tool()
async def explore_area(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: float = 500
) -> Dict[str, Any]:
    """
    Generate a comprehensive profile of an area including all amenities and features.
    
    This powerful analysis tool creates a detailed overview of a neighborhood or area by
    identifying and categorizing all geographic features, amenities, and points of interest.
    Results are organized by category for easy analysis. Excellent for neighborhood research,
    area comparisons, and location-based decision making.
    
    Args:
        latitude: Center point latitude (decimal degrees)
        longitude: Center point longitude (decimal degrees)
        radius: Search radius in meters (defaults to 500m)
        
    Returns:
        In-depth area profile including:
        - Address and location context
        - Total feature count
        - Features organized by category and subcategory
        - Each feature includes name, coordinates, and detailed metadata
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    # Categories to search for
    categories = [
        "amenity", "shop", "tourism", "leisure", 
        "natural", "historic", "public_transport"
    ]
    
    results = {}
    for i, category in enumerate(categories):
        await ctx.report_progress(i, len(categories))
        ctx.info(f"Exploring {category} features...")
        
        try:
            # Convert radius to bounding box
            lat_delta = radius / 111000
            lon_delta = radius / (111000 * math.cos(math.radians(latitude)))
            
            bbox = (
                longitude - lon_delta,
                latitude - lat_delta,
                longitude + lon_delta,
                latitude + lat_delta
            )
            
            features = await osm_client.search_features_by_category(bbox, category)
            
            # Group by subcategory
            subcategories = {}
            for feature in features:
                tags = feature.get("tags", {})
                subcategory = tags.get(category)
                
                if subcategory:
                    if subcategory not in subcategories:
                        subcategories[subcategory] = []
                    
                    # Get coordinates based on feature type
                    coords = {}
                    if feature.get("type") == "node":
                        coords = {
                            "latitude": feature.get("lat"),
                            "longitude": feature.get("lon")
                        }
                    elif "center" in feature:
                        coords = {
                            "latitude": feature.get("center", {}).get("lat"),
                            "longitude": feature.get("center", {}).get("lon")
                        }
                    
                    subcategories[subcategory].append({
                        "id": feature.get("id"),
                        "name": tags.get("name", "Unnamed"),
                        "coordinates": coords,
                        "type": feature.get("type"),
                        "tags": tags
                    })
            
            results[category] = subcategories
            
        except Exception as e:
            ctx.warning(f"Error fetching {category} features: {str(e)}")
            results[category] = {}
    
    # Get address information for the center point
    try:
        address_info = await osm_client.reverse_geocode(latitude, longitude)
    except Exception:
        address_info = {"error": "Could not retrieve address information"}
    
    # Report completion
    await ctx.report_progress(len(categories), len(categories))
    
    # Count total features
    total_features = sum(
        len(places)
        for category_data in results.values()
        for places in category_data.values()
    )
    
    return {
        "query": {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius
        },
        "address": address_info,
        "categories": results,
        "total_features": total_features,
        "timestamp": datetime.now().isoformat()
    }

@mcp.tool()
async def analyze_neighborhood(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: float = 1000
) -> Dict[str, Any]:
    """
    Generate a comprehensive neighborhood analysis focused on livability factors.
    
    This advanced analysis tool evaluates a neighborhood based on multiple livability factors,
    including amenities, transportation options, green spaces, and services. Results include
    counts and proximity scores for various categories, helping to assess the overall quality
    and convenience of a residential area. Invaluable for real estate decisions, relocation
    planning, and neighborhood comparisons.
    
    Args:
        latitude: Center point latitude (decimal degrees)
        longitude: Center point longitude (decimal degrees)
        radius: Analysis radius in meters (defaults to 1000m/1km)
        
    Returns:
        Comprehensive neighborhood profile including:
        - Overall neighborhood score
        - Walkability assessment
        - Public transportation access
        - Nearby amenities (shops, restaurants, services)
        - Green spaces and recreation
        - Education and healthcare facilities
        - Detailed counts and distance metrics for each category
    """
    osm_client = ctx.request_context.lifespan_context.osm_client
    
    # Get address information for the center point
    address_info = await osm_client.reverse_geocode(latitude, longitude)
    
    # Categories to analyze for neighborhood quality
    categories = [
        # Essential services
        {"name": "groceries", "tags": ["shop=supermarket", "shop=convenience", "shop=grocery"]},
        {"name": "restaurants", "tags": ["amenity=restaurant", "amenity=cafe", "amenity=fast_food"]},
        {"name": "healthcare", "tags": ["amenity=hospital", "amenity=doctors", "amenity=pharmacy"]},
        {"name": "education", "tags": ["amenity=school", "amenity=kindergarten", "amenity=university"]},
        
        # Transportation
        {"name": "public_transport", "tags": ["public_transport=stop_position", "railway=station", "amenity=bus_station"]},
        
        # Recreation
        {"name": "parks", "tags": ["leisure=park", "leisure=garden", "leisure=playground"]},
        {"name": "sports", "tags": ["leisure=sports_centre", "leisure=fitness_centre", "leisure=swimming_pool"]},
        
        # Culture and entertainment
        {"name": "entertainment", "tags": ["amenity=theatre", "amenity=cinema", "amenity=arts_centre"]},
        
        # Other amenities
        {"name": "shopping", "tags": ["shop=mall", "shop=department_store", "shop=clothes"]},
        {"name": "services", "tags": ["amenity=bank", "amenity=post_office", "amenity=atm"]}
    ]
    
    # Build overpass queries and collect results
    results = {}
    scores = {}
    
    for i, category in enumerate(categories):
        await ctx.report_progress(i, len(categories))
        ctx.info(f"Analyzing {category['name']} in neighborhood...")
        
        # Convert radius to bounding box
        lat_delta = radius / 111000
        lon_delta = radius / (111000 * math.cos(math.radians(latitude)))
        
        bbox = (
            longitude - lon_delta,
            latitude - lat_delta,
            longitude + lon_delta,
            latitude + lat_delta
        )
        
        # Build Overpass query
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Create query for category tags
        tag_filters = []
        for tag in category["tags"]:
            key, value = tag.split("=")
            tag_filters.append(f'node["{key}"="{value}"]({{bbox}});')
            tag_filters.append(f'way["{key}"="{value}"]({{bbox}});')
        
        query = f"""
        [out:json];
        (
            {" ".join(tag_filters)}
        );
        out body;
        """
        
        query = query.replace("{bbox}", f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(overpass_url, data={"data": query}) as response:
                    if response.status == 200:
                        data = await response.json()
                        features = data.get("elements", [])
                    else:
                        ctx.warning(f"Failed to analyze {category['name']}: {response.status}")
                        features = []
                        
            # Process and calculate metrics
            feature_list = []
            distances = []
            
            for feature in features:
                tags = feature.get("tags", {})
                
                # Get coordinates based on feature type
                coords = {}
                if feature.get("type") == "node":
                    coords = {
                        "latitude": feature.get("lat"),
                        "longitude": feature.get("lon")
                    }
                elif "center" in feature:
                    coords = {
                        "latitude": feature.get("center", {}).get("lat"),
                        "longitude": feature.get("center", {}).get("lon")
                    }
                
                # Skip if no valid coordinates
                if not coords:
                    continue
                
                # Calculate distance from center point
                distance = haversine(latitude, longitude, coords["latitude"], coords["longitude"])
                distances.append(distance)
                
                feature_list.append({
                    "id": feature.get("id"),
                    "name": tags.get("name", "Unnamed"),
                    "type": feature.get("type"),
                    "coordinates": coords,
                    "distance": round(distance, 1),
                    "tags": tags
                })
            
            # Sort by distance
            feature_list.sort(key=lambda x: x["distance"])
            
            # Calculate metrics
            count = len(feature_list)
            avg_distance = sum(distances) / count if count > 0 else None
            min_distance = min(distances) if count > 0 else None
            
            # Score this category (0-10)
            # Higher score for more amenities and closer proximity
            if count == 0:
                category_score = 0
            else:
                # Base score on count and proximity
                count_score = min(count / 5, 1) * 5  # Up to 5 points for count
                proximity_score = 5 - min(min_distance / radius, 1) * 5  # Up to 5 points for proximity
                category_score = count_score + proximity_score
            
            # Store results
            results[category["name"]] = {
                "count": count,
                "features": feature_list[:10],  # Limit to top 10
                "metrics": {
                    "total_count": count,
                    "avg_distance": round(avg_distance, 1) if avg_distance else None,
                    "min_distance": round(min_distance, 1) if min_distance else None
                }
            }
            
            scores[category["name"]] = category_score
            
        except Exception as e:
            ctx.warning(f"Error analyzing {category['name']}: {str(e)}")
            results[category["name"]] = {"error": str(e)}
            scores[category["name"]] = 0
    
    # Calculate overall neighborhood score
    if scores:
        overall_score = sum(scores.values()) / len(scores)
    else:
        overall_score = 0
    
    # Calculate walkability score based on amenities within walking distance (500m)
    walkable_amenities = 0
    walkable_categories = 0
    
    for category_name, category_data in results.items():
        if "metrics" in category_data:
            # Count amenities within walking distance
            walking_count = sum(1 for feature in category_data.get("features", []) 
                               if feature.get("distance", float("inf")) <= 500)
            
            if walking_count > 0:
                walkable_amenities += walking_count
                walkable_categories += 1
    
    walkability_score = min(walkable_amenities + walkable_categories, 10)
    
    # Report completion
    await ctx.report_progress(len(categories), len(categories))
    
    return {
        "location": {
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude
            },
            "address": address_info.get("display_name", "Unknown location")
        },
        "scores": {
            "overall": round(overall_score, 1),
            "walkability": walkability_score,
            "categories": {k: round(v, 1) for k, v in scores.items()}
        },
        "categories": results,
        "analysis_radius": radius,
        "timestamp": datetime.now().isoformat()
    }
