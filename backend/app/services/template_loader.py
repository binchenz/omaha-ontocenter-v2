"""Backward-compat shim. Real implementation lives at app.services.ontology.template_loader."""
from app.services.ontology.template_loader import (  # noqa: F401
    Path,
    yaml,
    _REPO_ROOT,
    _TEMPLATE_DIR,
    TemplateLoader,
)
