import asyncio
import zipfile
import os
import re
import argparse
import shutil
from playwright.async_api import async_playwright
from urllib.parse import urlparse


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


async def save_mhtml(url: str, output_file: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)

        cdp = await page.context.new_cdp_session(page)
        result = await cdp.send("Page.captureSnapshot", {"format": "mhtml"})

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result["data"])

        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Download a webpage as MHTML.")
    parser.add_argument("--url", required=True, help="URL of the page to download")
    parser.add_argument("--title", help="Optional output filename (without extension)")
    args = parser.parse_args()

    if args.title:
        base_name = sanitize_filename(args.title)
    else:
        parsed = urlparse(args.url)
        path = parsed.path.strip("/").replace("/", "_")
        base_name = sanitize_filename(path or parsed.netloc or "webpage")

    if not base_name:
        base_name = "webpage"

    mhtml_filename = f"{base_name}.mhtml"
    zip_filename = f"{base_name}.zip"

    download_dir = os.path.join("downloads", "mhtml")
    os.makedirs(download_dir, exist_ok=True)

    tmp_dir = "temp_mhtml"
    os.makedirs(tmp_dir, exist_ok=True)
    mhtml_path = os.path.join(tmp_dir, mhtml_filename)

    print(f"Downloading {args.url} -> {mhtml_filename}")
    asyncio.run(save_mhtml(args.url, mhtml_path))

    zip_path = os.path.join(download_dir, zip_filename)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(mhtml_path, arcname=mhtml_filename)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"Saved: {zip_path}")


if __name__ == "__main__":
    main()
