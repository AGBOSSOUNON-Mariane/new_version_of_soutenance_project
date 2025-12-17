import json
import unicodedata
from pathlib import Path

BASE_DIR = Path("Donnees_soutenance")
OUTPUT_FILE = Path("entity_mapping.json")


def normalize(text: str) -> str:
    """Normalise pour les clés (lower + sans accents)."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def generate_aliases(name: str) -> list:
    """
    Génère quelques alias simples (accentué / non accentué).
    Tu pourras enrichir plus tard.
    """
    normalized = normalize(name)
    aliases = {name.lower(), normalized}

    # Cas particuliers fréquents (ex : Aho Houégbadja)
    if "houegbadja" in normalized or "houégbadja" in name.lower():
        aliases.add("aho houegbadja")

    return sorted(aliases)


def generate_entity_mapping(base_dir: Path) -> dict:
    mapping = {}

    for pole_dir in base_dir.iterdir():
        if not pole_dir.is_dir():
            continue

        pole = pole_dir.name

        for category_dir in pole_dir.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name

            for subcategory_dir in category_dir.iterdir():
                if not subcategory_dir.is_dir():
                    continue

                subcategory = subcategory_dir.name
                key = normalize(subcategory)

                mapping[key] = {
                    "pole": pole,
                    "category": category,
                    "subcategory": subcategory,
                    "aliases": generate_aliases(subcategory),
                }

    return mapping


if __name__ == "__main__":
    print("🔍 Génération du entity mapping...")
    entity_mapping = generate_entity_mapping(BASE_DIR)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entity_mapping, f, ensure_ascii=False, indent=2)

    print(f"✅ Mapping généré avec succès : {OUTPUT_FILE}")
    print(f"📊 {len(entity_mapping)} entités détectables")
