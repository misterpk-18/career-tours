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

# Wrapper wording that models put around a skill without changing which skill it
# is: "experience with Django", "strong Python skills", "Docker (containers)".
# Stripping it before lookup is what lets an extracted phrase land on the
# canonical name instead of drifting off to an embedding comparison.
#
# The list is deliberately short and made only of words that are never part of a
# skill name here. Anything more aggressive starts destroying real names —
# "development" would turn "Web Development" into "Web", and "programming" would
# turn "Programming Fundamentals" into nothing.
_LEADING_FILLER = (
    "hands-on experience with",
    "hands on experience with",
    "working knowledge of",
    "practical knowledge of",
    "experience with",
    "experience in",
    "experience using",
    "knowledge of",
    "understanding of",
    "familiarity with",
    "proficiency in",
    "proficiency with",
    "proficient in",
    "expertise in",
    "competency in",
    "ability to use",
    "skilled in",
    "strong",
    "solid",
    "good",
    "basic",
    "advanced",
    "intermediate",
)

_TRAILING_FILLER = (
    "skills",
    "skill",
    "experience",
    "knowledge",
    "expertise",
    "proficiency",
)

_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")


def _key(name: str) -> str:
    """Lookup key for a skill name: casefolded with whitespace collapsed.

    Deliberately conservative — it does not strip punctuation, because
    punctuation is meaningful in names like ``C++``, ``C#``, ``CI/CD`` and
    ``TCP/IP``. Genuinely different wording belongs in ``aliases``.
    """
    return _WHITESPACE.sub(" ", name).strip().casefold()


def _stripped_key(name: str) -> str:
    """:func:`_key` with wrapper wording removed from both ends.

    Applied repeatedly, so "strong hands-on experience with Docker skills"
    collapses the same way a single wrapper does. Returns ``""`` when there is
    nothing left, which callers must treat as "no usable name" rather than as a
    lookup key.
    """
    key = _key(_PARENTHETICAL.sub("", name))

    changed = True
    while changed and key:
        changed = False

        for filler in _LEADING_FILLER:
            if key.startswith(filler + " "):
                key = key[len(filler) + 1:].lstrip()
                changed = True
                break

        for filler in _TRAILING_FILLER:
            if key.endswith(" " + filler):
                key = key[: -len(filler) - 1].rstrip()
                changed = True
                break

    return key.strip(" -–—:,")


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

        The exact key is tried first, then the same key with wrapper wording
        stripped, so "experience with Django" resolves to "Django" without
        needing an alias for every phrasing a model might produce. The order
        matters: a name that *is* canonical is never put through the stripper.

        Returns ``None`` when the name is empty or unknown to the taxonomy.
        Callers decide what to do with a miss — embedding-based snapping and
        the novel-skill path are handled by the normalizer, not here.
        """
        if not name or not name.strip():
            return None

        cls._load()

        exact = cls._lookup.get(_key(name))
        if exact is not None:
            return exact

        stripped = _stripped_key(name)
        return cls._lookup.get(stripped) if stripped else None

    @classmethod
    def identity(cls, name: Optional[str]) -> Optional[str]:
        """A comparison key for "are these two strings the same skill?".

        Canonical name when the taxonomy knows it, otherwise the stripped
        lookup key. Two names share an identity exactly when they name the same
        skill as far as the repo-owned vocabulary can tell — no embeddings
        involved. The 369-name taxonomy covers only part of the catalog, so the
        stripped-key fallback is what keeps "Kubernetes administration" and
        "experience with Kubernetes administration" together even though
        neither is canonical.

        Returns ``None`` when nothing usable is left, which callers must not
        treat as a match against another ``None``.
        """
        canonical = cls.canonical(name)
        if canonical is not None:
            return canonical.casefold()

        if not name:
            return None

        stripped = _stripped_key(name)
        return stripped or None

    @classmethod
    def is_canonical(cls, name: str) -> bool:
        cls._load()
        return name in cls._categories

    @classmethod
    def aliases(cls) -> Dict[str, str]:
        """The full lookup key -> canonical name map (canonicals included)."""
        cls._load()
        return dict(cls._lookup)
