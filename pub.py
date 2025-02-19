import time
import codecs
import re
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import yaml
import os
import json
from PIL import Image
from wx import WeChatAPI, PublishStatus, WeChatAPIError
from md import WxRenderer, opts

def read_text_file(file_path):
    with codecs.open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def decode_unicode_escape(text):
    return codecs.decode(text, 'unicode_escape')

def load_article_meta(file_path):
    with codecs.open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        meta_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if meta_match:
            meta_yaml = meta_match.group(1)
            meta = yaml.safe_load(meta_yaml)
            content = content[meta_match.end():]
            return meta, content
        return {}, content

def process_local_images(content, base_path, api):
    def replace_image(match):
        alt_text = match.group(1) or ''  # 获取 alt 文本，如果没有则为空字符串
        img_path = match.group(2)
        full_path = os.path.join(base_path, img_path)
        if os.path.exists(full_path):
            # Upload the image and get a URL
            image_url = api.upload_image_for_article(full_path)
            return f'![{alt_text}]({image_url})'
        return match.group(0)  # 如果图片不存在，保持原样
    
    # 使用新的正则表达式来匹配包含 alt 文本的图片标记
    return re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image, content)

def extract_title_from_markdown(content):
    # 查找第一个标题（# 开头的行）
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    ret = "Untitled"
    if title_match:
        ret = title_match.group(1).strip()
    else:
        # 如果没有找到 #，查找第一个非空行
        first_line_match = re.search(r'^(.+)$', content, re.MULTILINE)
        if first_line_match:
            ret = first_line_match.group(1).strip()
    
    ret = ret.replace("#", '')
    return ret

def crop_cover_image(cover_path):
    width = 1120
    height = 383
    crop_big = (0, 0, 900, 383)
    crop_small = (920, 91, 1120, 291)  # Corrected to (920, 91, 920+200, 91+200)

    # Calculate pic_crop_235_1 (for the big crop)
    x1_235 = crop_big[0] / width
    y1_235 = crop_big[1] / height
    x2_235 = crop_big[2] / width
    y2_235 = crop_big[3] / height
    pic_crop_235_1 = f"{x1_235:.6f}_{y1_235:.6f}_{x2_235:.6f}_{y2_235:.6f}"

    # Calculate pic_crop_1_1 (for the small crop)
    x1_1 = crop_small[0] / width
    y1_1 = crop_small[1] / height
    x2_1 = crop_small[2] / width
    y2_1 = crop_small[3] / height
    pic_crop_1_1 = f"{x1_1:.6f}_{y1_1:.6f}_{x2_1:.6f}_{y2_1:.6f}"

    return pic_crop_235_1, pic_crop_1_1
    
def publish_article(api: WeChatAPI, article_path: str):
    try:
        base_path = os.path.dirname(article_path)
        meta, content = load_article_meta(article_path)
        
        # Process local images
        content = process_local_images(content, base_path, api)
        title = extract_title_from_markdown(content)
        with open('test.md', 'w') as f:
            f.write(content)
        # Render Markdown to HTML
        renderer = WxRenderer(opts)
        html_content = renderer.render(content)
        
        with open('test.html', 'w') as f:
            f.write(html_content)
    
        # Upload cover image
        cover_path = os.path.join(base_path, meta['cover_image']['url'])
        print("Uploading cover image...")
        cover_result = api.upload_permanent_material("image", cover_path)
        thumb_media_id = cover_result["media_id"]
        print(f"Cover image uploaded. Media ID: {thumb_media_id}")
        
        # Crop cover image
        pic_crop_235_1, pic_crop_1_1 = crop_cover_image(cover_path)
        print(pic_crop_235_1, pic_crop_1_1)
        # Prepare the publishing data
        articles = [{
            "title": title,
            "author": meta.get('author', ''),
            "digest": meta.get('digest', content[:50]),  # Use the first 54 characters as digest if not provided
            "content": html_content,
            "show_cover_pic": 1,
            "content_source_url": meta.get('publish_url', ''),
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
            "pic_crop_235_1": pic_crop_235_1,
            "pic_crop_1_1": pic_crop_1_1
        }]
        
        # Create draft
        print("Creating draft...")
        draft_media_id = api.add_draft(articles)
        print(f"Draft created. Media ID: {draft_media_id}")

        # Publish draft
        print("Publishing draft...")
        publish_result = api.publish_draft(draft_media_id)
        publish_id = publish_result['publish_id']
        print(f"Draft submitted for publishing. Publish ID: {publish_id}")

        # Check publishing status
        max_retries = 10
        retry_interval = 5  # seconds
        for i in range(max_retries):
            print(f"Checking publish status... (Attempt {i+1}/{max_retries})")
            status_result = api.get_publish_status(publish_id)
            
            if status_result['status'] == PublishStatus.SUCCESS:
                print("Article published successfully!")
                print(f"Article ID: {status_result['article_id']}")
                for item in status_result['article_detail'].get('item', []):
                    print(f"Article URL: {item['article_url']}")
                return
            elif status_result['status'] in [PublishStatus.ORIGINAL_FAIL, PublishStatus.PLATFORM_AUDIT_FAIL, PublishStatus.NORMAL_FAIL]:
                print(f"Publishing failed. Status: {status_result['status_description']}")
                if 'fail_idx' in status_result:
                    print(f"Failed article indexes: {status_result['fail_idx']}")
                return
            elif status_result['status'] == PublishStatus.PUBLISHING:
                print("Still publishing, waiting...")
                time.sleep(retry_interval)
            else:
                print(f"Unexpected status: {status_result['status_description']}")
                return

        print("Max retries reached. Please check the publish status manually.")

    except WeChatAPIError as e:
        print(f"WeChat API Error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")    