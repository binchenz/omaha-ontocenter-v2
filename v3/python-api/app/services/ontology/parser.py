import os
import yaml
import re
from app.schemas.ontology_config import OntologyConfig
from app.services.query.function_engine import _validate_handler


def load_ontology(yaml_path: str) -> OntologyConfig:
    """Load and validate an ontology YAML file."""
    with open(yaml_path, "r") as f:
        raw = f.read()
    raw = _substitute_env(raw)
    data = yaml.safe_load(raw)
    config = OntologyConfig(**data)
    _validate_functions(config)
    return config


def parse_ontology_string(yaml_str: str) -> OntologyConfig:
    """Parse a YAML string into OntologyConfig."""
    yaml_str = _substitute_env(yaml_str)
    data = yaml.safe_load(yaml_str)
    config = OntologyConfig(**data)
    _validate_functions(config)
    return config


def _validate_functions(config: OntologyConfig) -> None:
    """Reject YAML configs that reference handlers outside the whitelist.

    Prevents uploading `handler: os.system` via YAML → later invocation.
    """
    for fn in config.functions:
        _validate_handler(fn.handler)
    for obj in config.objects:
        for fn in obj.functions:
            _validate_handler(fn.handler)


def _substitute_env(yaml_str: str) -> str:
    """Replace ${VAR_NAME} (uppercase only) with environment variable values."""
    def replacer(match):
        var_name = match.group(1)
        if var_name.isupper():
            return os.environ.get(var_name, match.group(0))
        return match.group(0)
    return re.sub(r'\$\{(\w+)\}', replacer, yaml_str)


def ontology_config_to_dict(config: OntologyConfig) -> dict:
    """Convert OntologyConfig back to dict for YAML export."""
    return config.model_dump(exclude_none=True)
