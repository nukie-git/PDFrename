import os
from dry_run_rename import get_rename_mapping
from logger import log

def rename_files(directory='.'):
    directory = os.path.expandvars(os.path.expanduser(directory))
    log(f"Starting execute rename on directory: {directory}", "INFO")

    cache_path = os.path.join(directory, '.rename_cache.json')
    mapping = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            log(f"Loaded pre-computed rename mapping from cache: {cache_path}", "INFO")
        except Exception as e:
            log(f"Could not read cache ({e}), falling back to rescanning directory.", "WARNING")

    if mapping is None:
        mapping = get_rename_mapping(directory)

    renamed_count = 0
    
    print("--- EXECUTING RENAME ---")
    try:
        for item in mapping:
            if 'error' in item:
                msg = f"[SKIP] {item['original']}: {item['error']}"
                print(msg)
                log(msg, "ERROR")
                continue
                
            old_path = item['full_original']
            new_path = item['full_new']
            
            if item['original'] == item['new']:
                msg = f"[NO CHANGE] {item['original']}"
                print(msg)
                log(msg, "INFO")
                continue
                
            try:
                # On Windows, renaming a file to a case-only change requires a 2-step rename
                temp_path = old_path + ".tmp_rename"
                os.rename(old_path, temp_path)
                os.rename(temp_path, new_path)
                msg = f"[RENAMED] {item['original']} -> {item['new']}"
                print(msg)
                log(msg, "SUCCESS")
                renamed_count += 1
            except Exception as e:
                msg = f"[ERROR] Could not rename {item['original']}: {e}"
                print(msg)
                log(msg, "ERROR")
                
        summary_msg = f"Successfully renamed {renamed_count} files."
        print(f"\n{summary_msg}")
        log(summary_msg, "INFO")
    finally:
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                log(f"Cleaned up cache file: {cache_path}", "INFO")
            except Exception as e:
                log(f"Failed to remove cache file ({cache_path}): {e}", "WARNING")

if __name__ == '__main__':
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    rename_files(target_dir)
