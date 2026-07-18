import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen('http://127.0.0.1:8000/products/import/template/')
    if response.getcode() == 200:
        print("Template downloaded successfully")
        with open('import_template.xlsx', 'wb') as f:
            f.write(response.read())
    else:
        print(f"Failed to download template: {response.getcode()}")
except urllib.error.URLError as e:
    print(f"Error: {e}")
