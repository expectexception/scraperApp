import re
from typing import Optional


class CompanyManager:
    """Utility class for advanced company name normalization and identification"""

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """
        Normalize company name for matching purposes.
        Removes common suffixes like Inc, Ltd, etc., but preserves branch indicators.
        """
        if not name:
            return "unknown"

        # 1. Basic cleaning
        normalized = name.strip()

        # 2. Preserve specific branch identifiers by making them uniform
        # (e.g., "Air India Express" vs "Air India" should be different)
        # We don't remove these, just normalize them

        # 3. Suffixes that SHOULD be removed (Generic legal/business indicators)
        generic_suffixes = [
            r"\binc(orporated)?\b",
            r"\bltd\b",
            r"\blimited\b",
            r"\bllp\b",
            r"\bllc\b",
            r"\bcorp(oration)?\b",
            r"\bplc\b",
            r"\bpvt\b",
            r"\bprivate\b",
            r"\bco(mpany)?\b",
            r"\bs\.?a\.?\b",
            r"\ba\.?g\.?\b",
            r"\bn\.?v\.?\b",
            r"\bgmbh\b",
        ]

        # Apply normalization to lower for matching
        norm_match = normalized.lower()

        # Remove generic suffixes (only if at the end or followed by punctuation)
        for pattern in generic_suffixes:
            norm_match = re.sub(pattern + r"[.\s,]*$", "", norm_match).strip()
            norm_match = re.sub(pattern + r"[.\s,]+", " ", norm_match).strip()

        # Remove trailing punctuation
        norm_match = re.sub(r"[.,\-&]+$", "", norm_match).strip()

        # Collapse whitespace
        norm_match = " ".join(norm_match.split())

        return norm_match

    @staticmethod
    def extract_company_from_text(text: str) -> Optional[str]:
        """
        Attempt to extract company name from description or other text.
        Look for "at [Company]" or "[Company] is hiring".
        """
        if not text:
            return None

        patterns = [
            r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:is|was|seeks)",
            r"Join\s+the\s+team\s+at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
            r"About\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None
