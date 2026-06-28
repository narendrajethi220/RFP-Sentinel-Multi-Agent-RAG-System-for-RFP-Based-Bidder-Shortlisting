"""
Text Cleaner for Government Documents
--------------------------------------
Cleans raw PDF-extracted text by:
  1. Stripping Hindi/Devanagari characters
  2. Removing repeated page headers and footers
  3. Normalizing whitespace while preserving paragraph structure
  4. Removing PDF parsing artifacts
"""

import re


class TextCleaner:

    def __init__(self):
        # Common header patterns found in government PDFs
        # These repeat on every page and add noise
        self.header_patterns = [
            # "Page 1 of 52", "Page | 1", "1 / 12" etc.
            r'Page\s*\|?\s*\d+\s*(of\s*\d+)?',
            r'\d+\s*/\s*\d+',
            # Repeated document title headers (GeM GTC style)
            r'General Terms and Conditions on GeM.*?dt\s+\d+.*?\d{4}\s*',
        ]

    def strip_hindi(self, text):
        """Remove Devanagari script and related Unicode characters.
        
        Government PDFs like GeM Bid Documents use bilingual labels:
          "Ministry/State Name/मंत्रालय/राज्य का नाम"
        After stripping Hindi, we clean up leftover fragments.
        """
        # Step 1: Remove control characters first (they're embedded in Hindi text)
        # \x01, \x0f, \x12 etc. appear inside Devanagari words in GeM bid docs
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

        # Step 2: Remove Devanagari script
        # Devanagari block: U+0900 to U+097F
        # Devanagari Extended: U+A8E0 to U+A8FF
        # Vedic Extensions: U+1CD0 to U+1CFF
        text = re.sub(r'[\u0900-\u097F\uA8E0-\uA8FF\u1CD0-\u1CFF]+', '', text)

        # Step 3: Clean up bilingual label artifacts
        # "English Label/हिंदी" → "English Label/" → "English Label"
        # Remove trailing slash at end of labels
        text = re.sub(r'/\s*\n', '\n', text)
        text = re.sub(r'/\s*/', '/', text)

        # Step 4: Remove orphan short lines (1-4 chars) that are just leftover junk
        # After Hindi removal, lines like "!", "%", "' " are left
        text = re.sub(r'^\s*[^a-zA-Z0-9\n]{1,4}\s*$', '', text, flags=re.MULTILINE)

        # Remove short lines (under 20 chars) where no word is longer than 2 chars
        # These are Hindi translation remnants: "% % (3 - )", "6 S S", "< d 7 %", "23 %"
        # But keep meaningful short lines like "Yes", "No", "486", "180 (Days)"
        def _is_junk_line(match):
            line = match.group(0).strip()
            if not line:
                return True
            # Keep lines with any word of 3+ letters (meaningful English)
            words = re.findall(r'[a-zA-Z]+', line)
            if any(len(w) >= 3 for w in words):
                return False
            # Keep pure numbers (quantities, years, etc.)
            if re.match(r'^\d+$', line):
                return False
            # Keep section references: "1.", "2.5", "2.5.1", "(a)", "(1)", "a."
            if re.match(r'^\d+\.(\d+\.?)*$', line):
                return False
            if re.match(r'^\([a-zA-Z0-9]+\)$', line):
                return False
            # Keep dates: "03-01-2025 19:00:00"
            if re.search(r'\d{2}[-/]\d{2}[-/]\d{4}', line):
                return False
            # Keep number + unit: "180 (Days)", "139 Lakh (s)"
            if re.search(r'\d+\s*\(', line):
                return False
            # Everything else short with no real words is junk
            return True

        text = re.sub(
            r'^.{1,15}$',
            lambda m: '' if _is_junk_line(m) else m.group(0),
            text, flags=re.MULTILINE
        )

        # Clean up trailing slash+junk from bilingual labels
        # "bidder (For 3 Years)/ '" → "bidder (For 3 Years)"
        text = re.sub(r'/\s*[^\sa-zA-Z0-9]{1,3}\s*$', '', text, flags=re.MULTILINE)

        # Clean up empty parentheses: "( )" or "(  )" or "( - )"
        text = re.sub(r'\(\s*[-\s]*\)', '', text)

        return text

    def remove_headers_footers(self, text):
        """Remove repeated page headers and footers."""
        for pattern in self.header_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text

    def normalize_whitespace(self, text):
        """
        Normalize whitespace while preserving paragraph breaks.
        - Multiple blank lines → single blank line (paragraph break)
        - Multiple spaces → single space
        - Strip trailing whitespace per line
        """
        # Replace tabs with spaces
        text = text.replace('\t', ' ')

        # Collapse multiple spaces on the same line into one
        text = re.sub(r'[^\S\n]+', ' ', text)

        # Strip trailing/leading whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # Collapse 3+ consecutive newlines into 2 (one blank line = paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def clean_pdf_artifacts(self, text):
        """Remove common PDF extraction artifacts."""
        # Control characters are already removed in strip_hindi()
        # This handles remaining visual artifacts

        # Remove bullet-like artifacts (single special chars on their own)
        text = re.sub(r'^\s*[\u2022\u2023\u25E6\u2043\u2219]\s*$', '', text, flags=re.MULTILINE)

        # Remove lines that are just dashes, underscores, or equals (decorative separators)
        text = re.sub(r'^\s*[-_=]{10,}\s*$', '', text, flags=re.MULTILINE)

        # Remove lines that are just asterisks (end-of-document markers like "***")
        text = re.sub(r'^\s*\*{2,}\s*$', '', text, flags=re.MULTILINE)

        return text

    def clean(self, text):
        """
        Full cleaning pipeline. Order matters:
        1. Strip Hindi first (before whitespace normalization)
        2. Remove headers/footers
        3. Clean PDF artifacts
        4. Normalize whitespace last
        """
        text = self.strip_hindi(text)
        text = self.remove_headers_footers(text)
        text = self.clean_pdf_artifacts(text)
        text = self.normalize_whitespace(text)
        return text

    def clean_pages(self, pages):
        """
        Clean a list of pages from PDFLoader.
        Input:  [{"page_number": 1, "text": "..."}, ...]
        Output: [{"page_number": 1, "text": "cleaned..."}, ...]
        Also returns the full joined text for structure parsing.
        """
        cleaned_pages = []
        full_text_parts = []

        for page in pages:
            cleaned_text = self.clean(page["text"])

            # Skip empty pages after cleaning
            if not cleaned_text.strip():
                continue

            cleaned_pages.append({
                "page_number": page["page_number"],
                "text": cleaned_text
            })
            full_text_parts.append(cleaned_text)

        full_text = "\n\n".join(full_text_parts)

        return cleaned_pages, full_text
