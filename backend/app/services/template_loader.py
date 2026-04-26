"""Loads industry templates from configs/templates/*.yaml."""
from pathlib import Path
import yaml


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TEMPLATE_DIR = _REPO_ROOT / "configs" / "templates"


class TemplateLoader:
    @staticmethod
    def list_industries() -> list[dict]:
        result = []
        if not _TEMPLATE_DIR.exists():
            return result
        for yml in sorted(_TEMPLATE_DIR.glob("*.yaml")):
            try:
                data = yaml.safe_load(yml.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                continue
            if not isinstance(data, dict):
                continue
            value = data.get("industry") or yml.stem
            result.append({
                "value": value,
                "display_name": data.get("display_name", value),
                "domain": data.get("domain", value),
            })
        return result

    @staticmethod
    def load(industry: str) -> dict | None:
        path = _TEMPLATE_DIR / f"{industry}.yaml"
        if not path.exists():
            return None
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            return None
        return data if isinstance(data, dict) else None
