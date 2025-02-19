import traceback

import requests
import os
from PIL import Image
import io
import json
import yaml
from datetime import datetime

# 读取配置文件
def load_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

config = load_config()
UNSPLASH_KEY = config['UNSPLASH_KEY']

# 设置保存图片的目录
COVER_DIR = "wechat_covers"
LOG_FILE = os.path.join(f"{COVER_DIR}/photo_log.json")
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB in bytes
MAX_RESOLUTION = (3840, 2160)  # 4K resolution

# 上传 URL
UPLOAD_URL = "https://tg.sciproxy.com/"

def create_directories():
    if not os.path.exists(COVER_DIR):
        os.makedirs(COVER_DIR)

def optimize_image(image, max_size):
    quality = 95
    while True:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=quality)
        if img_byte_arr.tell() <= max_size or quality <= 20:
            break
        quality -= 5
    return Image.open(img_byte_arr)

def merge_covers(large_cover_path, small_cover_path, output_path, gap=20):
    large_cover = Image.open(large_cover_path)
    small_cover = Image.open(small_cover_path)

    large_width, large_height = large_cover.size
    small_width, small_height = small_cover.size

    new_width = large_width + small_width + gap
    new_height = max(large_height, small_height)

    new_image = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))

    large_position = (0, (new_height - large_height) // 2)
    small_position = (large_width + gap, (new_height - small_height) // 2)

    new_image.paste(large_cover, large_position)
    new_image.paste(small_cover, small_position)

    new_image.save(output_path, 'PNG')

    return {
        'large_cover': {
            'position': large_position,
            'size': large_cover.size
        },
        'small_cover': {
            'position': small_position,
            'size': small_cover.size
        }
    }
    
def crop_and_resize(img, target_width, target_height):
    target_ratio = target_width / target_height
    img_ratio = img.width / img.height
    
    if img_ratio > target_ratio:
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    elif img_ratio < target_ratio:
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))
    
    return img.resize((target_width, target_height), Image.LANCZOS)

def create_wechat_covers(img, photo_id):
    cover_large = crop_and_resize(img, 900, 383)
    large_cover_path = os.path.join(COVER_DIR, f"{photo_id}_900x383.jpg")
    cover_large.save(large_cover_path, 'JPEG', quality=95)

    cover_small = crop_and_resize(img, 200, 200)
    small_cover_path = os.path.join(COVER_DIR, f"{photo_id}_200x200.jpg")
    cover_small.save(small_cover_path, 'JPEG', quality=95)

    return large_cover_path, small_cover_path

def upload_image(image):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    files = {'file': ('image.jpg', img_byte_arr, 'image/jpeg')}
    response = requests.post(UPLOAD_URL, files=files)
    if response.status_code == 200:
        upload_info = json.loads(response.text)
        return upload_info[0]['src']
    else:
        print(f"Failed to upload image")
        return None

def process_and_upload_image(url, photo_id):
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(io.BytesIO(response.content))
        
        if image.size[0] > MAX_RESOLUTION[0] or image.size[1] > MAX_RESOLUTION[1]:
            image.thumbnail(MAX_RESOLUTION)
        
        if len(response.content) > MAX_FILE_SIZE:
            image = optimize_image(image, MAX_FILE_SIZE)
        
        large_cover_path, small_cover_path = create_wechat_covers(image, photo_id)
        # try:
        #     upload_url = upload_image(image)
        # except Exception as e:
        #     print(f"Failed to upload image: {e}")
        #     return False, None, None, None
        #
        # if upload_url:
        #     print(f"Uploaded image successfully")
        #     return True, upload_url, large_cover_path, small_cover_path
        # else:
        #     return False, None, None, None
        return True, large_cover_path, small_cover_path
    else:
        print(f"Failed to download: {url}")
        return False, None, None, None

def log_photo(photo_id, upload_url, large_cover_path, small_cover_path, crop_info, output_path):
    log_entry = {
        "photo_id": photo_id,
        "upload_url": upload_url,
        "large_cover_path": large_cover_path,
        "small_cover_path": small_cover_path,
        "crop_info": crop_info,
        "cover_path": output_path,
        "is_used": False,
        "article_url": None,
        "timestamp": datetime.now().isoformat()
    }
    
    log_data = read_log()
    log_data[photo_id] = log_entry
    
    with open(LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2)

def read_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return {}

def update_photo_usage(photo_id, article_url):
    log_data = read_log()
    if photo_id in log_data:
        log_data[photo_id]["is_used"] = True
        log_data[photo_id]["article_url"] = article_url
        log_data[photo_id]["usage_timestamp"] = datetime.now().isoformat()
        with open(LOG_FILE, 'w') as f:
            json.dump(log_data, f, indent=2)
        return True
    return False

def get_unused_photos():
    log_data = read_log()
    return [photo_id for photo_id, data in log_data.items() if not data["is_used"]]

def get_landscape_photos(count=3):
    url = "https://api.unsplash.com/photos/random"
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}
    params = {
        "query": "landscape",
        "count": count,
        "orientation": "landscape"
    }

    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        photos = response.json()
        for photo in photos:
            image_url = photo['urls']['full']
            photo_id = photo['id']
            try:
                success, large_cover_path, small_cover_path = process_and_upload_image(image_url, photo_id)
                output_path = os.path.join(COVER_DIR, f"{photo_id}_covers.png")
                if success:
                    crop_info = merge_covers(large_cover_path, small_cover_path, output_path)
                    log_photo(photo_id, image_url, large_cover_path, small_cover_path, crop_info, output_path)
                    os.remove(large_cover_path)
                    os.remove(small_cover_path)
            except Exception as e:
                # 打印错误堆栈
                stacktrace = traceback.format_exc(e)
                print(stacktrace)
                print(f"Error processing photo {photo_id}: {e}")
    else:
        print(f"API request failed with status code: {response.status_code}")

if __name__ == "__main__":
    create_directories()
    get_landscape_photos()

    # 示例：如何更新照片使用状态
    # update_photo_usage("some_photo_id", "https://example.com/article")

    # 示例：如何获取未使用的照片
    # unused_photos = get_unused_photos()
    # print(f"未使用的照片 ID: {unused_photos}")