from curl_cffi import requests
html = requests.get('https://hifly.aero/careers/', impersonate='chrome').text
open('hifly_debug.html', 'w').write(html)
