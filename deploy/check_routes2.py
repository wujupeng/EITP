"""检查 OpenAPI 路由 - 修正版。"""
import httpx
import asyncio
import json

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=15) as c:
        resp = await c.get("/openapi.json")
        data = resp.json()
        all_paths = list(data.get("paths", {}).keys())
        inv_paths = [p for p in all_paths if "/inv/" in p]
        print(f"Total paths: {len(all_paths)}")
        print(f"INV paths: {len(inv_paths)}")
        for p in sorted(inv_paths):
            methods = list(data["paths"][p].keys())
            print(f"  {p} [{','.join(methods)}]")

asyncio.run(main())