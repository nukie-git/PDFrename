"""dry_run_rename.py (PDFrename v1.4.0)

Automated dry run scanner and preview generator for Bank Mandiri (KOPRA) transfer proofs
(Single Transfer & Multiple Transfer) and image-based scanned bon receipts (IMG_YYYYMMDD_*).

Scans target directory, extracts metadata via pypdf and RapidOCR, resolves filename collisions,
formats filenames, flags low-confidence fallback reads (with -missed suffix and warning flags),
renders a visual Markdown preview table, and saves a preview-locked snapshot mapping to
logs/pending_mapping.json for execute_rename.py.
"""

import os
import re
import glob
import json
from datetime import datetime
from pypdf import PdfReader

from logger import log, get_logs_dir

try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
except Exception:
    ocr_engine = None

MONTH_MAP = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
    'AGT': 8, 'AGO': 8
}

# Corrections for common OCR misreads of digits/separators. Applied only to the
# small local window around a candidate date match, never to the whole OCR text -
# otherwise a stray '108' or '&' anywhere else on the page (a price, an account
# fragment) gets silently mangled too.
DATE_FIX_MAP = [
    ('l0', '10'), ('I0', '10'), ('4108', '04 08'), ('24.101', '24 08 '),
    ('1081', '08'), ('108', '08'), ('0f1', '07'), ('0f', '07'), ('&', '8'),
]

# Words that show up near a vendor header/logo on these bons but are never
# themselves the vendor name - filtered out of header-line candidates.
VENDOR_STOPWORDS = {
    'BON', 'NAMA', 'PEMESANAN', 'ALAMAT', 'BANDUNG', 'TOTAL', 'KETERANGAN',
    'TANDA', 'TERIMA', 'HORMAT', 'KAMI', 'CUSTOMER', 'LUNAS', 'FINANCE',
    'TELP', 'JL', 'GG', 'NO', 'RP',
}

PENDING_FILE = 'pending_mapping.json'
WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}
MAX_STEM_LEN = 150  # leaves headroom under Windows' 260-char path limit


def normalize_name(name):
    """Normalize receiver name to Title Case (e.g. 'DEDE MADIN' -> 'Dede Madin')."""
    return name.title()


def sanitize_component(text):
    """Strip characters/patterns that are illegal or problematic in Windows filenames."""
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    text = text.strip(' .')  # Windows disallows trailing dots/spaces
    if text.upper() in WINDOWS_RESERVED:
        text = f'_{text}'
    return text


def get_pending_path():
    return os.path.join(get_logs_dir(), PENDING_FILE)


def save_pending_mapping(directory, mapping):
    """Persist the exact mapping shown in the preview so execute_rename.py applies
    that mapping instead of silently re-deriving a (possibly different) one."""
    clean_dir = os.path.abspath(os.path.expandvars(os.path.expanduser(directory)))
    payload = {
        'directory': clean_dir,
        'generated_at': datetime.now().isoformat(),
        'mapping': mapping,
    }
    try:
        with open(get_pending_path(), 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        log(f"Saved pending rename mapping snapshot to: {get_pending_path()}", "INFO")
    except Exception as e:
        log(f"Failed to write pending mapping snapshot: {e}", "ERROR")


# --- OCR ---------------------------------------------------------------

def run_ocr(reader):
    """Run OCR once per document and return every recognized line with its
    vertical position, so both date and vendor extraction can share one pass
    instead of paying the OCR cost twice."""
    if not ocr_engine:
        return None
    lines_with_pos = []
    try:
        for page in reader.pages:
            for img in page.images:
                res, _ = ocr_engine(img.data)
                if res:
                    for box, text, score in res:
                        y = min(point[1] for point in box)
                        lines_with_pos.append((text, y))
    except Exception as e:
        log(f"OCR pass failed: {e}", "WARNING")
        return None
    if not lines_with_pos:
        return None
    lines_with_pos.sort(key=lambda t: t[1])  # top of page first
    full_text = '\n'.join(t for t, _ in lines_with_pos)
    return {'lines': lines_with_pos, 'full_text': full_text}


def _fix_ocr_digits(span):
    for old, new in DATE_FIX_MAP:
        span = span.replace(old, new)
    return span


def extract_ocr_date_from_text(full_text):
    """Multi-layer date parsing: printed LUNAS stamp date first, then handwritten
    date field fallback. Returns (date_formatted, source) where source is
    'ocr_stamp' or 'ocr_handwritten', or (None, None) if nothing usable found."""
    if not full_text:
        return None, None

    cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', full_text)

    # Anchor year: look anywhere in the OCR text for a plausible printed year
    # (typically visible near the LUNAS stamp) so a handwritten date missing
    # its year, or a stamp match that fails to capture one, doesn't have to
    # fall back to a hardcoded year.
    anchor_year = None
    year_candidates = re.findall(r'\b20\d{2}\b', cleaned)
    if year_candidates:
        anchor_year = int(year_candidates[0])

    # 1. Try LUNAS stamp date matching (e.g. '10 AUG 2026', '24 AUG 2026')
    for match in re.finditer(r'(\d{1,2})\s*([A-Za-z]{3,9})\s*([Gg]?\d{4})?', cleaned, re.IGNORECASE):
        day_str, month_str, year_str = match.groups()
        m_upper = month_str.upper()[:3]
        if m_upper in MONTH_MAP:
            m = MONTH_MAP[m_upper]
            d = int(day_str)
            if 1 <= d <= 31:
                if year_str:
                    clean_y = re.sub(r'\D', '', year_str)
                    y = int(clean_y) if len(clean_y) == 4 else (int(clean_y) + 2000 if len(clean_y) == 2 else (anchor_year or datetime.now().year))
                else:
                    y = anchor_year or datetime.now().year
                try:
                    return datetime(y, m, d).strftime('%Y%m%d'), 'ocr_stamp'
                except ValueError:
                    pass

    # 2. Try date pattern after 'Bandung,' or anywhere in text, applying OCR-noise
    # corrections only to the small window around each candidate match.
    for m in re.finditer(r'\S{0,4}\d\S{0,3}\d\S{0,3}\d{2,4}\S{0,2}', cleaned):
        fixed = _fix_ocr_digits(m.group(0))
        dm = re.search(r'(\d{1,2})\s*[\/\.-]\s*(\d{1,2})\s*[\/\.-]\s*(\d{2,4})', fixed)
        if not dm:
            continue
        d, month, y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        if y < 100:
            y = anchor_year if (anchor_year and anchor_year % 100 == y) else y + 2000
        if 1 <= d <= 31 and 1 <= month <= 12:
            try:
                return datetime(y, month, d).strftime('%Y%m%d'), 'ocr_handwritten'
            except ValueError:
                pass

    return None, None


def extract_ocr_vendor(ocr_lines_sorted):
    """Best-effort vendor name from the header area of a scanned bon (the topmost
    plausible text lines). Heuristic, not reliable OCR of a logo/stylized header -
    callers should treat a None/low-confidence result as 'use the default'."""
    candidates = []
    for text, y in ocr_lines_sorted[:8]:
        # These labels always identify the customer/orderer on this receipt
        # template, never the vendor - drop the whole line rather than only the
        # label word, so a line like 'Nama Pemesanan : SPPG Baleendah' can't be
        # mistaken for the vendor name just because 'SPPG Baleendah' itself
        # isn't a stopword.
        if re.search(r'\b(Nama|Alamat)\s+Pemesanan\b', text, re.IGNORECASE):
            continue
        cleaned = re.sub(r'[^A-Za-z.\s]', ' ', text).strip()
        if len(cleaned) < 4:
            continue
        words = [w for w in cleaned.upper().split() if w not in VENDOR_STOPWORDS]
        if not words:
            continue
        alpha_ratio = sum(c.isalpha() or c in ' .' for c in cleaned) / max(len(cleaned), 1)
        if alpha_ratio < 0.7:
            continue
        candidates.append((y, cleaned))

    if not candidates:
        return None

    for y, cleaned in candidates:
        if re.search(r'\bPT\b|\bCV\b|\bTOKO\b|\bAGEN\b|\bUD\b', cleaned.upper()):
            return _normalize_vendor_name(cleaned)

    candidates.sort(key=lambda c: c[0])
    return _normalize_vendor_name(candidates[0][1])


def _normalize_vendor_name(raw):
    raw = re.sub(r'^(PT\.?|CV\.?|UD\.?)\s*', '', raw.strip(), flags=re.IGNORECASE)
    for word in VENDOR_NAME_STRIP_WORDS:
        raw = re.sub(re.escape(word), '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\s+', ' ', raw).strip()
    return raw.title()


# Words dropped from the vendor name wherever it comes from (OCR or default) -
# kept out of the rename template on request even though it's part of the
# vendor's legal/printed name.
VENDOR_NAME_STRIP_WORDS = {'SABILULUNGAN'}

DEFAULT_BON_VENDOR = 'Bentang'


# --- Main mapping --------------------------------------------------------

def get_rename_mapping(directory='.'):
    directory = os.path.expandvars(os.path.expanduser(directory))
    log(f"Starting dry run scan on directory: {directory}", "INFO")

    pdf_files = glob.glob(os.path.join(directory, '*.pdf'))
    log(f"Found {len(pdf_files)} PDF file(s) in target directory.", "INFO")

    raw_items = []
    error_items = []

    for f in sorted(pdf_files):
        filename = os.path.basename(f)
        try:
            reader = PdfReader(f)
            text = '\n'.join([page.extract_text() for page in reader.pages])

            # Check if file matches IMG_YearMonthDate_* pattern (e.g. IMG_20260806_0001.pdf)
            img_match = re.match(r'^IMG_(\d{8})_.*\.pdf$', filename, re.IGNORECASE)
            if img_match:
                date_formatted = None
                date_source = None

                if text:
                    doc_date_match = re.search(r'(\d{1,2})\s*[\/\.-]\s*(\d{1,2})\s*[\/\.-]\s*(\d{2,4})', text)
                    if doc_date_match:
                        day_str, month_str, year_str = doc_date_match.groups()
                        if len(year_str) == 2:
                            year_str = "20" + year_str
                        try:
                            dt = datetime.strptime(f'{year_str}{month_str.zfill(2)}{day_str.zfill(2)}', '%Y%m%d')
                            date_formatted = dt.strftime('%Y%m%d')
                            date_source = 'text_layer'
                        except ValueError:
                            pass

                ocr_data = None
                if not date_formatted:
                    if ocr_engine:
                        ocr_data = run_ocr(reader)
                        if ocr_data:
                            date_formatted, date_source = extract_ocr_date_from_text(ocr_data['full_text'])
                    else:
                        log(f"OCR engine unavailable for '{filename}' - rapidocr-onnxruntime not installed/loaded.", "WARNING")

                date_warning = None
                if not date_formatted:
                    date_formatted = img_match.group(1)
                    date_source = 'filename_fallback'
                    if not ocr_engine:
                        date_warning = "OCR engine unavailable - using scan filename date, NOT the transaction date"
                    else:
                        date_warning = "OCR found no readable date - using scan filename date, NOT the transaction date"

                vendor_name = DEFAULT_BON_VENDOR
                vendor_warning = None
                if ocr_data:
                    detected_vendor = extract_ocr_vendor(ocr_data['lines'])
                    if detected_vendor:
                        vendor_name = detected_vendor
                    else:
                        vendor_warning = "Vendor header OCR inconclusive - using default vendor name"
                elif not ocr_engine:
                    vendor_warning = "OCR engine unavailable - using default vendor name"

                safe_vendor = sanitize_component(vendor_name)
                is_fallback = bool(date_warning or vendor_warning)
                missed_suffix = "-missed" if is_fallback else ""
                base_stem = f"bon_{safe_vendor.lower().replace(' ', '_')}_{date_formatted}{missed_suffix}"
                if len(base_stem) > MAX_STEM_LEN:
                    base_stem = base_stem[:MAX_STEM_LEN].rstrip(' ._')

                raw_items.append({
                    'original': filename,
                    'full_original': f,
                    'date': date_formatted,
                    'date_source': date_source,
                    'receiver': vendor_name,
                    'remark': 'Bon',
                    'is_img_bon': True,
                    'base_stem': base_stem,
                    'warnings': [w for w in (date_warning, vendor_warning) if w],
                })
                continue

            # Skip if the document is not a valid transaction receipt of the expected types
            if not re.search(r'(Single Transfer [Tt]o (Other Bank|Mandiri)|Multiple Transfer [Bb]y (Manual Input|File Upload)|Multiple Transfer)', text, re.IGNORECASE):
                continue

            mandiri_warnings = []

            # Extract Creation Date, Execution Date, or Instruction Date
            date_match1 = re.search(r'(?:Creation|Execution|Instruction) Date\s+([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', text)
            date_match2 = re.search(r'(?:Creation|Execution|Instruction) Date\s+(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})', text)

            if date_match1:
                month_str, day_str, year_str = date_match1.groups()
                m_str = month_str[:3].title()
                dt = datetime.strptime(f'{m_str} {day_str.zfill(2)} {year_str}', '%b %d %Y')
                date_formatted = dt.strftime('%Y%m%d')
            elif date_match2:
                day_str, month_str, year_str = date_match2.groups()
                m_str = month_str[:3].title()
                dt = datetime.strptime(f'{day_str.zfill(2)} {m_str} {year_str}', '%d %b %Y')
                date_formatted = dt.strftime('%Y%m%d')
            else:
                date_formatted = 'UNKNOWN_DATE'
                mandiri_warnings.append("Could not find/parse date field - date left as UNKNOWN_DATE")

            dest_match = re.search(r'(?:Destination Account|Credit Account Number)\s+\d+(?:\s+[A-Za-z]{3})?\s+([^\r\n]+)', text)
            if dest_match:
                raw_receiver = dest_match.group(1).strip()
                raw_receiver = re.sub(r'^[A-Z]{3}\s+', '', raw_receiver)
            else:
                raw_receiver = 'UNKNOWN_RECEIVER'
                mandiri_warnings.append("Could not find account field - receiver left as UNKNOWN_RECEIVER")
            receiver = normalize_name(raw_receiver)

            remark_match = re.search(r'Remark\s+([^\r\n]+)', text)
            if remark_match:
                remark = remark_match.group(1).strip()
            else:
                remark = 'Transfer'

            safe_receiver = sanitize_component(receiver)
            safe_remark = sanitize_component(remark)

            raw_items.append({
                'original': filename,
                'full_original': f,
                'date': date_formatted,
                'receiver': receiver,
                'remark': remark,
                'safe_receiver': safe_receiver,
                'safe_remark': safe_remark,
                'warnings': mandiri_warnings,
            })
        except Exception as e:
            log(f"Error reading PDF '{filename}': {e}", "ERROR")
            error_msg = str(e)
            try:
                if PdfReader(f).is_encrypted:
                    error_msg = "PDF is password-protected/encrypted - cannot read without a password"
            except Exception:
                pass
            error_items.append({
                'original': filename,
                'error': error_msg
            })

    # Collision resolution
    try:
        existing_on_disk = {f.lower() for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))}
    except Exception:
        existing_on_disk = set()

    originals_in_batch = {item['original'].lower() for item in raw_items}
    external_existing = existing_on_disk - originals_in_batch

    used_names = set(external_existing)
    mapping = []

    for item in raw_items:
        if item.get('is_img_bon'):
            base_stem = item['base_stem']
        else:
            base_stem = f"{item['date']} {item['safe_receiver']} {item['safe_remark']}"
            if len(base_stem) > MAX_STEM_LEN:
                base_stem = base_stem[:MAX_STEM_LEN].rstrip(' .')
        base_filename = f"{base_stem}.pdf"

        if base_filename.lower() in used_names:
            counter = 1
            while True:
                candidate_filename = f"{base_stem} ({counter}).pdf"
                if candidate_filename.lower() not in used_names:
                    break
                counter += 1
            new_filename = candidate_filename
            is_conflict = True
            log(f"Conflict detected for '{item['original']}'. Resolved to '{new_filename}'.", "WARNING")
        else:
            new_filename = base_filename
            is_conflict = False

        used_names.add(new_filename.lower())

        mapping.append({
            'original': item['original'],
            'new': new_filename,
            'full_original': item['full_original'],
            'full_new': os.path.join(directory, new_filename),
            'date': item['date'],
            'receiver': item['receiver'],
            'remark': item['remark'],
            'conflict': is_conflict,
            'warnings': item.get('warnings', []),
        })

    mapping.extend(error_items)
    log(f"Dry run complete. Found {len(mapping)} eligible transaction receipt(s).", "INFO")
    return mapping


def print_markdown_preview(mapping):
    has_conflicts = any(item.get('conflict', False) for item in mapping)
    has_warnings = any(item.get('warnings') for item in mapping)

    print("\n### Rename Preview Table\n")
    if has_conflicts:
        print("> [!WARNING]")
        print("> **FILENAME CONFLICTS DETECTED**: One or more proposed filenames collided with existing files or duplicate receipts.")
        print("> Suffixes like `(1)`, `(2)`, `(3)` have been automatically appended to resolve collisions.\n")
    if has_warnings:
        print("> [!CAUTION]")
        print("> **LOW-CONFIDENCE EXTRACTION**: One or more rows below were built from a fallback guess, not a confirmed read. Check the `!` rows before approving.\n")

    print("| Original Filename | Proposed New Filename | Receiver (Normalized) | Remark |")
    print("| :--- | :--- | :--- | :--- |")
    for item in mapping:
        if 'error' in item:
            print(f"| `{item['original']}` | Error: {item['error']} | - | - |")
        else:
            conflict_flag = " *(conflict resolved)*" if item.get('conflict') else ""
            warn_flag = " ⚠️" if item.get('warnings') else ""
            print(f"| `{item['original']}` | `{item['new']}`{conflict_flag}{warn_flag} | {item['receiver']} | {item['remark']} |")
            for w in item.get('warnings', []):
                print(f"|   | ⚠️ *{w}* | | |")
    print()


if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    mapping = get_rename_mapping(target_dir)
    if not mapping:
        print("No eligible PDF files to rename exist in target folder.")
        sys.exit(2)
    print_markdown_preview(mapping)
    save_pending_mapping(target_dir, mapping)
    has_conflicts = any(item.get('conflict', False) for item in mapping)
    if has_conflicts:
        sys.exit(3)
