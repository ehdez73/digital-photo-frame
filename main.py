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
import pygame
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

class PygameCarousel:
    def __init__(self, image_paths, transition_time, image_margin):
        pygame.init()
        pygame.display.set_caption("Digital Photo Frame")
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.bg_color = (0, 0, 0)
        self.image_paths = image_paths
        self.transition_time = transition_time
        self.image_margin = image_margin
        self.current_index = 0
        self.paused = False
        self.last_switch_time = time.time()
        self.surfaces = []
        self.screen_rect = self.screen.get_rect()
        self.load_images()

    def _show_centered_message(self, text):
        self.screen.fill(self.bg_color)
        font = pygame.font.SysFont(None, 64)
        surface = font.render(text, True, (220, 220, 220))
        rect = surface.get_rect(center=self.screen_rect.center)
        self.screen.blit(surface, rect)
        pygame.display.flip()

    def load_images(self):
        self.surfaces = []
        width, height = self.screen_rect.size
        max_w = max(1, width - 2 * self.image_margin)
        max_h = max(1, height - 2 * self.image_margin)
        for path in self.image_paths:
            try:
                img = Image.open(path).convert("RGB")
                img = resize_image_to_fit(img, max_w, max_h)
                mode = img.mode
                size = img.size
                data = img.tobytes()
                surf = pygame.image.fromstring(data, size, mode)
                self.surfaces.append(surf)
            except Exception as e:
                print(f"Error loading image {path}: {e}")
        if not self.surfaces:
            # Create a placeholder surface with text
            font = pygame.font.SysFont(None, 48)
            text = font.render("No images found.", True, (200, 200, 200))
            placeholder = pygame.Surface((max_w, max_h))
            placeholder.fill((0, 0, 0))
            rect = text.get_rect(center=(placeholder.get_width() // 2, placeholder.get_height() // 2))
            placeholder.blit(text, rect)
            self.surfaces.append(placeholder)

    def refresh_images(self, new_image_paths):
        self.image_paths = new_image_paths
        # Keep current index if possible
        old_index = self.current_index
        self.load_images()
        if self.surfaces:
            self.current_index = min(old_index, len(self.surfaces) - 1)
        else:
            self.current_index = 0
        self.last_switch_time = time.time()

    def show_current(self):
        self.screen.fill(self.bg_color)
        if not self.surfaces:
            # Render fallback text
            font = pygame.font.SysFont(None, 48)
            text = font.render("No images found.", True, (200, 200, 200))
            rect = text.get_rect(center=self.screen_rect.center)
            self.screen.blit(text, rect)
            pygame.display.flip()
            return
        surf = self.surfaces[self.current_index % len(self.surfaces)]
        # Center within an inset rect to guarantee margins on all sides
        inset_rect = self.screen_rect.inflate(-2 * self.image_margin, -2 * self.image_margin)
        rect = surf.get_rect(center=inset_rect.center)
        self.screen.blit(surf, rect)
        pygame.display.flip()

    def next_image(self, reset_timer=False):
        if not self.surfaces:
            return
        print("[User Action] Next photo")
        self.current_index = (self.current_index + 1) % len(self.surfaces)
        if reset_timer:
            self.last_switch_time = time.time()

    def prev_image(self, reset_timer=False):
        if not self.surfaces:
            return
        print("[User Action] Previous photo")
        self.current_index = (self.current_index - 1) % len(self.surfaces)
        if reset_timer:
            self.last_switch_time = time.time()

    def toggle_pause(self):
        if self.paused:
            print("[User Action] Unpause slideshow")
            self.paused = False
            self.last_switch_time = time.time()
        else:
            print("[User Action] Pause slideshow")
            self.paused = True

    def rotate_current_image(self, degrees=-90):
        if not self.image_paths or not self.surfaces:
            return
        try:
            path = self.image_paths[self.current_index]
            direction = "right" if degrees == -90 else ("left" if degrees == 90 else f"{degrees}°")
            print(f"[User Action] Rotate image {abs(degrees)}° {direction} and overwrite: {os.path.basename(path)}")
            # Show overlay message before rotating
            self._show_centered_message("Rotating, please wait")
            pygame.event.pump()
            with Image.open(path) as img:
                rotated = img.rotate(degrees, expand=True)
                save_kwargs = {}
                if path.lower().endswith((".jpg", ".jpeg")):
                    save_kwargs["quality"] = 95
                rotated.save(path, **save_kwargs)
            # Reload images and keep index on the same file
            current_path = path
            self.load_images()
            if self.image_paths:
                try:
                    self.current_index = self.image_paths.index(current_path)
                except ValueError:
                    self.current_index = 0
            # Immediately show the rotated image and reset timer
            self.last_switch_time = time.time()
            self.show_current()
        except Exception as e:
            print(f"Error rotating image: {e}")

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        print("[User Action] Exit application")
                        running = False
                    elif event.key == pygame.K_RIGHT:
                        self.next_image(reset_timer=True)
                    elif event.key == pygame.K_LEFT:
                        self.prev_image(reset_timer=True)
                    elif event.key == pygame.K_SPACE:
                        self.toggle_pause()
                    elif event.key == pygame.K_DOWN:
                        # Clockwise 90°
                        self.rotate_current_image(degrees=-90)
                    elif event.key == pygame.K_UP:
                        # Anticlockwise 90°
                        self.rotate_current_image(degrees=90)
            if self.surfaces and (not self.paused) and ((time.time() - self.last_switch_time) >= self.transition_time):
                self.next_image(reset_timer=True)
            self.show_current()
            self.clock.tick(60)
        pygame.quit()

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
    config = load_config()
    print("Loaded config:", config)
    ensure_download_folder(config['download_folder'])
    download_images_from_drive(
        config['service_account_json'],
        config['drive_folder_id'],
        config['download_folder']
    )
    image_paths = get_local_images(config['download_folder'])
    carousel = PygameCarousel(
        image_paths,
        config.get('transition_time', 5),
        config.get('image_margin', 40)
    )
    monitor_thread = threading.Thread(target=monitor_drive_folder, args=(config, carousel), daemon=True)
    monitor_thread.start()
    carousel.run()
