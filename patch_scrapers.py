import os
import glob

def patch_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    modified = False
    
    # Check if file has apply_title_filter
    has_final_filter = any("apply_title_filter(jobs)" in line for line in lines)
    
    # Check if file has should_process_job
    has_pre_filter = any("self.should_process_job(" in line for line in lines)

    new_lines = []
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Patch final filter before save_results
        if not has_final_filter and "await self.save_results(jobs)" in line:
            # Check indentation
            indent = line[:len(line) - len(line.lstrip())]
            filter_code = [
                f"{indent}if self.use_filter and self.filter_manager and jobs:\n",
                f"{indent}    logger.info(f\"[{{self.site_key}}] Applying final filter check...\")\n",
                f"{indent}    jobs, _, filter_stats = self.apply_title_filter(jobs)\n",
                f"{indent}    self.filter_manager.print_filter_stats(filter_stats)\n\n"
            ]
            new_lines.insert(-1, "".join(filter_code))
            modified = True
            
        # Patch pre filter before fetching details
        if not has_pre_filter and "Fetching details for:" in line and "logger.info" in line:
            indent = line[:len(line) - len(line.lstrip())]
            filter_code = [
                f"{indent}if not self.should_process_job(title):\n",
                f"{indent}    continue\n\n",
                f"{indent}if await self.is_url_already_scraped(url):\n",
                f"{indent}    continue\n\n"
            ]
            new_lines.insert(-1, "".join(filter_code))
            modified = True

    if modified:
        with open(filepath, 'w') as f:
            f.writelines(new_lines)
        print(f"Patched {os.path.basename(filepath)}")

def main():
    files = glob.glob('scraper_manager/scrapers/*_scraper.py')
    for f in files:
        if "base_scraper.py" in f:
            continue
        patch_file(f)

if __name__ == '__main__':
    main()
