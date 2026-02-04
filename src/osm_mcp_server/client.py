import aiohttp
import math
from typing import List, Dict, Tuple

class OSMClient:
    def __init__(self, base_url="https://api.openstreetmap.org/api/0.6"):
        self.base_url = base_url
        self.session = None
        self.cache = {}  # Simple in-memory cache
    
    async def connect(self):
        self.session = aiohttp.ClientSession()
        
    async def disconnect(self):
        if self.session:
            await self.session.close()

    async def geocode(self, query: str) -> List[Dict]:
        """Geocode an address or place name"""
        if not self.session:
            raise RuntimeError("OSM client not connected")
        
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        async with self.session.get(
            nominatim_url,
            params={
                "q": query,
                "format": "json",
                "limit": 5
            },
            headers={"User-Agent": "OSM-MCP-Server/1.0"}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to geocode '{query}': {response.status}")
    
    async def reverse_geocode(self, lat: float, lon: float) -> Dict:
        """Reverse geocode coordinates to address"""
        if not self.session:
            raise RuntimeError("OSM client not connected")
        
        nominatim_url = "https://nominatim.openstreetmap.org/reverse"
        async with self.session.get(
            nominatim_url,
            params={
                "lat": lat,
                "lon": lon,
                "format": "json"
            },
            headers={"User-Agent": "OSM-MCP-Server/1.0"}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to reverse geocode ({lat}, {lon}): {response.status}")

    async def get_route(self, 
                         from_lat: float, 
                         from_lon: float, 
                         to_lat: float, 
                         to_lon: float,
                         mode: str = "car",
                         steps: bool = False,
                         overview: str = "overview",
                         annotations: bool = True) -> Dict:
        """Get routing information between two points"""
        if not self.session:
            raise RuntimeError("OSM client not connected")
        
        # Use OSRM for routing
        osrm_url = f"http://router.project-osrm.org/route/v1/{mode}/{from_lon},{from_lat};{to_lon},{to_lat}"
        params = {
            "overview": overview,
            "geometries": "geojson",
            "steps": str(steps).lower(),
            "annotations": str(annotations).lower()
        }
        
        async with self.session.get(osrm_url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get route: {response.status}")

    async def get_nearby_pois(self, 
                             lat: float, 
                             lon: float, 
                             radius: float = 1000,
                             categories: List[str] = None) -> List[Dict]:
        """Get points of interest near a location"""
        if not self.session:
            raise RuntimeError("OSM client not connected")
        
        # Convert radius to bounding box (approximate)
        # 1 degree latitude ~= 111km
        # 1 degree longitude ~= 111km * cos(latitude)
        lat_delta = radius / 111000
        lon_delta = radius / (111000 * math.cos(math.radians(lat)))
        
        bbox = (
            lon - lon_delta,
            lat - lat_delta,
            lon + lon_delta,
            lat + lat_delta
        )
        
        # Build Overpass query
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Default to common POI types if none specified
        if not categories:
            categories = ["amenity", "shop", "tourism", "leisure"]
        
        # Build tag filters
        tag_filters = []
        for category in categories:
            tag_filters.append(f'node["{category}"]({{bbox}});')
        
        query = f"""
        [out:json];
        (
            {" ".join(tag_filters)}
        );
        out body;
        """
        
        query = query.replace("{bbox}", f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}")
        
        async with self.session.post(overpass_url, data={"data": query}) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("elements", [])
            else:
                raise Exception(f"Failed to get nearby POIs: {response.status}")

    async def search_features_by_category(self, 
                                         bbox: Tuple[float, float, float, float],
                                         category: str,
                                         subcategories: List[str] = None) -> List[Dict]:
        """Search for OSM features by category and subcategories"""
        if not self.session:
            raise RuntimeError("OSM client not connected")
        
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Build query for specified category and subcategories
        if subcategories:
            subcategory_filters = " or ".join([f'"{category}"="{sub}"' for sub in subcategories])
            query_filter = f'({subcategory_filters})'
        else:
            query_filter = f'"{category}"'
        
        query = f"""
        [out:json];
        (
          node[{query_filter}]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
          way[{query_filter}]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
          relation[{query_filter}]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
        );
        out body;
        """
        
        async with self.session.post(overpass_url, data={"data": query}) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("elements", [])
            else:
                raise Exception(f"Failed to search features by category: {response.status}")
