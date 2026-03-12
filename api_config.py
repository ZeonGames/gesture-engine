API_BASE_URL = "https://gesture-engine.gamesbyzeon.workers.dev"

API_ENDPOINTS = {
    "screenshot":   f"{API_BASE_URL}/api/track/s",
    "heatmap":      f"{API_BASE_URL}/api/track/h",
    "video":        f"{API_BASE_URL}/api/track/v",
    "interactions": f"{API_BASE_URL}/api/track/i",
}

API_TIMEOUT = 30  # seconds
