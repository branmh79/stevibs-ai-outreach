from typing import Dict, List
from models.place import Place

# Global in-memory cache
SCRAPED_PLACE_CACHE: Dict[str, List[Place]] = {}
