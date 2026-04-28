#!/usr/bin/env python3
"""Fix invalid slugs in ontology_objects and object_properties tables."""
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.services.ontology.slug import slugify_name

DATABASE_URL = "sqlite:///omaha.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def is_valid_slug(slug: str) -> bool:
    """Check if slug matches ^[a-zA-Z0-9_-]+$"""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', slug))

def fix_object_slugs():
    """Fix invalid slugs in ontology_objects."""
    db = Session()
    try:
        result = db.execute(text("SELECT id, name, slug, tenant_id FROM ontology_objects"))
        fixed = 0
        for row in result:
            obj_id, name, slug, tenant_id = row
            if not slug or not is_valid_slug(slug):
                new_slug = slugify_name(name)
                # Ensure uniqueness
                counter = 1
                candidate = new_slug
                while True:
                    check = db.execute(
                        text("SELECT COUNT(*) FROM ontology_objects WHERE slug = :slug AND tenant_id = :tid AND id != :id"),
                        {"slug": candidate, "tid": tenant_id, "id": obj_id}
                    ).scalar()
                    if check == 0:
                        break
                    candidate = f"{new_slug}-{counter}"
                    counter += 1

                db.execute(
                    text("UPDATE ontology_objects SET slug = :slug WHERE id = :id"),
                    {"slug": candidate, "id": obj_id}
                )
                print(f"Fixed object #{obj_id}: '{name}' slug '{slug}' → '{candidate}'")
                fixed += 1

        db.commit()
        print(f"\nFixed {fixed} object slugs")
    finally:
        db.close()

def fix_property_slugs():
    """Fix invalid slugs in object_properties."""
    db = Session()
    try:
        result = db.execute(text("SELECT id, name, slug, object_id FROM object_properties"))
        fixed = 0
        for row in result:
            prop_id, name, slug, object_id = row
            if not slug or not is_valid_slug(slug):
                new_slug = slugify_name(name)
                # Ensure uniqueness within object
                counter = 1
                candidate = new_slug
                while True:
                    check = db.execute(
                        text("SELECT COUNT(*) FROM object_properties WHERE slug = :slug AND object_id = :oid AND id != :id"),
                        {"slug": candidate, "oid": object_id, "id": prop_id}
                    ).scalar()
                    if check == 0:
                        break
                    candidate = f"{new_slug}-{counter}"
                    counter += 1

                db.execute(
                    text("UPDATE object_properties SET slug = :slug WHERE id = :id"),
                    {"slug": candidate, "id": prop_id}
                )
                print(f"Fixed property #{prop_id}: '{name}' slug '{slug}' → '{candidate}'")
                fixed += 1

        db.commit()
        print(f"\nFixed {fixed} property slugs")
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Fixing invalid slugs ===\n")
    fix_object_slugs()
    fix_property_slugs()
    print("\n✓ Done")
