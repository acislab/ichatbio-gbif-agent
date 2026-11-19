from agent import GBIFAgent
from dotenv import load_dotenv
from ichatbio.server import run_agent_server
from src.log import setup_logger

if __name__ == "__main__":
    # Force logger initialization
    load_dotenv()
    logger = setup_logger()
    logger.info("TEST: Logging system startup check")
    print("DEBUG: Logging initialized, test message logged")
    gbif = GBIFAgent()
    run_agent_server(gbif, host="0.0.0.0", port=9999)
