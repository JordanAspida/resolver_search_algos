from .common import cached, store
from .lifecycleElementSearch import search as search_lifecycles

import logging
logger = logging.getLogger(__name__)


LABEL = "Roles"

# NEEDS TO BE CHANGED LOGIC DOES NOT MAKE SENSE GIVEN NEW UNDERSTANDING - MAYBE PIVOT TO ROLE TRACER

"""
CONFIGURATION TRACING 
1. Roles added to Object Types
1a. Roles on forms on those obj types
1b. Roles assigned in lifecycles
2. Roles added to Activities
3. Roles emailed to in lifecycles

COULD ALSO BE USEFUL TO CHECK:
1. If role has any permissions
2. Role has any users / groups (Only in live)
"""

def search(client):
    pass
