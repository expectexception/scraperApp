import asyncio
import os
import django
import re
import curl_cffi.requests as curl_requests

async def debug():
    url = "https://hahnair.jobs.personio.de/xml"
    async with curl_requests.AsyncSession() as s:
        response = await s.get(url)
        xml = response.text
        print(f"XML length: {len(xml)}")
        
        position_pattern = r'<position[^>]*>(.*?)</position>'
        positions = re.findall(position_pattern, xml, re.DOTALL)
        print(f"Found {len(positions)} positions")
        
        if positions:
            print("\nFirst position XML snippet:")
            print(positions[0][:500])
            
            title_match = re.search(r'<name><!\[CDATA\[(.*?)\]\]></name>', positions[0])
            print(f"\nTitle match: {title_match}")
            if not title_match:
                # Try without CDATA
                alt_title_match = re.search(r'<name>(.*?)</name>', positions[0])
                print(f"Alt Title match (no CDATA): {alt_title_match}")
                if alt_title_match:
                    print(f"Alt Title: {alt_title_match.group(1)}")

if __name__ == "__main__":
    asyncio.run(debug())
