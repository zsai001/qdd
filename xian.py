import os
import yaml
import random
from datetime import datetime
import json
from typing import List, Dict, Tuple
from cover import get_landscape_photos, get_unused_photos, update_photo_usage, read_log
from pub import publish_article as wechat_publish_article
from wx import WeChatAPI

def load_config():
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    return config['wechat']['appid'], config['wechat']['appsecret']

def load_yaml_meta(content):
    try:
        if content.startswith('---\n'):
            end = content.find('\n---\n', 4)
            if end != -1:
                yaml_content = content[4:end]
                return yaml.safe_load(yaml_content), content[end+5:]
    except yaml.YAMLError:
        pass
    return None, content

def create_default_meta():
    return {
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'author': 'zsai',
        'tags': [],
        'publishable': False,
        'published': False,
        'publish_date': None,
        'publish_url': None,
        'cover_image': None
    }

def select_cover_image() -> Tuple[str, str, str]:
    unused_photos = get_unused_photos()
    if not unused_photos:
        print("没有可用的封面图片，正在获取新图片...")
        get_landscape_photos()
        unused_photos = get_unused_photos()
    
    if unused_photos:
        selected_photo_id = random.choice(unused_photos)
        log_data = read_log()
        photo_data = log_data[selected_photo_id]
        update_photo_usage(selected_photo_id, "待发布")
        cover_path = photo_data['cover_path']
        cover_path = os.path.join("../../", cover_path)
        return selected_photo_id, cover_path, ""
    else:
        print("警告：无法获取封面图片")
        return None, None, None

def process_md_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    meta, doc_content = load_yaml_meta(content)
    if meta is None:
        meta = create_default_meta()
    
    default_meta = create_default_meta()
    for key, value in default_meta.items():
        if key not in meta:
            meta[key] = value
    
    if meta['cover_image'] is None:
        photo_id, photo_url, relative_path = select_cover_image()
        if photo_id and photo_url:
            meta['cover_image'] = {
                'photo_id': photo_id,
                'url': photo_url
            }
    return meta, doc_content

def save_md_file(file_path, meta, content):
    yaml_meta = yaml.dump(meta, default_flow_style=False)
    content = content.strip()
    full_content = f"---\n{yaml_meta}---\n{content}"
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(full_content)

def publish_article(file_path, meta, content):
    print(f"Publishing article: {file_path}")
    
    appid, secret = load_config()
    wechat_api = WeChatAPI(appid, secret)
    
    image_path = meta['cover_image']['url']
    article_title = os.path.basename(file_path).replace('.md', '')
    article_author = meta['author']
    
    url = wechat_publish_article(wechat_api, file_path)
    if url:
        meta['published'] = True
        meta['publish_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        meta['publish_url'] = url
    
        if meta['cover_image'] and meta['cover_image']['photo_id']:
            update_photo_usage(meta['cover_image']['photo_id'], meta['publish_url'])
    
    return meta

def process_directory(directory):
    md_files = []
    publishable_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                meta, content = process_md_file(file_path)
                save_md_file(file_path, meta, content)
                md_files.append(file_path)
                if meta['publishable'] and not meta['published']:
                    publishable_files.append(file_path)
    
    return md_files, publishable_files

def pub():
    directory = "./articles"
    all_files, publishable_files = process_directory(directory)
    
    print(f"处理了 {len(all_files)} 个 Markdown 文件。")
    print(f"其中有 {len(publishable_files)} 个文件可以发布。")
    
    if publishable_files:
        file_to_publish = random.choice(publishable_files)
        meta, content = process_md_file(file_to_publish)
        
        updated_meta = publish_article(file_to_publish, meta, content)
        save_md_file(file_to_publish, updated_meta, content)
        print(f"文章已发布: {file_to_publish}")
    else:
        print("没有找到可以发布的文件。")



import sys
from gpt import article

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] == "pub":
            pub()
        else:
            article()
    else:
        pub()