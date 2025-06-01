"""Constants for the Paris Markets integration."""

from typing import List

from .models import FilterMode, ProductType

DOMAIN = "paris_markets"
ATTRIBUTION = "Data provided by OpenData Paris"


# API
API_ENDPOINT = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/marches-decouverts/records"

# Configuration Keys
CONF_FILTER_MODE = "filter_mode"
CONF_RADIUS = "radius_km"
CONF_ARRONDISSEMENTS = "arrondissements"
CONF_PRODUCT_TYPES = "product_types"
SCAN_INTERVAL = "scan_interval"

# Default Values
DEFAULT_ICON = "mdi:basket"
DEFAULT_FILTER_MODE = FilterMode.RADIUS.value
DEFAULT_RADIUS_KM = 2.0
DEFAULT_ARRONDISSEMENTS: List[int] = []
DEFAULT_SCAN_INTERVAL = 1
MINIMUM_SCAN_INTERVAL = 1  # Markets data doesn't change frequently
DEFAULT_PRODUCT_TYPES = [
    ProductType.ALIMENTAIRE.value,
    ProductType.ALIMENTAIRE_BIO.value,
]
