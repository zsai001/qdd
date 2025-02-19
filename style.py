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

def extract_article_content(url):
    """从URL中提取文章内容"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除脚本和样式元素
        for script in soup(["script", "style"]):
            script.decompose()
            
        # 获取文本内容
        text = soup.get_text(separator='\n')
        
        # 清理文本
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        console.print(f"[red]提取文章内容失败: {str(e)}[/red]")
        return None

def analyze_style_with_openai(content):
    """使用OpenAI分析文章样式"""
    try:
        config = load_config()
        client = initialize_openai_client(config)
        
        prompt = """作为一个文章风格分析专家，请分析给定文章的写作风格，包括以下方面：
        1. 语气（正式/轻松/专业等）
        2. 结构特点
        3. 常用修辞手法
        4. 段落组织方式
        5. 特色表达方式
        6. 用词特点
        
        请直接返回JSON格式数据，不要添加任何markdown标记，必须包含以下字段：
        {
            "tone": "语气特点",
            "structure": "结构特征",
            "rhetoric": ["主要修辞手法"],
            "paragraph_style": "段落组织特点",
            "expression": "表达特色",
            "vocabulary": "用词特点"
        }"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的文章风格分析专家。请只返回JSON格式数据，不要包含任何markdown标记。"},
                {"role": "user", "content": f"{prompt}\n\n要分析的文章内容：\n{content[:3000]}"}  # 限制长度
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        
        # 清理返回的内容，移除可能的markdown标记
        response_content = response.choices[0].message.content
        # 如果内容包含 ```json 和 ``` 标记，提取中间的JSON内容
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0]
        elif "```" in response_content:
            response_content = response_content.split("```")[1].split("```")[0]
            
        # 清理空白字符
        response_content = response_content.strip()
        
        try:
            style_analysis = json.loads(response_content)
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
    
    for style in styles:
        created_at = datetime.fromisoformat(style["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(
            style["id"],
            created_at,
            style["source_url"]
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