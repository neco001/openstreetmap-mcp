from osm_mcp_server.instance import mcp

# Import tools to register them
import osm_mcp_server.tools.geocoding
import osm_mcp_server.tools.routing
import osm_mcp_server.tools.search
import osm_mcp_server.tools.analysis

# Import resources
import osm_mcp_server.resources

# Optionally import tools.extras to enable specialized search method
# import tools.extras 

if __name__ == "__main__":
    mcp.run()