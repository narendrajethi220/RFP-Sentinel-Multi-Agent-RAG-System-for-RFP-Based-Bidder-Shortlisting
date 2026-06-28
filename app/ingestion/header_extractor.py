"""
Header Extractor for Government Documents
--------------------------------------------
Extracts document metadata from the first 1-2 pages:
  - Document title
  - Document category (inferred from keywords in title/header)
  - Issuing authority (ministry/department name)

Uses simple keyword matching for Phase 1 — no LLM needed.
"""

import re


# Category classification rules
# Each tuple: (keywords_to_match, category_name)
# Checked in order — first match wins
CATEGORY_RULES = [
    # GeM-specific
    (["gem", "government e-marketplace", "government emarketplace"], "GeM"),
    (["general terms and conditions", "gtc"], "GeM General Terms and Conditions"),
    (["bid document", "bid details", "bid number"], "GeM Bid Document"),
    (["invitation to bid", "itb", "information to bidder"], "GeM ITB"),
    (["additional terms and conditions", "atc"], "GeM Additional Terms and Conditions"),
    (["special terms and conditions", "stc"], "GeM Special Terms and Conditions"),

    # BIS / Standards
    (["bureau of indian standards", "bis", "indian standard"], "BIS Standards"),
    (["compulsory registration", "crs scheme"], "BIS CRS"),
    (["testing", "test report", "test lab"], "BIS Testing"),

    # MSME / Enterprise
    (["micro and small enterprises", "mse", "msme", "msmed"], "MSME Policy"),
    (["startup", "start-up", "start up"], "Startup Policy"),
    (["public procurement policy"], "Public Procurement Policy"),

    # DPIIT
    (["dpiit", "department for promotion of industry"], "DPIIT Policy"),
    (["make in india"], "Make in India Policy"),

    # General Government
    (["general financial rules", "gfr"], "GFR"),
    (["central vigilance commission", "cvc"], "CVC Guidelines"),
    (["tender", "rfp", "request for proposal"], "Tender/RFP"),
]


def extract_header(first_page_text, filename=""):
    """
    Extract document metadata from the first page text.
    
    Args:
        first_page_text: Cleaned text of the first page
        filename: Original filename (used as fallback for categorization)
    
    Returns:
        dict with:
        {
            "document_title": str,
            "document_category": str,
            "issuing_authority": str,
        }
    """
    title = _extract_title(first_page_text)
    category = _classify_category(first_page_text, filename, title)
    authority = _extract_authority(first_page_text)

    return {
        "document_title": title,
        "document_category": category,
        "issuing_authority": authority,
    }


def _extract_title(text):
    """
    Extract the document title from the first page.
    Strategy: Prefer longer lines with title keywords (more descriptive),
    then fall back to shorter keyword lines, then first substantial line.
    """
    lines = text.strip().split('\n')
    
    title_keywords = [
        'terms and conditions', 'policy', 'order', 'guidelines',
        'handbook', 'bid document', 'invitation to bid',
        'information to bidder', 'tender', 'rfp', 'annexure',
        'additional terms', 'special terms', 'procurement',
    ]

    # First pass: look for LONG lines (20+ chars) with title keywords
    # These are the most descriptive titles
    for line in lines[:15]:
        stripped = line.strip()
        if not stripped or len(stripped) < 20:
            continue
        lower = stripped.lower()
        if any(kw in lower for kw in title_keywords):
            return stripped

    # Second pass: shorter lines with keywords
    for line in lines[:15]:
        stripped = line.strip()
        if not stripped or len(stripped) < 5:
            continue
        lower = stripped.lower()
        if any(kw in lower for kw in title_keywords):
            return stripped

    # Third pass: first substantial line (likely the title)
    for line in lines[:10]:
        stripped = line.strip()
        if stripped and len(stripped) > 10:
            return stripped

    return "Unknown Document"


def _classify_category(text, filename, title):
    """
    Classify the document into a category using keyword matching.
    Checks title, first page text, and filename.
    """
    # Combine all sources for matching
    search_text = f"{title} {text[:2000]} {filename}".lower()

    for keywords, category in CATEGORY_RULES:
        if any(kw in search_text for kw in keywords):
            return category

    return "Government Document"  # default fallback


def _extract_authority(text):
    """
    Extract the issuing authority (ministry/department) from the first page.
    """
    authority_patterns = [
        r'(?:Ministry\s+of\s+)([A-Z][A-Za-z,\s&]+?)(?:\n|$)',
        r'(?:Department\s+of\s+)([A-Z][A-Za-z,\s&]+?)(?:\n|$)',
        r'(?:Office\s+of\s+)([A-Z][A-Za-z,\s&]+?)(?:\n|$)',
        r'(?:Government\s+of\s+)([A-Z][A-Za-z,\s&]+?)(?:\n|$)',
        r'(?:Issued\s+by\s*\n?)([A-Z][A-Za-z,\s&\n]+?)(?:\n\n|$)',
    ]

    for pattern in authority_patterns:
        match = re.search(pattern, text[:1500])
        if match:
            authority = match.group(1).strip()
            # Clean up multiline matches
            authority = ' '.join(authority.split())
            if len(authority) > 10:
                return authority

    return ""
