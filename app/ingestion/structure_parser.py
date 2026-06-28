"""
Structure Parser for Government Documents
-------------------------------------------
Detects hierarchical document structure (sections, clauses, sub-clauses)
using regex patterns. Works universally across Indian government document
formats: GeM GTC, Bid Documents, BIS standards, MSME orders, etc.

Output: A flat list of StructuralUnit dicts, each representing one
logical section of the document with its heading, level, and text.
"""

import re


# Patterns ordered by structural hierarchy (highest level first)
# Each tuple: (pattern, level, name)
# The pattern matches the START of a new section/clause
STRUCTURE_PATTERNS = [
    # Level 1: Major document divisions
    (r'^(?:SECTION|Section)\s+([IVXLCDM]+|\d+)\b[.\s\-:]*(.*)$', 1, 'section'),
    (r'^(?:CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)\b[.\s\-:]*(.*)$', 1, 'chapter'),
    (r'^(?:PART|Part)\s+([IVXLCDM]+|\d+)\b[.\s\-:]*(.*)$', 1, 'part'),
    (r'^(?:ANNEXURE|Annexure|APPENDIX|Appendix)\s+([A-Z\d]+)\b[.\s\-:]*(.*)$', 1, 'annexure'),

    # Level 2: Top-level numbered sections (e.g., "1. Introduction", "2. General Terms")
    # Must start a line. The number should be followed by a dot and space.
    (r'^(\d{1,2})\.\s+([A-Z].*)', 2, 'numbered_section'),
    # Also catch "1.\n Introduction" pattern (number on separate line)
    (r'^(\d{1,2})\.\s*$', 2, 'numbered_section_solo'),

    # Level 3: Sub-sections (e.g., "2.5 Earnest Money Deposit", "9.1 Eligibility")
    (r'^(\d{1,2}\.\d{1,2})\s+(.+)', 3, 'subsection'),

    # Level 4: Sub-sub-sections (e.g., "4.1.2 Technical Criteria")
    (r'^(\d{1,2}\.\d{1,2}\.\d{1,2})\s+(.+)', 4, 'subsubsection'),

    # Level 2 alternate: ALL-CAPS headings (e.g., "ADDITIONAL TERMS AND CONDITIONS")
    # These are common in standalone government documents
    (r'^([A-Z][A-Z\s&,]{10,}[A-Z])\s*$', 2, 'caps_heading'),

    # Level 3 alternate: Roman numeral items (i., ii., iii., iv.)
    (r'^((?:i|ii|iii|iv|v|vi|vii|viii|ix|x))\.\s+(.+)', 3, 'roman_item'),

    # Level 4 alternate: Alphabetical items a., b., c. (common in GeM GTC)
    (r'^([a-z])\.\s+(.+)', 4, 'alpha_item'),

    # Level 4 alternate: Parenthetical items (1), (2), (a), (b)
    (r'^\((\d+)\)\s+(.+)', 4, 'paren_num_item'),
    (r'^\(([a-z])\)\s+(.+)', 4, 'paren_alpha_item'),
]


def parse_structure(full_text, page_texts=None):
    """
    Parse document text into structural units.
    
    Args:
        full_text: The complete cleaned document text (all pages joined)
        page_texts: Optional list of {"page_number": int, "text": str} dicts
                    for mapping content back to page numbers
    
    Returns:
        List of structural unit dicts:
        {
            "level": int,           # 1=major, 2=section, 3=subsection, 4=item
            "section_id": str,      # e.g., "2.5", "SECTION III", "(a)"
            "heading": str,         # section heading/title text
            "text": str,            # full text content of this unit
            "page_start": int,      # first page this appears on
            "page_end": int,        # last page this appears on
            "pattern_type": str,    # which pattern matched
        }
    """
    # Build a page lookup if we have page texts
    page_map = _build_page_map(full_text, page_texts) if page_texts else None

    # Find all section boundaries
    boundaries = _find_boundaries(full_text)

    if not boundaries:
        # No structure detected — treat entire document as one unit
        return [{
            "level": 1,
            "section_id": "full_document",
            "heading": "Full Document",
            "text": full_text.strip(),
            "page_start": 1,
            "page_end": len(page_texts) if page_texts else 1,
            "pattern_type": "none",
        }]

    # Split text into units based on boundaries
    units = _split_into_units(full_text, boundaries, page_map)

    return units


def _build_page_map(full_text, page_texts):
    """
    Build a character offset → page number mapping.
    This lets us figure out which page a given section falls on.
    """
    if not page_texts:
        return None

    page_map = []  # List of (start_offset, end_offset, page_number)
    current_offset = 0

    for page in page_texts:
        page_text = page["text"]
        # Find this page's text in the full text
        # (pages are joined with "\n\n" in text_cleaner.clean_pages)
        idx = full_text.find(page_text, current_offset)
        if idx == -1:
            # Fuzzy match — try first 50 chars
            snippet = page_text[:50]
            idx = full_text.find(snippet, current_offset)
            if idx == -1:
                idx = current_offset

        end_idx = idx + len(page_text)
        page_map.append((idx, end_idx, page["page_number"]))
        current_offset = end_idx

    return page_map


def _offset_to_page(offset, page_map):
    """Convert a character offset to a page number."""
    if not page_map:
        return 1

    for start, end, page_num in page_map:
        if start <= offset < end:
            return page_num

    # If past the end, return last page
    return page_map[-1][2] if page_map else 1


def _find_boundaries(text):
    """
    Scan through the text and find all section boundaries.
    Returns a list of (line_start_offset, level, section_id, heading, pattern_type).
    """
    boundaries = []
    lines = text.split('\n')
    offset = 0

    for line in lines:
        stripped = line.strip()

        if stripped:
            for pattern, level, ptype in STRUCTURE_PATTERNS:
                match = re.match(pattern, stripped)
                if match:
                    groups = match.groups()

                    if ptype == 'numbered_section_solo':
                        # Just a number like "1." on its own line
                        section_id = groups[0]
                        heading = ""  # heading will be on next line
                    elif ptype == 'caps_heading':
                        section_id = groups[0][:30]  # Use truncated heading as ID
                        heading = groups[0]
                    elif len(groups) >= 2:
                        section_id = groups[0]
                        heading = groups[1].strip() if groups[1] else ""
                    else:
                        section_id = groups[0]
                        heading = ""

                    boundaries.append((offset, level, section_id, heading, ptype))
                    break  # First matching pattern wins

        offset += len(line) + 1  # +1 for the \n

    return boundaries


def _split_into_units(text, boundaries, page_map):
    """
    Split the full text into structural units based on detected boundaries.
    Each unit gets the text from its boundary to the next boundary.
    """
    units = []

    # Handle text before the first boundary (preamble)
    if boundaries[0][0] > 0:
        preamble_text = text[:boundaries[0][0]].strip()
        if preamble_text and len(preamble_text) > 30:
            units.append({
                "level": 0,
                "section_id": "preamble",
                "heading": "Document Header / Preamble",
                "text": preamble_text,
                "page_start": _offset_to_page(0, page_map),
                "page_end": _offset_to_page(boundaries[0][0], page_map),
                "pattern_type": "preamble",
            })

    for i, (offset, level, section_id, heading, ptype) in enumerate(boundaries):
        # Text runs from this boundary to the next one (or end of document)
        if i + 1 < len(boundaries):
            next_offset = boundaries[i + 1][0]
        else:
            next_offset = len(text)

        section_text = text[offset:next_offset].strip()

        if not section_text:
            continue

        # For "numbered_section_solo" (e.g., "1.\n"), grab the heading from
        # the first non-empty line of the section text after the number
        if ptype == 'numbered_section_solo' and not heading:
            lines = section_text.split('\n')
            for line in lines[1:]:  # skip the number line itself
                if line.strip():
                    heading = line.strip()
                    break

        units.append({
            "level": level,
            "section_id": section_id,
            "heading": heading,
            "text": section_text,
            "page_start": _offset_to_page(offset, page_map),
            "page_end": _offset_to_page(next_offset - 1, page_map),
            "pattern_type": ptype,
        })

    return units
