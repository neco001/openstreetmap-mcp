from math import radians, sin, cos, sqrt, asin

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth using the Haversine formula."""
    R = 6371000  # Earth radius in meters
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c
