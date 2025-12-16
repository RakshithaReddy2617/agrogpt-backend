import os
import requests

def download_file(url: str, dest_path: str):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    if os.path.exists(dest_path):
        print(f"✅ File already exists: {dest_path}")
        return

    print(f"⬇️ Downloading: {dest_path}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"✅ Download completed: {dest_path}")
