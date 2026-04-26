#!/usr/bin/env python3
"""Batch-rewrite import paths after services/ restructure."""
import re
import sys
from pathlib import Path

MAPPING = [
    # ontology domain
    (r"from app\.services\.ontology_store ", "from app.services.ontology.store "),
    (r"from app\.services\.ontology_importer ", "from app.services.ontology.importer "),
    (r"from app\.services\.ontology_inferrer ", "from app.services.ontology.inferrer "),
    (r"from app\.services\.ontology_draft_store ", "from app.services.ontology.draft_store "),
    (r"from app\.services\.template_loader ", "from app.services.ontology.template_loader "),
    (r"from app\.services\.schema_scanner ", "from app.services.ontology.schema_scanner "),
    # data domain
    (r"from app\.services\.data_cleaner ", "from app.services.data.cleaner "),
    (r"from app\.services\.uploaded_table_store ", "from app.services.data.uploaded_table_store "),
    # agent domain
    (r"from app\.services\.agent_tools\b", "from app.services.agent.toolkit"),
    (r"from app\.services\.agent\b(?!_|\.)", "from app.services.agent.react"),
    (r"from app\.services\.chat ", "from app.services.agent.chat_service "),
    (r"from app\.services\.chart_engine ", "from app.services.agent.chart_engine "),
    # semantic domain
    (r"from app\.services\.semantic ", "from app.services.semantic.service "),
    (r"from app\.services\.semantic_validator ", "from app.services.semantic.validator "),
    (r"from app\.services\.semantic_formatter ", "from app.services.semantic.formatter "),
    (r"from app\.services\.computed_property_engine ", "from app.services.semantic.computed_property "),
    # platform domain
    (r"from app\.services\.scheduler ", "from app.services.platform.scheduler "),
    (r"from app\.services\.pipeline_runner ", "from app.services.platform.pipeline_runner "),
    (r"from app\.services\.audit ", "from app.services.platform.audit "),
    (r"from app\.services\.datahub ", "from app.services.platform.datahub "),
    # legacy/financial domain
    (r"from app\.services\.omaha ", "from app.services.legacy.financial.omaha "),
    (r"from app\.services\.query_builder ", "from app.services.legacy.financial.query_builder "),
    (r"from app\.services\.ontology_cache_service ", "from app.services.legacy.financial.ontology_cache_service "),
]

def rewrite_file(path: Path, dry_run: bool = False) -> list[str]:
    text = path.read_text()
    changes = []
    for pattern, replacement in MAPPING:
        new_text = re.sub(pattern, replacement, text)
        if new_text != text:
            changes.append(f"  {pattern} -> {replacement}")
            text = new_text
    if changes and not dry_run:
        path.write_text(text)
    return changes

def main():
    dry_run = "--dry-run" in sys.argv
    root = Path("backend")
    files = list(root.rglob("*.py"))
    total = 0
    for f in sorted(files):
        changes = rewrite_file(f, dry_run=dry_run)
        if changes:
            print(f"{f}:")
            for c in changes:
                print(c)
            total += len(changes)
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Total rewrites: {total}")

if __name__ == "__main__":
    main()
