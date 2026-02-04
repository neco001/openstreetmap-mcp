# Enterprise OpenStreetMap (OSM) MCP Analytics Server

A modular, high-performance Model Context Protocol (MCP) server for OpenStreetMap. This implementation goes beyond simple geocoding, providing advanced geospatial analytics like neighborhood livability scoring and commute analysis.
## 🚀 Why this server?

While there are many OSM MCP servers, this version is built for **stability**, **modular extension**, and **advanced insights**:

- **Modular Architecture**: Clean separation between API Client, Utility logic, and Tool definitions. Easy to audit and extend.
- **Enterprise Analytics**:
  - `analyze_neighborhood`: Calculates a "Livability Score" based on walking proximity to essential services (groceries, healthcare, parks).
  - `analyze_commute`: Multi-modal comparison of travel times (car, bike, foot) for lifestyle planning.
- **Efficient**: Uses FastMCP for asynchronous I/O and structured tool registration.
- **Windows Optimized**: Built and tested to run reliably as a background process on Windows environments.

## 🛠 Features

### Core Tools
- **Geocoding**: `geocode_address`, `reverse_geocode`
- **Routing**: `get_route_directions` (OSRM based)
- **Search**: `find_nearby_places`, `search_category`
- **Analytics**: `explore_area`, `analyze_neighborhood`, `analyze_commute`

### Specialized Tools (Optional)
Found in `tools/extras.py` (not loaded by default for performance):
- `find_schools_nearby`
- `find_ev_charging_stations`
- `find_parking_facilities`
- `suggest_meeting_point`

### Resources
- `location://place/{query}`: Real-time place metadata.
- `location://map/{style}/{z}/{x}/{y}`: Interactive map tile retrieval.

## 📦 Installation

### Requirements
- Python 3.10+
- `uv` (recommended) or `pip`

### Method 1: Via MCP Config (Claude/Cursor)
Add this to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "osm-mcp": {
      "command": "python",
      "args": [
        "c:/path/to/osm-mcp-server/src/osm_mcp_server/server.py"
      ],
      "env": {
        "PYTHONPATH": "c:/path/to/osm-mcp-server/src/osm_mcp_server"
      }
    }
  }
}
```

### Method 2: Local Development
```bash
git clone https://github.com/neco001/openstreetmap-mcp
cd openstreetmap-mcp
uv sync
```

## 📂 Project Structure

```text
src/osm_mcp_server/
├── server.py           # Main Entry Point
├── instance.py         # FastMCP lifecycle
├── client.py           # HTTP logic for OSM/OSRM/Overpass
├── utils.py            # Haversine & geometric helpers
├── tools/              # Categorized tool definitions
│   ├── geocoding.py
│   ├── routing.py
│   ├── search.py
│   └── analysis.py
└── resources.py        # Map & Data resources
```

## ⚖️ License

MIT License - feel free to use, modify and distribute.

## Acknowledgments

Original logic & concepts by [Jagan Shanmugam](https://github.com/jagan-shanmugam). This repository is a modular refactor focused on Enterprise usage, Windows compatibility, and Analytics tools.
