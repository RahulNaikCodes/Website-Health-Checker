import urllib.request
import urllib.error
from datetime import datetime, timezone

TARGET_URL = "https://example.com"  # Replace with the website URL you want to monitor


def lambda_handler(event, context):
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        req = urllib.request.Request(
            TARGET_URL,
            headers={"User-Agent": "AWS-Lambda-Health-Checker"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            print(f"[{timestamp}] SUCCESS: {TARGET_URL} returned HTTP {status_code}")
            return {
                "statusCode": status_code,
                "status": "UP",
                "url": TARGET_URL
            }
    except urllib.error.URLError as e:
        print(f"[{timestamp}] FAILURE: {TARGET_URL} check failed - {e}")
        return {
            "statusCode": 500,
            "status": "DOWN",
            "url": TARGET_URL,
            "error": str(e)
        }
