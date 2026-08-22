import requests
import os
import zipfile

def file_downloader(url, local_filename):
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()  # controleer of de download succesvol was
            with open(local_filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        print(f"Bestand gedownload en opgeslagen als {local_filename}")
    except requests.exceptions.RequestException as e:
        print(f"Er is een fout opgetreden: {e}")

def unzip_file(zip_file_path, extract_to_dir):
    # zorg dat de doelmap bestaat
    os.makedirs(extract_to_dir, exist_ok=True)

    # open het ZIP-bestand
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        # pak alles uit naar de opgegeven map
        zip_ref.extractall(extract_to_dir)
        print(f"Alle bestanden uitgepakt naar {extract_to_dir}")