import os
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s %(levelname)s %(name)s : %(message)s"
)

logger = logging.getLogger(__name__)

load_dotenv()

LIVE_API_KEY = os.getenv("ASPIDA_ADVISORY_SERVICES_LIVE")
APEX_API_KEY = os.getenv("APEX_LIVE")
DEPLOY_2_KEY = os.getenv("DEPLOY_2")

from resolver_sdk.client import ResolverClient