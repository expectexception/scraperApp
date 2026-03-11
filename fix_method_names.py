import glob
for f in glob.glob('scraper_manager/scrapers/*.py'):
    with open(f, 'r') as file:
        data = file.read()
    if 'should_scrape_job' in data:
        data = data.replace('should_scrape_job', 'should_process_job')
        with open(f, 'w') as file:
            file.write(data)
        print(f'Fixed {f}')
