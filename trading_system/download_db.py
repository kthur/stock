import os
import zipfile
import io
import urllib.request
import urllib.error
import urllib.parse
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load env from .env in the same directory or parent directory
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

def download_github_databases():
    # Check if download is enabled
    download_enabled = os.environ.get("DOWNLOAD_DB_FROM_GITHUB", "false").lower() == "true"
    if not download_enabled:
        logger.info("GitHub database download is disabled (DOWNLOAD_DB_FROM_GITHUB is not true).")
        return

    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")

    if not repo or not token:
        logger.warning("DOWNLOAD_DB_FROM_GITHUB is True, but GITHUB_REPOSITORY or GITHUB_TOKEN is not set in .env")
        return

    logger.info(f"Checking for latest database artifact in repository '{repo}'...")

    # Resolve local database paths
    base_dir = Path(__file__).parent
    db_path = os.environ.get("DB_PATH", "market_indicators.db")
    stock_price_db_path = os.environ.get("STOCK_PRICE_DB_PATH", "stock_prices.db")

    if not os.path.isabs(db_path):
        db_path = str(base_dir / db_path)
    if not os.path.isabs(stock_price_db_path):
        stock_price_db_path = str(base_dir / stock_price_db_path)

    # 1. Fetch artifacts from GitHub
    target_market = os.environ.get("INFERENCE_TARGET", os.environ.get("TARGET_MARKET", "")).strip().split(",")[0].strip()
    target_name = f"stock-databases-{target_market}" if target_market else "stock-databases"

    url = f"https://api.github.com/repos/{repo}/actions/artifacts?per_page=30"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "Python-urllib")

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

        artifacts = data.get("artifacts", [])
        matched_artifact = None
        # Try exact target name match first
        for art in artifacts:
            if art.get("name") == target_name:
                matched_artifact = art
                break
        # Fallback to any stock-databases artifact
        if not matched_artifact:
            for art in artifacts:
                if str(art.get("name", "")).startswith("stock-databases"):
                    matched_artifact = art
                    break

        if not matched_artifact:
            logger.warning(f"No artifact matching '{target_name}' or 'stock-databases*' found in GitHub.")
            return

        latest_artifact = matched_artifact
        artifact_id = latest_artifact["id"]
        logger.info(f"Found artifact '{latest_artifact.get('name')}' (ID: {artifact_id}) created at {latest_artifact['created_at']}.")

        # 2. Get the redirect URL first.
        #    GitHub API redirects to Azure Blob Storage for the actual ZIP.
        #    urllib's default handler forwards the Authorization header on redirect,
        #    which Azure rejects with 401. Fix: intercept the redirect, extract the
        #    Location URL, then download from the blob URL *without* Authorization.
        download_url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip"

        class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            """Capture the redirect Location header and do NOT follow it."""
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None  # abort redirect chain

        no_redirect_opener = urllib.request.build_opener(_NoRedirectHandler)
        download_req = urllib.request.Request(download_url)
        download_req.add_header("Authorization", f"Bearer {token}")
        download_req.add_header("Accept", "application/vnd.github+json")
        download_req.add_header("X-GitHub-Api-Version", "2022-11-28")
        download_req.add_header("User-Agent", "Python-urllib")

        logger.info("Resolving artifact download URL...")
        blob_url = None
        try:
            with no_redirect_opener.open(download_req) as response:
                # No redirect occurred — use final URL as-is
                blob_url = response.url
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and "Location" in e.headers:
                blob_url = e.headers["Location"]
                parsed = urllib.parse.urlparse(blob_url)
                logger.info(f"Redirect captured → blob host: {parsed.netloc}")
            else:
                raise

        if not blob_url:
            raise RuntimeError("Could not resolve artifact blob URL.")

        # 3. Download the actual ZIP from the blob URL.
        #    No Authorization header — Azure Blob Storage rejects it with 401.
        logger.info("Downloading database artifact ZIP (this might take a few moments)...")
        blob_req = urllib.request.Request(blob_url)
        blob_req.add_header("User-Agent", "Python-urllib")
        with urllib.request.urlopen(blob_req) as response:
            zip_data = response.read()

        # 4. Unzip the databases
        logger.info("Extracting database files...")
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            namelist = z.namelist()
            for name in namelist:
                basename = os.path.basename(name)
                if basename == "stock_prices.db":
                    logger.info(f"Extracting {name} -> {stock_price_db_path}")
                    os.makedirs(os.path.dirname(stock_price_db_path), exist_ok=True)
                    with open(stock_price_db_path, "wb") as f:
                        f.write(z.read(name))
                elif basename == "market_indicators.db":
                    logger.info(f"Extracting {name} -> {db_path}")
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    with open(db_path, "wb") as f:
                        f.write(z.read(name))

        logger.info("Database sync from GitHub completed successfully.")

    except Exception as e:
        logger.error(f"Failed to download/extract database cache from GitHub: {e}", exc_info=True)

if __name__ == "__main__":
    download_github_databases()
