import asyncio
import os
import re
import argparse
import shutil
from playwright.async_api import async_playwright
from urllib.parse import urlparse


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def parse_netscape_cookies(filepath: str) -> list[dict]:
    """Parse a Netscape-format cookies.txt file into playwright cookie dicts."""
    cookies = []
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path, secure, expires, name, value = parts[:7]
            cookies.append({
                "name": name,
                "value": value,
                "domain": domain.lstrip("."),
                "path": path,
                "secure": secure.upper() == "TRUE",
                "expires": int(expires) if expires.isdigit() else -1,
            })
    return cookies


async def save_mhtml(url: str, output_file: str, cookies_file: str | None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context()

        if cookies_file and os.path.exists(cookies_file):
            cookies = parse_netscape_cookies(cookies_file)
            if cookies:
                await context.add_cookies(cookies)
                print(f"Loaded {len(cookies)} cookies")

        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)

        cdp = await context.new_cdp_session(page)
        result = await cdp.send("Page.captureSnapshot", {"format": "mhtml"})

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result["data"])

        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Download a webpage as MHTML.")
    parser.add_argument("--url", required=True, help="URL of the page to download")
    parser.add_argument("--title", help="Optional output filename (without extension)")
    parser.add_argument("--output", required=True, help="Full path for the output .mhtml file")
    parser.add_argument("--cookies-file", help="Path to Netscape-format cookies.txt")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print(f"Downloading page...")
    asyncio.run(save_mhtml(args.url, args.output, args.cookies_file))
    print(f"Saved MHTML: {args.output}")


if __name__ == "__main__":
    main()
