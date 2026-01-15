"""
Verify WebSocket paths
"""
import asyncio
import websockets
import sys

async def check_ws(url):
    print(f"Checking {url}...")
    try:
        async with websockets.connect(url, timeout=2) as ws:
            print(f"  ✅ Success: {url}")
            return True
    except Exception as e:
        print(f"  ❌ Failed: {url} - {e}")
        return False

async def main():
    port = 8009
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    base_url = f"ws://127.0.0.1:{port}"
    task_id = "test-check"
    
    paths = [
        f"{base_url}/v1/ws/tasks/{task_id}",
        f"{base_url}/ws/tasks/{task_id}",
        f"{base_url}/ws/terminal",
        f"{base_url}/v1/ws/terminal",
    ]
    
    for path in paths:
        await check_ws(path)

if __name__ == "__main__":
    asyncio.run(main())
