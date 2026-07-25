import os
import re
import glob
from datetime import datetime
from pypdf import PdfReader

def normalize_name(name):
    """Normalize receiver name to Title Case (e.g. 'DEDE MADIN' -> 'Dede Madin')."""
    return name.title()

def get_rename_mapping(directory='.'):
    pdf_files = glob.glob(os.path.join(directory, '*.pdf'))
    mapping = []

    for f in sorted(pdf_files):
        filename = os.path.basename(f)
        try:
            reader = PdfReader(f)
            text = '\n'.join([page.extract_text() for page in reader.pages])
            
            # Skip if the document is not a valid transaction receipt of the expected types
            if "Transaction Status Single Transfer to Other Bank" not in text and "Transaction Status Single Transfer to Mandiri" not in text:
                continue
            
            # Extract Creation Date
            # Format 1: MMM DD, YYYY (e.g. Jul 21, 2026)
            date_match1 = re.search(r'Creation Date\s+([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})', text)
            # Format 2: DD MMM YYYY (e.g. 23 Jul 2026)
            date_match2 = re.search(r'Creation Date\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', text)
            
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
            
            new_filename = f"{date_formatted} {safe_receiver} {safe_remark}.pdf"
            mapping.append({
                'original': filename,
                'new': new_filename,
                'full_original': f,
                'full_new': os.path.join(directory, new_filename),
                'date': date_formatted,
                'receiver': receiver,
                'remark': remark
            })
        except Exception as e:
            mapping.append({
                'original': filename,
                'error': str(e)
            })
            
    return mapping

def print_markdown_preview(mapping):
    print("\n### Rename Preview Table\n")
    print("| Original Filename | Proposed New Filename | Receiver (Normalized) | Remark |")
    print("| :--- | :--- | :--- | :--- |")
    for item in mapping:
        if 'error' in item:
            print(f"| `{item['original']}` | Error: {item['error']} | - | - |")
        else:
            print(f"| `{item['original']}` | `{item['new']}` | {item['receiver']} | {item['remark']} |")
    print()

if __name__ == '__main__':
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    mapping = get_rename_mapping(target_dir)
    if not mapping:
        print("No eligible PDF files to rename exist in target folder.")
        sys.exit(2)
    print_markdown_preview(mapping)
