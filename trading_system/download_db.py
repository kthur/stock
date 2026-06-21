import os
import zipfile
import io
import urllib.request
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
        
    # 1. Fetch latest artifact named 'stock-databases'
    url = f"https://api.github.com/repos/{repo}/actions/artifacts?name=stock-databases&per_page=1"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "Python-urllib")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        artifacts = data.get("artifacts", [])
        if not artifacts:
            logger.warning("No artifact named 'stock-databases' found in GitHub.")
            return
            
        latest_artifact = artifacts[0]
        artifact_id = latest_artifact["id"]
        logger.info(f"Found artifact ID: {artifact_id} created at {latest_artifact['created_at']}.")
        
        # 2. Download the artifact ZIP
        download_url = f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip"
        download_req = urllib.request.Request(download_url)
        download_req.add_header("Authorization", f"Bearer {token}")
        download_req.add_header("Accept", "application/vnd.github+json")
        download_req.add_header("X-GitHub-Api-Version", "2022-11-28")
        download_req.add_header("User-Agent", "Python-urllib")
        
        logger.info("Downloading database artifact ZIP (this might take a few moments)...")
        with urllib.request.urlopen(download_req) as response:
            zip_data = response.read()
            
        # 3. Unzip the databases
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
