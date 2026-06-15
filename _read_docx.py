import zipfile
import xml.etree.ElementTree as ET
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r'E:\Sales Training System\.reasonix\attachments\clipboard-20260611-175046.279109-000002.docx'
with zipfile.ZipFile(path) as z:
    xml = z.read('word/document.xml')

tree = ET.fromstring(xml)
ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

for p in tree.iter(f'{{{ns}}}p'):
    texts = [t.text for t in p.iter(f'{{{ns}}}t') if t.text]
    if texts:
        print(''.join(texts))
