"""Source catalogs. Each catalog is metadata; documents stay at their canonical URLs."""

from pdoom_pipeline.catalogs.us_federal import (
    CatalogError,
    load_catalog,
    validate_catalog,
    validate_entry,
)

__all__ = [
    "CatalogError",
    "load_catalog",
    "validate_catalog",
    "validate_entry",
]
