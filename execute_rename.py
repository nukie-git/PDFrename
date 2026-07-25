import os
from dry_run_rename import get_rename_mapping

def rename_files(directory='.'):
    mapping = get_rename_mapping(directory)
    renamed_count = 0
    
    print("--- EXECUTING RENAME ---")
    for item in mapping:
        if 'error' in item:
            print(f"[SKIP] {item['original']}: {item['error']}")
            continue
            
        old_path = item['full_original']
        new_path = item['full_new']
        
        if item['original'] == item['new']:
            print(f"[NO CHANGE] {item['original']}")
            continue
            
        try:
            # On Windows, renaming a file to a case-only change requires a 2-step rename
            temp_path = old_path + ".tmp_rename"
            os.rename(old_path, temp_path)
            os.rename(temp_path, new_path)
            print(f"[RENAMED] {item['original']} -> {item['new']}")
            renamed_count += 1
        except Exception as e:
            print(f"[ERROR] Could not rename {item['original']}: {e}")
            
    print(f"\nSuccessfully renamed {renamed_count} files.")

if __name__ == '__main__':
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    rename_files(target_dir)
