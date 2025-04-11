import os
import requests
import tkinter as tk
from tkinter import filedialog, messagebox
from tqdm import tqdm
from threading import Thread

def fetch_items(collection, limit):
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f"collection:{collection}",
        "fl[]": "identifier",
        "rows": limit,
        "output": "json",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return [doc["identifier"] for doc in response.json()["response"]["docs"]]

def fetch_files(identifier):
    metadata_url = f"https://archive.org/metadata/{identifier}"
    response = requests.get(metadata_url)
    response.raise_for_status()
    files = response.json().get("files", [])
    return [
        f for f in files
        if f.get("format") == "JPEG" or f.get("name", "").lower().endswith(".jpg")
        if not any(suffix in f["name"].lower() for suffix in ["_thumb", "___ia_thumb"])
    ]

def download_image(file, identifier, folder):
    os.makedirs(folder, exist_ok=True)
    name = file["name"]
    url = f"https://archive.org/download/{identifier}/{name}"
    path = os.path.join(folder, f"{identifier}_{name}")
    if not os.path.exists(path):
        try:
            data = requests.get(url).content
            with open(path, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"Error downloading {url}: {e}")

def start_download(collection_url, limit, folder):
    collection = collection_url.strip().split("/")[-1]
    try:
        identifiers = fetch_items(collection, limit)
        for identifier in tqdm(identifiers, desc="Processing items"):
            image_files = fetch_files(identifier)
            for file in image_files:
                download_image(file, identifier, folder)
        messagebox.showinfo("Done", f"Downloaded images to {folder}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def run_downloader():
    url = url_entry.get()
    try:
        limit = int(limit_entry.get())
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid number.")
        return
    folder = output_folder.get()
    if not url or not folder:
        messagebox.showerror("Missing Input", "Please fill in all fields.")
        return
    Thread(target=start_download, args=(url, limit, folder), daemon=True).start()

def choose_folder():
    path = filedialog.askdirectory()
    if path:
        output_folder.set(path)

# GUI
root = tk.Tk()
root.title("Archive.org Image Downloader")

tk.Label(root, text="Archive.org Collection URL:").pack()
url_entry = tk.Entry(root, width=60)
url_entry.insert(0, "https://archive.org/details/flickr-ows")
url_entry.pack()

tk.Label(root, text="Number of Items to Download:").pack()
limit_entry = tk.Entry(root)
limit_entry.insert(0, "10")
limit_entry.pack()

tk.Label(root, text="Output Folder:").pack()
output_folder = tk.StringVar()
tk.Entry(root, textvariable=output_folder, width=50).pack(side="left")
tk.Button(root, text="Browse", command=choose_folder).pack(side="left")

tk.Button(root, text="Start Download", command=run_downloader).pack(pady=10)

root.mainloop()
