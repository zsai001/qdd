import json
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import click
import hashlib
from openai import OpenAI

console = Console()

def load_config():
    """加载配置文件"""
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

def initialize_openai_client(config):
    """初始化OpenAI客户端"""
    return OpenAI(
        api_key=config['openai']['api_key'],
        base_url=config['openai']['api_base']
    )

def cache_article_content(url, content):
    """缓存文章内容"""
    try:
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)
        
        # 使用URL的MD5作为缓存文件名
        cache_id = hashlib.md5(url.encode()).hexdigest()
        cache_file = cache_dir / f"{cache_id}.json"
        
        cache_data = {
            "url": url,
            "content": content,
            "cached_at": datetime.now().isoformat()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
        return cache_id
    except Exception as e:
        console.print(f"[red]缓存文章内容失败: {str(e)}[/red]")
        return None

def get_cached_content(url):
    """获取缓存的文章内容"""
    try:
        cache_dir = Path("cache")
        if not cache_dir.exists():
            return None
            
        cache_id = hashlib.md5(url.encode()).hexdigest()
        cache_file = cache_dir / f"{cache_id}.json"
        
        if not cache_file.exists():
            return None
            
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            return cache_data.get("content")
    except Exception as e:
        console.print(f"[red]读取缓存内容失败: {str(e)}[/red]")
        return None

def extract_article_content(url):
    """从URL中提取文章内容"""
    # 首先尝试从缓存获取
    cached_content = get_cached_content(url)
    if cached_content:
        console.print("[green]从缓存中获取文章内容[/green]")
        return cached_content
        
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 保存原始HTML
        html_content = str(soup)
        
        # 缓存内容
        cache_article_content(url, html_content)
        
        return html_content
    except Exception as e:
        console.print(f"[red]提取文章内容失败: {str(e)}[/red]")
        return None

def analyze_style_with_openai(content):
    """使用OpenAI分析文章样式"""
    try:
        config = load_config()
        client = initialize_openai_client(config)
        
        # 使用BeautifulSoup解析HTML内容以提取样式信息
        soup = BeautifulSoup(content, 'html.parser')
        
        # 提取所有样式标签和内联样式
        styles = []
        for style in soup.find_all('style'):
            styles.append(style.string)
        
        # 提取带有style属性的元素
        styled_elements = []
        for element in soup.find_all(attrs={'style': True}):
            styled_elements.append({
                'tag': element.name,
                'style': element['style']
            })
            
        # 构建分析上下文
        analysis_context = {
            'styles': styles,
            'styled_elements': styled_elements,
            'html_structure': str(soup)[:3000]  # 限制长度
        }

        prompt = """作为一个网页样式分析专家，请分析给定文章的HTML和CSS样式特征，并返回以下JSON格式数据：
        {
            "css_suggestions": {
                "font_family": ["建议的字体系列，如 Arial, sans-serif"],
                "heading_styles": {
                    "font_size": "24px",
                    "font_weight": "bold",
                    "color": "#333333",
                    "margin": "20px 0"
                },
                "body_styles": {
                    "font_size": "16px",
                    "line_height": "1.6",
                    "color": "#444444"
                },
                "paragraph_spacing": "1.5em",
                "color_scheme": {
                    "primary": "#333333",
                    "secondary": "#666666",
                    "accent": "#007bff"
                }
            },
            "style_analysis": {
                "layout": "文章布局特点",
                "typography": "排版特点",
                "color_usage": "配色特点",
                "spacing": "间距使用特点"
            }
        }
        
        请确保所有颜色值使用十六进制格式（如 #333333），所有尺寸使用具体的像素值或em值。"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的网页样式分析专家。请只返回JSON格式数据，确保包含所有必要的CSS属性值。"},
                {"role": "user", "content": f"{prompt}\n\n要分析的样式信息：\n{json.dumps(analysis_context, ensure_ascii=False)}"}
            ],
            max_tokens=1500,
            temperature=0.7,
        )
        
        # 清理返回的内容
        response_content = response.choices[0].message.content.strip()
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0]
        elif "```" in response_content:
            response_content = response_content.split("```")[1].split("```")[0]
            
        try:
            style_analysis = json.loads(response_content)
            # 确保返回的数据包含必要的字段
            if 'css_suggestions' not in style_analysis:
                raise ValueError("Missing css_suggestions in response")
            return style_analysis
        except json.JSONDecodeError as je:
            console.print(f"[red]JSON解析失败: {str(je)}[/red]")
            console.print(f"[yellow]原始返回内容:[/yellow]\n{response_content}")
            return None
            
    except Exception as e:
        console.print(f"[red]分析文章样式失败: {str(e)}[/red]")
        return None

def save_style(style_data):
    """保存样式到文件"""
    try:
        styles_dir = Path("styles")
        styles_dir.mkdir(exist_ok=True)
        
        # 生成唯一的样式ID
        style_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
        
        style_info = {
            "id": style_id,
            "created_at": datetime.now().isoformat(),
            "source_url": style_data["source_url"],
            "analysis": style_data["analysis"]
        }
        
        # 保存样式文件
        style_file = styles_dir / f"{style_id}.json"
        with open(style_file, 'w', encoding='utf-8') as f:
            json.dump(style_info, f, ensure_ascii=False, indent=2)
            
        # 生成并保存预览图
        preview_path = generate_style_preview(style_info)
        if preview_path:
            style_info['preview_image'] = str(preview_path)
            # 更新样式文件以包含预览图路径
            with open(style_file, 'w', encoding='utf-8') as f:
                json.dump(style_info, f, ensure_ascii=False, indent=2)
            
        return style_id
    except Exception as e:
        console.print(f"[red]保存样式失败: {str(e)}[/red]")
        return None

def load_styles():
    """加载所有样式"""
    styles_dir = Path("styles")
    styles = []
    
    if not styles_dir.exists():
        return styles
        
    for style_file in styles_dir.glob("*.json"):
        try:
            with open(style_file, 'r', encoding='utf-8') as f:
                style = json.load(f)
                styles.append(style)
        except Exception as e:
            console.print(f"[red]加载样式文件 {style_file} 失败: {str(e)}[/red]")
            
    return styles

def view_styles():
    """查看样式列表"""
    styles = load_styles()
    
    if not styles:
        console.print("[yellow]还没有保存的样式。[/yellow]")
        return
        
    table = Table(title="样式列表")
    table.add_column("ID", style="cyan")
    table.add_column("创建时间", style="magenta")
    table.add_column("来源URL", style="blue")
    table.add_column("预览图", style="green")
    
    for style in styles:
        created_at = datetime.fromisoformat(style["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        preview_path = style.get("preview_image", "无预览图")
        table.add_row(
            style["id"],
            created_at,
            style["source_url"],
            preview_path
        )
    
    console.print(table)

def add_style():
    """添加新样式"""
    url = click.prompt("请输入文章URL", type=str)
    
    with console.status("[bold green]正在处理...[/bold green]"):
        # 1. 提取文章内容
        content = extract_article_content(url)
        if not content:
            return
            
        # 2. 使用OpenAI分析样式
        style_analysis = analyze_style_with_openai(content)
        if not style_analysis:
            return
            
        # 3. 保存样式
        style_data = {
            "source_url": url,
            "analysis": style_analysis
        }
        
        style_id = save_style(style_data)
        if style_id:
            console.print(f"[green]样式添加成功！样式ID: {style_id}[/green]")
            # 显示分析结果
            console.print(Panel(
                json.dumps(style_analysis, indent=2, ensure_ascii=False),
                title="样式分析结果",
                expand=False
            ))

def edit_style():
    """编辑样式"""
    styles = load_styles()
    if not styles:
        console.print("[yellow]没有可编辑的样式。[/yellow]")
        return
        
    view_styles()
    style_id = click.prompt("请输入要编辑的样式ID", type=str)
    
    # 查找对应的样式
    style = next((s for s in styles if s["id"] == style_id), None)
    if not style:
        console.print("[red]未找到指定的样式。[/red]")
        return
        
    # 显示当前样式信息并允许编辑
    console.print(Panel(
        json.dumps(style["analysis"], indent=2, ensure_ascii=False),
        title="当前样式信息"
    ))
    
    if click.confirm("是否重新分析样式？"):
        content = extract_article_content(style["source_url"])
        if content:
            style_analysis = analyze_style_with_openai(content)
            if style_analysis:
                style["analysis"] = style_analysis
                save_style(style)
                console.print("[green]样式更新成功！[/green]")
                # 显示更新后的分析结果
                console.print(Panel(
                    json.dumps(style_analysis, indent=2, ensure_ascii=False),
                    title="更新后的样式分析结果",
                    expand=False
                ))

def delete_style():
    """删除样式"""
    styles = load_styles()
    if not styles:
        console.print("[yellow]没有可删除的样式。[/yellow]")
        return
        
    view_styles()
    style_id = click.prompt("请输入要删除的样式ID", type=str)
    
    style_file = Path("styles") / f"{style_id}.json"
    if style_file.exists():
        style_file.unlink()
        console.print(f"[green]样式 {style_id} 已删除。[/green]")
    else:
        console.print("[red]未找到指定的样式。[/red]")

def manage_style_versions():
    """管理样式版本"""
    console.print("[yellow]样式版本管理功能开发中...[/yellow]")

def generate_style_preview(style_data):
    """生成样式预览图"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建预览图
        width, height = 400, 300
        preview = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(preview)
        
        # 获取样式信息
        css = style_data['analysis'].get('css_suggestions', {})
        if not css:
            raise ValueError("No CSS suggestions found in style data")
            
        colors = css.get('color_scheme', {
            'primary': '#333333',
            'secondary': '#666666',
            'accent': '#007bff'
        })
        
        # 绘制颜色方案预览
        color_height = 50
        color_positions = [
            ('primary', 0),
            ('secondary', 1),
            ('accent', 2)
        ]
        
        for name, pos in color_positions:
            color = colors.get(name, '#cccccc')  # 使用默认颜色如果未指定
            draw.rectangle(
                [(0, pos * color_height), (width, (pos + 1) * color_height)],
                fill=color
            )
            
        # 添加示例文本
        try:
            # 尝试使用系统默认字体
            font = ImageFont.load_default()
            font_size = 16
            
            # 绘制标题示例
            heading_color = css.get('heading_styles', {}).get('color', '#333333')
            draw.text(
                (20, 160),
                "示例标题",
                font=font,
                fill=heading_color
            )
            
            # 绘制正文示例
            body_color = css.get('body_styles', {}).get('color', '#444444')
            draw.text(
                (20, 200),
                "这是一段示例正文，展示文章的排版效果。",
                font=font,
                fill=body_color
            )
        except Exception as font_error:
            console.print(f"[yellow]字体渲染警告: {str(font_error)}[/yellow]")
        
        # 保存预览图
        preview_path = Path("styles") / f"{style_data['id']}_preview.png"
        preview.save(preview_path)
        return preview_path
    except Exception as e:
        console.print(f"[red]生成样式预览图失败: {str(e)}[/red]")
        console.print(f"[yellow]错误详情: {type(e).__name__}: {str(e)}[/yellow]")
        return None

def clear_article_cache(url=None):
    """清除文章缓存"""
    try:
        cache_dir = Path("cache")
        if not cache_dir.exists():
            return
            
        if url:
            # 清除指定URL的缓存
            cache_id = hashlib.md5(url.encode()).hexdigest()
            cache_file = cache_dir / f"{cache_id}.json"
            if cache_file.exists():
                cache_file.unlink()
                console.print(f"[green]已清除URL {url} 的缓存[/green]")
        else:
            # 清除所有缓存
            for cache_file in cache_dir.glob("*.json"):
                cache_file.unlink()
            console.print("[green]已清除所有缓存[/green]")
    except Exception as e:
        console.print(f"[red]清除缓存失败: {str(e)}[/red]") 