import os
import re
import glob
import json
from datetime import datetime
from pypdf import PdfReader

from logger import log

try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
except Exception:
    ocr_engine = None

def extract_ocr_date_from_pdf(reader):
    """Extract date from scanned PDF bon using OCR on page images."""
    if not ocr_engine:
        return None
    try:
        for page in reader.pages:
            for img in page.images:
                res, _ = ocr_engine(img.data)
                if not res:
                    continue
                for line in res:
                    txt = line[1]
                    if 'bandung' in txt.lower():
                        sub = re.sub(r'Bandung,?\s*', '', txt, flags=re.IGNORECASE)
                        sub = (sub.replace('4108', '04 08')
                                  .replace('1081', '08')
                                  .replace('108', '08')
                                  .replace('0f1', '07')
                                  .replace('0f', '07')
                                  .replace('&', '8'))
                        groups = re.findall(r'\d+', sub)
                        if len(groups) >= 3:
                            d, m, y = int(groups[0]), int(groups[1]), int(groups[2])
                            if y < 100:
                                y += 2000
                            try:
                                dt = datetime(y, m, d)
                                return dt.strftime('%Y%m%d')
                            except ValueError:
                                pass
    except Exception as e:
        log(f"OCR date extraction warning: {e}", "WARNING")
    return None

def normalize_name(name):
    """Normalize receiver name to Title Case (e.g. 'DEDE MADIN' -> 'Dede Madin')."""
    return name.title()

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
                if text:
                    # Try to extract date from text if available (e.g. 28/07/26, 28-07-2026)
                    doc_date_match = re.search(r'(\d{1,2})\s*[\/\.-]\s*(\d{1,2})\s*[\/\.-]\s*(\d{2,4})', text)
                    if doc_date_match:
                        day_str, month_str, year_str = doc_date_match.groups()
                        if len(year_str) == 2:
                            year_str = "20" + year_str
                        try:
                            dt = datetime.strptime(f'{year_str}{month_str.zfill(2)}{day_str.zfill(2)}', '%Y%m%d')
                            date_formatted = dt.strftime('%Y%m%d')
                        except ValueError:
                            pass
                
                # If no text date found, perform OCR on the PDF image
                if not date_formatted:
                    date_formatted = extract_ocr_date_from_pdf(reader)

                # Fallback to date in filename if OCR fails or returns None
                if not date_formatted:
                    date_formatted = img_match.group(1)
                
                raw_items.append({
                    'original': filename,
                    'full_original': f,
                    'date': date_formatted,
                    'receiver': 'Bentang Sabilulungan',
                    'remark': 'Bon',
                    'is_img_bon': True,
                    'base_stem': f"bon_bentang_{date_formatted}"
                })
                continue

            # Skip if the document is not a valid transaction receipt of the expected types
            if not re.search(r'Single Transfer [Tt]o (Other Bank|Mandiri)', text, re.IGNORECASE):
                continue
            
            # Extract Creation Date
            # Format 1: MMM DD, YYYY (e.g. Jul 21, 2026)
            date_match1 = re.search(r'Creation Date\s+([A-Za-z]{3})\s+(\d{1,2}),?\s+(\d{4})', text)
            # Format 2: DD MMM YYYY (e.g. 26 Jul 2026)
            date_match2 = re.search(r'Creation Date\s+(\d{1,2})\s+([A-Za-z]{3}),?\s+(\d{4})', text)
            
            if date_match1:
                month_str, day_str, year_str = date_match1.groups()
                dt = datetime.strptime(f'{month_str} {day_str} {year_str}', '%b %d %Y')
                date_formatted = dt.strftime('%Y%m%d')
            elif date_match2:
                day_str, month_str, year_str = date_match2.groups()
                dt = datetime.strptime(f'{day_str} {month_str} {year_str}', '%d %b %Y')
                date_formatted = dt.strftime('%Y%m%d')
            else:
                date_formatted = 'UNKNOWN_DATE'
                
            # Extract Destination Account (account number stripped)
            dest_match = re.search(r'Destination Account\s+\d+\s+([^\r\n]+)', text)
            raw_receiver = dest_match.group(1).strip() if dest_match else 'UNKNOWN_RECEIVER'
            receiver = normalize_name(raw_receiver)
            
            # Extract Remark
            remark_match = re.search(r'Remark\s+([^\r\n]+)', text)
            remark = remark_match.group(1).strip() if remark_match else 'UNKNOWN_REMARK'
            
            # Clean filename from invalid characters
            safe_receiver = re.sub(r'[\\/*?:"<>|]', '', receiver)
            safe_remark = re.sub(r'[\\/*?:"<>|]', '', remark)
            
            raw_items.append({
                'original': filename,
                'full_original': f,
                'date': date_formatted,
                'receiver': receiver,
                'remark': remark,
                'safe_receiver': safe_receiver,
                'safe_remark': safe_remark
            })
        except Exception as e:
            log(f"Error reading PDF '{filename}': {e}", "ERROR")
            error_items.append({
                'original': filename,
                'error': str(e)
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
            'conflict': is_conflict
        })

    mapping.extend(error_items)
    log(f"Dry run complete. Found {len(mapping)} eligible transaction receipt(s).", "INFO")
    return mapping

def print_markdown_preview(mapping):
    has_conflicts = any(item.get('conflict', False) for item in mapping)

    print("\n### Rename Preview Table\n")
    if has_conflicts:
        print("> [!WARNING]")
        print("> **FILENAME CONFLICTS DETECTED**: One or more proposed filenames collided with existing files or duplicate receipts.")
        print("> Suffixes like `(1)`, `(2)`, `(3)` have been automatically appended to resolve collisions.\n")

    print("| Original Filename | Proposed New Filename | Receiver (Normalized) | Remark |")
    print("| :--- | :--- | :--- | :--- |")
    for item in mapping:
        if 'error' in item:
            print(f"| `{item['original']}` | Error: {item['error']} | - | - |")
        else:
            conflict_flag = " *(conflict resolved)*" if item.get('conflict') else ""
            print(f"| `{item['original']}` | `{item['new']}`{conflict_flag} | {item['receiver']} | {item['remark']} |")
    print()

def save_cache(mapping, directory='.'):
    cache_path = os.path.join(directory, '.rename_cache.json')
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2)
        log(f"Saved rename mapping cache to: {cache_path}", "INFO")
    except Exception as e:
        log(f"Failed to save rename cache: {e}", "WARNING")

if __name__ == '__main__':
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    mapping = get_rename_mapping(target_dir)
    if not mapping:
        print("No eligible PDF files to rename exist in target folder.")
        sys.exit(2)
    save_cache(mapping, target_dir)
    print_markdown_preview(mapping)
    has_conflicts = any(item.get('conflict', False) for item in mapping)
    if has_conflicts:
        sys.exit(3)
