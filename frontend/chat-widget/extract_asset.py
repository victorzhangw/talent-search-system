
import re
import base64
import os

target_file = 'src/components/MessageList.vue'
output_dir = 'src/assets/images'
output_file = os.path.join(output_dir, 'traitty-avatar.svg')

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Match the base64 string: src="data:image/svg+xml;base64,..."
pattern = r'src="data:image/svg\+xml;base64,([^"]+)"'
match = re.search(pattern, content)

if match:
    base64_str = match.group(1)
    decoded_bytes = base64.b64decode(base64_str)
    
    with open(output_file, 'wb') as f:
        f.write(decoded_bytes)
    print(f"Successfully extracted asset to {output_file}")
else:
    print("No base64 SVG found in MessageList.vue")
