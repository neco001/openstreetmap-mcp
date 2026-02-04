from mcp.server.fastmcp import FastMCP, Context
from dataclasses import dataclass
from typing import AsyncIterator
from contextlib import asynccontextmanager
from osm_mcp_server.client import OSMClient

# Create application context
@dataclass
class AppContext:
    osm_client: OSMClient

# Define lifespan manager
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage OSM client lifecycle"""
    osm_client = OSMClient()
    try:
        await osm_client.connect()
        yield AppContext(osm_client=osm_client)
    finally:
        await osm_client.disconnect()

# Create the MCP server
mcp = FastMCP(
    "Location-Based App MCP Server",
    dependencies=["aiohttp", "geojson", "shapely", "haversine"],
    lifespan=app_lifespan
)
