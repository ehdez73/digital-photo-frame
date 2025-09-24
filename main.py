import json
import os
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from PIL import Image
from io import BytesIO
import threading
import time
import hashlib
from PyQt5 import QtWidgets, QtGui, QtCore
from google.oauth2 import service_account

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config(path=CONFIG_PATH):
    with open(path, 'r') as f:
        config = json.load(f)
    return config

def ensure_download_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

def is_image_file(filename):
    return filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))

def get_drive_service(service_account_json):
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    credentials = service_account.Credentials.from_service_account_file(
        service_account_json, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
    return service

def download_images_from_drive(service_account_json, folder_id, download_folder):
    print("Connecting to Google Drive with service account...")
    service = get_drive_service(service_account_json)
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])
        print(f"Found {len(files)} files in Drive folder.")
        for file in files:
            if not is_image_file(file['name']):
                continue
            local_path = os.path.join(download_folder, file['name'])
            if os.path.exists(local_path):
                print(f"Already downloaded: {file['name']}")
                continue
            print(f"Downloading: {file['name']}...")
            try:
                request = service.files().get_media(fileId=file['id'])
                from googleapiclient.http import MediaIoBaseDownload
                with open(local_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                print(f"Downloaded: {file['name']}")
            except Exception as e:
                print(f"Error downloading {file['name']}: {e}")
    except HttpError as error:
        print(f"An error occurred: {error}")
        print("Continuing with local images only.")

def get_local_images(download_folder):
    files = os.listdir(download_folder)
    return [os.path.join(download_folder, f) for f in files if is_image_file(f)]

def resize_image_to_fit(img, max_width, max_height):
    img_width, img_height = img.size
    ratio = min(max_width / img_width, max_height / img_height)
    new_size = (int(img_width * ratio), int(img_height * ratio))
    return img.resize(new_size, Image.LANCZOS)

def hash_file_list(file_list):
    m = hashlib.sha256()
    for f in sorted(file_list):
        m.update(f.encode())
    return m.hexdigest()

class ImageCarousel(QtWidgets.QWidget):
    def __init__(self, image_paths, transition_time, frame_color, frame_width, image_margin):
        super().__init__()
        self.setWindowTitle("Digital Photo Frame")
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")
        self.image_paths = image_paths
        self.transition_time = transition_time
        self.frame_color = frame_color
        self.frame_width = frame_width
        self.image_margin = image_margin
        self.current = 0
        self.images = []
        self.paused = False
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setStyleSheet("background-color: black;")
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.load_images()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.show_next_image)
        self.timer.start(self.transition_time * 1000)
        self.show_next_image()
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def load_images(self):
        screen_rect = QtWidgets.QApplication.primaryScreen().geometry()
        screen_w, screen_h = screen_rect.width(), screen_rect.height()
        margin = self.image_margin
        max_w = screen_w - 2 * margin
        max_h = screen_h - 2 * margin
        self.images = []
        for path in self.image_paths:
            try:
                img = Image.open(path)
                img = resize_image_to_fit(img, max_w, max_h)
                # Create a black background and paste the image centered with margin
                bg = Image.new("RGB", (screen_w, screen_h), "black")
                x = (screen_w - img.width) // 2
                y = (screen_h - img.height) // 2
                bg.paste(img, (x, y))
                data = bg.convert("RGBA").tobytes("raw", "RGBA")
                qimg = QtGui.QImage(data, bg.width, bg.height, QtGui.QImage.Format_RGBA8888)
                pixmap = QtGui.QPixmap.fromImage(qimg)
                self.images.append(pixmap)
            except Exception as e:
                print(f"Error loading image {path}: {e}")

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Right:
            print("[User Action] Next photo")
            self.show_next_image(reset_timer=True)
        elif event.key() == QtCore.Qt.Key_Left:
            print("[User Action] Previous photo")
            self.show_prev_image(reset_timer=True)
        elif event.key() == QtCore.Qt.Key_Escape:
            print("[User Action] Exit application")
            QtWidgets.QApplication.quit()
        elif event.key() == QtCore.Qt.Key_Space:
            self.toggle_pause()
        else:
            super().keyPressEvent(event)

    def toggle_pause(self):
        if self.paused:
            print("[User Action] Unpause slideshow")
            self.timer.start(self.transition_time * 1000)
            self.paused = False
        else:
            print("[User Action] Pause slideshow")
            self.timer.stop()
            self.paused = True

    def show_next_image(self, reset_timer=False):
        if not self.images:
            self.label.setText("No images found.")
            return
        self.label.setPixmap(self.images[self.current])
        self.current = (self.current + 1) % len(self.images)
        if reset_timer and not self.paused:
            self.timer.start(self.transition_time * 1000)

    def show_prev_image(self, reset_timer=False):
        if not self.images:
            self.label.setText("No images found.")
            return
        self.current = (self.current - 2) % len(self.images)  # -1 to go back, -1 because show_next_image will +1
        self.show_next_image(reset_timer=reset_timer)

    def refresh_images(self, new_image_paths):
        self.image_paths = new_image_paths
        self.load_images()
        self.current = 0
        self.show_next_image()

def monitor_drive_folder(config, carousel):
    last_hash = None
    while True:
        try:
            download_images_from_drive(
                config['service_account_json'],
                config['drive_folder_id'],
                config['download_folder']
            )
            image_paths = get_local_images(config['download_folder'])
            current_hash = hash_file_list(image_paths)
            if current_hash != last_hash:
                print("Detected change in images. Refreshing carousel.")
                carousel.refresh_images(image_paths)
                last_hash = current_hash
        except Exception as e:
            print(f"Error monitoring Drive folder: {e}")
            
        sleep_time = config.get('monitor_interval', 600)     
        print(f"sleeping for : {sleep_time} seconds")
        time.sleep(sleep_time)

if __name__ == "__main__":
    import sys
    config = load_config()
    print("Loaded config:", config)
    ensure_download_folder(config['download_folder'])
    download_images_from_drive(
        config['service_account_json'],
        config['drive_folder_id'],
        config['download_folder']
    )
    image_paths = get_local_images(config['download_folder'])
    image_margin = config.get('image_margin', 40)  # Default margin 40px
    app = QtWidgets.QApplication(sys.argv)
    carousel = ImageCarousel(
        image_paths,
        config.get('transition_time', 3),
        config.get('frame_color', '#FFFFFF'),
        config.get('frame_width', 20),
        image_margin
    )
    monitor_thread = threading.Thread(target=monitor_drive_folder, args=(config, carousel), daemon=True)
    monitor_thread.start()
    sys.exit(app.exec_())
