import os
import yaml
import random
from datetime import datetime
import json
from typing import List, Dict, Tuple
from cover import get_landscape_photos, get_unused_photos, update_photo_usage, read_log
from pub import publish_article as wechat_publish_article
from wx import WeChatAPI
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

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

def show_trending_menu():
    while True:
        console.print(Panel.fit(
            "热点查看\n\n"
            "1. 今日头条热点\n"
            "2. 微博热搜\n"
            "3. 知乎热榜\n"
            "0. 返回上级菜单",
            title="热点菜单"
        ))
        
        choice = click.prompt("请选择", type=str, default="0")
        
        if choice == "1":
            from trending import view_toutiao_trending
            selected_topic = view_toutiao_trending()
            if selected_topic:
                show_topic_detail(selected_topic)
        elif choice == "2":
            from trending import view_weibo_trending
            selected_topic = view_weibo_trending()
            if selected_topic:
                show_topic_detail(selected_topic)
        elif choice == "3":
            from trending import view_zhihu_trending
            selected_topic = view_zhihu_trending()
            if selected_topic:
                show_topic_detail(selected_topic)
        elif choice == "0":
            break
        else:
            console.print("[red]无效的选项，请重新选择[/red]")

def show_trending_data_menu(source: str, trending_data: list):
    while True:
        table = Table(title=f"{source}列表")
        table.add_column("序号", justify="right", style="cyan")
        table.add_column("标题", style="magenta")
        table.add_column("热度", justify="right", style="green")

        for idx, item in enumerate(trending_data, 1):
            table.add_row(
                str(idx),
                item.get('title', '未知'),
                str(item.get('hot', ''))
            )

        console.print(table)
        console.print("\n[yellow]输入序号查看详情，输入0返回上级菜单[/yellow]")
        
        choice = click.prompt("请选择", type=int, default=0)
        
        if choice == 0:
            break
        elif 1 <= choice <= len(trending_data):
            selected_topic = trending_data[choice-1]
            show_topic_detail(selected_topic)
        else:
            console.print("[red]无效的序号，请重新选择[/red]")

def show_topic_detail(topic: dict):
    while True:
        console.print(Panel.fit(
            f"[bold magenta]标题：[/bold magenta]{topic.get('title')}\n\n"
            f"[bold green]热度：[/bold green]{topic.get('hot', '')}\n\n"
            f"[bold yellow]描述：[/bold yellow]{topic.get('description', '暂无描述')}\n\n"
            f"[bold blue]链接：[/bold blue]{topic.get('url', '暂无链接')}\n\n"
            "\n1. 改写文章\n"
            "0. 返回上级菜单",
            title="热点详情"
        ))
        
        choice = click.prompt("请选择", type=str, default="0")
        
        if choice == "1":
            show_rewrite_menu(topic)
            break
        elif choice == "0":
            break
        else:
            console.print("[red]无效的选项，请重新选择[/red]")

def show_rewrite_menu(topic: dict):
    while True:
        console.print(Panel.fit(
            f"已选择话题：{topic.get('title')}\n\n"
            "1. 改写为观点文章\n"
            "2. 改写为科普文章\n"
            "3. 改写为故事文章\n"
            "4. 改写为评论文章\n"
            "0. 返回上级菜单",
            title="改写菜单"
        ))
        
        choice = click.prompt("请选择改写方式", type=str, default="0")
        
        if choice == "1":
            from gpt import rewrite_as_opinion
            rewrite_as_opinion(topic)
        elif choice == "2":
            from gpt import rewrite_as_educational
            rewrite_as_educational(topic)
        elif choice == "3":
            from gpt import rewrite_as_story
            rewrite_as_story(topic)
        elif choice == "4":
            from gpt import rewrite_as_commentary
            rewrite_as_commentary(topic)
        elif choice == "0":
            break
        else:
            console.print("[red]无效的选项，请重新选择[/red]")

def show_article_menu():
    while True:
        console.print(Panel.fit(
            "文章创作\n\n"
            "1. 从热点创作\n"
            "2. 从自定义主题创作\n"
            "3. 查看草稿箱\n"
            "0. 返回上级菜单",
            title="创作菜单"
        ))
        
        choice = click.prompt("请选择", type=str, default="0")
        
        if choice == "1":
            from gpt import create_from_trending
            create_from_trending()
        elif choice == "2":
            from gpt import create_from_topic
            create_from_topic()
        elif choice == "3":
            from gpt import view_drafts
            view_drafts()
        elif choice == "0":
            break
        else:
            console.print("[red]无效的选项，请重新选择[/red]")

def show_publish_menu():
    while True:
        console.print(Panel.fit(
            "文章发布\n\n"
            "1. 查看待发布文章\n"
            "2. 发布单篇文章\n"
            "3. 自动发布\n"
            "0. 返回上级菜单",
            title="发布菜单"
        ))
        
        choice = click.prompt("请选择", type=str, default="0")
        
        if choice == "1":
            view_publishable()
        elif choice == "2":
            publish_single()
        elif choice == "3":
            pub()
        elif choice == "0":
            break
        else:
            console.print("[red]无效的选项，请重新选择[/red]")

def view_publishable():
    _, publishable_files = process_directory("./articles")
    if not publishable_files:
        console.print("[yellow]没有找到可以发布的文件。[/yellow]")
        return
    
    table = Table(title="待发布文章列表")
    table.add_column("序号", justify="right", style="cyan")
    table.add_column("文件名", style="magenta")
    
    for idx, file_path in enumerate(publishable_files, 1):
        table.add_row(str(idx), os.path.basename(file_path))
    
    console.print(table)

def publish_single():
    _, publishable_files = process_directory("./articles")
    if not publishable_files:
        console.print("[yellow]没有找到可以发布的文件。[/yellow]")
        return
    
    view_publishable()
    idx = click.prompt("请选择要发布的文章序号（0取消）", type=int, default=0)
    
    if idx == 0:
        return
    
    if 1 <= idx <= len(publishable_files):
        file_to_publish = publishable_files[idx-1]
        meta, content = process_md_file(file_to_publish)
        updated_meta = publish_article(file_to_publish, meta, content)
        save_md_file(file_to_publish, updated_meta, content)
        console.print(f"[green]文章已发布: {file_to_publish}[/green]")
    else:
        console.print("[red]无效的序号[/red]")

def main_menu():
    while True:
        console.print(Panel.fit(
            "欢迎使用文章创作发布系统\n\n"
            "1. 查看热点\n"
            "2. 创作文章\n"
            "3. 发布文章\n"
            "0. 退出",
            title="主菜单"
        ))
        
        choice = click.prompt("请选择", type=str, default="0")
        
        if choice == "1":
            show_trending_menu()
        elif choice == "2":
            show_article_menu()
        elif choice == "3":
            show_publish_menu()
        elif choice == "0":
            console.print("[green]感谢使用，再见！[/green]")
            break
        else:
            console.print("[red]无效的选项，请重新选择[/red]")

@click.group()
def cli():
    """文章创作发布系统命令行工具"""
    pass

@cli.command()
def interactive():
    """启动交互式菜单"""
    main_menu()

@cli.command()
def publish():
    """直接发布文章"""
    pub()

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        main_menu()