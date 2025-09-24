# Digital Photo Frame (Carousel)

This application displays a fullscreen digital photo frame (carousel) that shows images from a Google Drive folder. It automatically downloads new images, displays them with animated transitions and a digital frame, and monitors the Google Drive folder for updates.

## Features
- Reads configuration from `config.json` (Google Drive service account JSON, folder ID, local download folder, transition time, monitoring interval, image margin)
- Downloads images from a Google Drive folder to a local folder (only if not already present)
- Displays images in a fullscreen PyQt5 carousel with animated transitions
- Images are always fully visible, centered, and maintain their aspect ratio
- Configurable margin between the image and the screen edges
- Black background for a modern look
- Monitors the Google Drive folder at a configurable interval and updates the carousel automatically
- **Keyboard navigation:**
  - Left/Right arrows: Previous/Next photo
  - Space: Pause/Unpause slideshow
  - Escape: Exit application
- **User actions are logged to the console** (next, previous, pause, unpause, exit)

## Configuration
Create a `config.json` file in the project root with the following structure:

```json
{
  "service_account_json": "service_account.json",
  "drive_folder_id": "YOUR_FOLDER_ID",
  "download_folder": "downloads",
  "transition_time": 5,
  "monitor_interval": 600,
  "image_margin": 40
}
```
- `service_account_json`: Path to your Google service account JSON file (see below)
- `drive_folder_id`: The ID of the Google Drive folder containing images
- `download_folder`: Local folder to store downloaded images
- `transition_time`: Time (in seconds) for each image to be displayed
- `monitor_interval`: Time (in seconds) between checks for new images (default: 600 = 10 minutes)
- `image_margin`: Margin (in pixels) between the image and the screen edges

### How to obtain a Google service account JSON file
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the Google Drive API for your project.
4. Go to "APIs & Services > Credentials" and click "Create Credentials > Service account".
5. Follow the prompts to create a service account and download the JSON key file.
6. Share the target Google Drive folder with the service account email address.
7. Save the JSON file in your project directory and update `config.json` with its path.

## Keyboard Controls
- **Right Arrow (`→`)**: Next photo
- **Left Arrow (`←`)**: Previous photo
- **Space**: Pause/Unpause the slideshow
- **Escape**: Exit the application

All user actions are logged to the console for easy monitoring.

## Requirements
- Python 3.13+
- `PyQt5`, `requests`, `Pillow`, `google-api-python-client`, `google-auth`

## Usage
This project uses `uv` for dependency management and execution. Install and learn more about `uv` here: [uv documentation](https://docs.astral.sh/uv/).

1. Install dependencies: `uv sync`
2. Create and fill `config.json` as described above.
3. Run the application: `uv run main.py`
