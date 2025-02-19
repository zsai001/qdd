from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
import hashlib
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from template import view_templates
from style import view_styles, apply_style
import re

console = Console()

def create_from_title():
    """从标题创作文章"""
    # 获取标题
    title = click.prompt("请输入要创作的标题", type=str)
    
    # 选择创作模版
    template = select_template()
    if not template:
        console.print("[red]未选择模版，创作取消[/red]")
        return
        
    # 输入创作要求
    requirements = click.prompt("请输入创作要求(可选)", type=str, default="")
    
    # 使用GPT生成文章内容
    from gpt import load_config, initialize_openai_client, generate_article_with_alt_text
    
    try:
        # 初始化OpenAI客户端
        config = load_config()
        client = initialize_openai_client(config)
        
        # 生成文章内容
        console.print("[green]正在生成文章，请稍候...[/green]")
        content = generate_article_with_alt_text(client, title)
        
        # 应用模板和要求
        if requirements:
            content = apply_requirements(client, content, requirements)
        
        # 选择样式
        style = select_style()
        if not style:
            console.print("[red]未选择样式，创作取消[/red]")
            return
            
        # 应用样式生成最终内容
        console.print("[green]正在应用样式...[/green]")
        final_content, html_content = apply_style(client, content, style)
        
        # 保存文章
        saved_path = save_article(client, title, final_content, html_content)
        console.print(f"[green]文章已生成并保存至: {saved_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]生成文章失败: {str(e)}[/red]")

def apply_requirements(client, content: str, requirements: str) -> str:
    """应用用户的创作要求"""
    prompt = f"""请根据以下要求修改文章内容：

要求：{requirements}

原文：
{content}

请保持Markdown格式，返回修改后的完整文章。"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a professional article editor."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000,
        temperature=0.7,
    )
    
    return response.choices[0].message.content.strip()

def create_from_url():
    """从URL一键改写文章"""
    # 获取URL
    url = click.prompt("请输入要改写的文章URL", type=str)
    
    # 下载并解析内容
    try:
        content = download_article(url)
    except Exception as e:
        console.print(f"[red]下载文章失败: {str(e)}[/red]")
        return
    
    # 选择创作模版
    template = select_template()
    if not template:
        console.print("[red]未选择模版，改写取消[/red]")
        return
        
    # 输入改写要求
    requirements = click.prompt("请输入改写要求(可选)", type=str, default="")
    
    # 使用GPT改写文章
    from gpt import rewrite_article
    new_content = rewrite_article(content, template, requirements)
    if not new_content:
        console.print("[red]文章改写失败[/red]")
        return
        
    # 选择样式
    style = select_style()
    if not style:
        console.print("[red]未选择样式，改写取消[/red]")
        return
        
    # 应用样式生成最终内容
    final_content = apply_style(new_content, style)
    
    # 保存文章
    title = extract_title(content) or "改写文章"
    save_article(title, final_content)
    console.print("[green]文章改写完成并保存[/green]")

def select_template():
    """选择创作模版"""
    console.print("\n[yellow]请选择创作模版:[/yellow]")
    templates = view_templates()
    if not templates:
        return None
        
    while True:
        choice = click.prompt("请输入模版编号(0取消)", type=int, default=0)
        if choice == 0:
            return None
        if 1 <= choice <= len(templates):
            return templates[choice-1]
        console.print("[red]无效的编号，请重新选择[/red]")

def select_style():
    """选择文章样式"""
    console.print("\n[yellow]请选择文章样式:[/yellow]")
    styles = view_styles()
    if not styles:
        return None
        
    while True:
        choice = click.prompt("请输入样式编号(0取消)", type=int, default=0)
        if choice == 0:
            return None
        if 1 <= choice <= len(styles):
            return styles[choice-1]
        console.print("[red]无效的编号，请重新选择[/red]")

def download_article(url: str) -> str:
    """从URL下载文章内容"""
    # 计算缓存文件名
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = Path(f"cache/{cache_key}.json")
    
    # 检查缓存
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            if datetime.now().timestamp() - data['cached_at'] < 86400:  # 24小时缓存
                return data['content']
    
    # 下载内容
    response = requests.get(url)
    response.raise_for_status()
    
    # 解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    content = extract_article_content(soup)
    
    # 保存缓存
    cache_file.parent.mkdir(exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump({
            'url': url,
            'content': content,
            'cached_at': datetime.now().timestamp()
        }, f)
    
    return content

def extract_article_content(soup: BeautifulSoup) -> str:
    """从HTML中提取文章内容"""
    # 这里需要根据具体网站结构调整提取逻辑
    article = soup.find('article') or soup.find('div', class_='article')
    if article:
        return article.get_text()
    return soup.get_text()

def extract_title(content: str) -> str:
    """从文章内容中提取标题"""
    # 简单实现，可以根据需要改进
    lines = content.strip().split('\n')
    return lines[0] if lines else ""

def apply_style(client, content: str, style: dict) -> tuple[str, str]:
    """使用 GPT 应用样式并生成 HTML"""
    # 构建提示词
    prompt = f"""请将以下 Markdown 内容转换为 HTML，并应用给定的样式规则。

样式规则：
{json.dumps(style.get('analysis', {}), indent=2, ensure_ascii=False)}

Markdown 内容：
{content}

请返回两个部分：
1. 应用了样式的 Markdown 内容（保持 Markdown 格式）
2. 完整的 HTML 代码（包含所有必要的 CSS）

用 [MARKDOWN] 和 [HTML] 标记来分隔这两部分内容。
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的网页样式专家，精通 Markdown 和 HTML/CSS。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7,
        )

        result = response.choices[0].message.content.strip()
        
        # 分离 Markdown 和 HTML 内容
        md_match = re.search(r'\[MARKDOWN\](.*?)\[HTML\]', result, re.DOTALL)
        html_match = re.search(r'\[HTML\](.*?)$', result, re.DOTALL)
        
        if not md_match or not html_match:
            raise ValueError("GPT 返回的内容格式不正确")
            
        markdown_content = md_match.group(1).strip()
        html_content = html_match.group(1).strip()
        
        return markdown_content, html_content
        
    except Exception as e:
        console.print(f"[red]应用样式失败: {str(e)}[/red]")
        return content, ""  # 返回原始内容和空 HTML

def save_article(client, title: str, content: str, html_content: str = None):
    """保存文章的 Markdown 和 HTML 版本"""
    # 创建文章目录
    articles_dir = Path("articles")
    article_dir = articles_dir / f"{datetime.now().strftime('%Y%m%d')}_{title.replace(' ', '_')}"
    article_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存 Markdown 文件
    md_file = article_dir / f"{article_dir.name}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    # 如果有 HTML 内容，保存 HTML 文件
    html_file = None
    if html_content:
        html_file = article_dir / f"{article_dir.name}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
    
    # 提示是否发布
    if click.confirm("是否立即发布文章？"):
        try:
            from pub import publish_article
            from wx import WeChatAPI
            
            # 获取微信配置
            config = load_config()
            wechat_api = WeChatAPI(config['wechat']['appid'], config['wechat']['appsecret'])
            
            # 发布文章
            if html_file:
                console.print("[green]正在发布文章...[/green]")
                url = publish_article(wechat_api, str(html_file))
                if url:
                    console.print(f"[green]文章发布成功！URL: {url}[/green]")
                    
                    # 更新元数据
                    meta = create_default_meta()
                    meta.update({
                        'title': title,
                        'publishable': True,
                        'published': True,
                        'publish_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'publish_url': url
                    })
                    
                    # 保存元数据
                    meta_file = article_dir / "meta.json"
                    with open(meta_file, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                else:
                    console.print("[red]文章发布失败[/red]")
            else:
                console.print("[red]没有找到HTML文件，无法发布[/red]")
                
        except Exception as e:
            console.print(f"[red]发布文章时出错: {str(e)}[/red]")
    
    return str(article_dir)

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