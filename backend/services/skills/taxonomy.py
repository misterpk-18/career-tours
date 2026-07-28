"""Access to the repo-owned canonical skill vocabulary.

The taxonomy in ``backend/data/skill_taxonomy.json`` is the source of truth for
how a skill is *named*. It is deliberately independent of the ``skills``
database table: that catalog is joined on separately to resolve ``skill_id``,
and its non-canonical spellings (``AWS S3``, ``Python Pandas``, ``OOP``) live
here as aliases.

Two consumers:

* the extraction prompt, which is built from :meth:`SkillTaxonomy.names_by_category`
* skill normalization, which snaps model output onto canonical names via
  :meth:`SkillTaxonomy.canonical`

The file is loaded and validated once per process, on first use.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "data" / "skill_taxonomy.json"

CATEGORIES = ("technical", "soft", "domain")

_WHITESPACE = re.compile(r"\s+")


def _key(name: str) -> str:
    """Lookup key for a skill name: casefolded with whitespace collapsed.

    Deliberately conservative — it does not strip punctuation, because
    punctuation is meaningful in names like ``C++``, ``C#``, ``CI/CD`` and
    ``TCP/IP``. Genuinely different wording belongs in ``aliases``.
    """
    return _WHITESPACE.sub(" ", name).strip().casefold()


class SkillTaxonomy:
    _version: Optional[int] = None
    _categories: Dict[str, str] = {}
    _lookup: Dict[str, str] = {}
    _by_category: Dict[str, List[str]] = {}

    @classmethod
    def _load(cls) -> None:
        if cls._version is not None:
            return

        with TAXONOMY_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)

        version = data.get("version")
        entries = data.get("skills")

        if not isinstance(version, int):
            raise ValueError(f"{TAXONOMY_PATH}: 'version' must be an integer")

        if not isinstance(entries, list) or not entries:
            raise ValueError(f"{TAXONOMY_PATH}: 'skills' must be a non-empty list")

        categories: Dict[str, str] = {}
        lookup: Dict[str, str] = {}
        by_category: Dict[str, List[str]] = {category: [] for category in CATEGORIES}

        for entry in entries:
            name = entry.get("name")
            category = entry.get("category")
            aliases = entry.get("aliases", [])

            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{TAXONOMY_PATH}: every skill needs a non-empty 'name'")

            if category not in CATEGORIES:
                raise ValueError(f"{TAXONOMY_PATH}: {name!r} has invalid category {category!r}; expected one of {CATEGORIES}")

            if not isinstance(aliases, list):
                raise ValueError(f"{TAXONOMY_PATH}: {name!r} has non-list 'aliases'")

            name_key = _key(name)

            if name_key in lookup:
                raise ValueError(f"{TAXONOMY_PATH}: duplicate canonical name {name!r} (collides with {lookup[name_key]!r})")

            categories[name] = category
            lookup[name_key] = name
            by_category[category].append(name)

        # Aliases are registered in a second pass so a canonical name always
        # wins over an alias that happens to spell it differently.
        for entry in entries:
            name = entry["name"]

            for alias in entry.get("aliases", []):
                if not isinstance(alias, str) or not alias.strip():
                    raise ValueError(f"{TAXONOMY_PATH}: {name!r} has an empty alias")

                alias_key = _key(alias)
                existing = lookup.get(alias_key)

                if existing is not None and existing != name:
                    raise ValueError(
                        f"{TAXONOMY_PATH}: alias {alias!r} on {name!r} already resolves to {existing!r}"
                    )

                lookup[alias_key] = name

        for category in CATEGORIES:
            by_category[category].sort(key=str.casefold)

        cls._version = version
        cls._categories = categories
        cls._lookup = lookup
        cls._by_category = by_category

    @classmethod
    def version(cls) -> int:
        cls._load()
        assert cls._version is not None
        return cls._version

    @classmethod
    def names(cls) -> List[str]:
        """All canonical skill names, sorted case-insensitively."""
        cls._load()
        return sorted(cls._categories, key=str.casefold)

    @classmethod
    def names_by_category(cls) -> Dict[str, List[str]]:
        """Canonical names grouped by category, for building the prompt."""
        cls._load()
        return {category: list(names) for category, names in cls._by_category.items()}

    @classmethod
    def category(cls, name: str) -> Optional[str]:
        """Category of a canonical name, or ``None`` if it is not canonical."""
        cls._load()
        return cls._categories.get(name)

    @classmethod
    def canonical(cls, name: Optional[str]) -> Optional[str]:
        """Resolve a raw name to its canonical form via exact or alias match.

        Returns ``None`` when the name is empty or unknown to the taxonomy.
        Callers decide what to do with a miss — embedding-based snapping and
        the novel-skill path are handled by the normalizer, not here.
        """
        if not name or not name.strip():
            return None

        cls._load()
        return cls._lookup.get(_key(name))

    @classmethod
    def is_canonical(cls, name: str) -> bool:
        cls._load()
        return name in cls._categories

    @classmethod
    def aliases(cls) -> Dict[str, str]:
        """The full lookup key -> canonical name map (canonicals included)."""
        cls._load()
        return dict(cls._lookup)
