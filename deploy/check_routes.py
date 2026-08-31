"""检查 OpenAPI 路由。"""
import httpx
import asyncio
import json

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=15) as c:
        resp = await c.get("/openapi.json")
        data = resp.json()
        paths = [p for p in data.get("paths", {}) if "/inv/" in p]
        print(f"INV paths: {len(paths)}")
        for p in sorted(paths):
            methods = list(data["paths"][p].keys())
            print(f"  {p} [{','.join(methods)}]")

asyncio.run(main())