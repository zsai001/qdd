import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import click
import hashlib
from openai import OpenAI
import yaml
import requests
from bs4 import BeautifulSoup

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

def save_template(template_data):
    """保存模板到文件"""
    try:
        templates_dir = Path("templates")
        templates_dir.mkdir(exist_ok=True)
        
        # 生成唯一的模板ID
        template_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
        
        # 更新：保存所有模板数据
        template_info = {
            "id": template_id,
            "created_at": datetime.now().isoformat(),
            "name": template_data["name"],
            "description": template_data["description"],
            "content": template_data.get("content", ""),
            "url": template_data.get("url", ""),
            "tags": template_data.get("tags", []),
            "prompt": template_data.get("prompt", ""),
            "structure": template_data.get("structure", ""),
            "tone": template_data.get("tone", ""),
            "techniques": template_data.get("techniques", []),
            "variables": template_data.get("variables", [])
        }
        
        # 保存模板文件
        template_file = templates_dir / f"{template_id}.json"
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_info, f, ensure_ascii=False, indent=2)
            
        return template_id
    except Exception as e:
        console.print(f"[red]保存模板失败: {str(e)}[/red]")
        return None

def load_templates():
    """加载所有模板"""
    templates_dir = Path("templates")
    templates = []
    
    if not templates_dir.exists():
        return templates
        
    for template_file in templates_dir.glob("*.json"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template = json.load(f)
                templates.append(template)
        except Exception as e:
            console.print(f"[red]加载模板文件 {template_file} 失败: {str(e)}[/red]")
            
    return templates

def view_templates():
    """查看模板列表"""
    templates = load_templates()
    
    if not templates:
        console.print("[yellow]还没有保存的模板。[/yellow]")
        return
        
    table = Table(title="模板列表")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="magenta")
    table.add_column("标签", style="blue")
    table.add_column("描述", style="green", max_width=40)
    
    for template in templates:
        table.add_row(
            template["id"],
            template["name"],
            ", ".join(template.get("tags", [])),
            template["description"]
        )
    
    console.print(table)
    
    # 添加详细查看功能
    if click.confirm("是否查看模板详情？"):
        template_id = click.prompt("请输入要查看的模板ID", type=str)
        template = next((t for t in templates if t["id"] == template_id), None)
        if template:
            console.print(Panel.fit(
                f"[bold]模板名称:[/bold] {template['name']}\n"
                f"[bold]描述:[/bold] {template['description']}\n"
                f"[bold]标签:[/bold] {', '.join(template.get('tags', []))}\n"
                f"[bold]写作语气:[/bold] {template.get('tone', '未设置')}\n"
                f"[bold]文章结构:[/bold] {template.get('structure', '未设置')}\n"
                f"[bold]写作技巧:[/bold] {', '.join(template.get('techniques', []))}\n"
                f"[bold]来源URL:[/bold] {template.get('url', '无')}\n"
                f"[bold]GPT提示词:[/bold]\n{template.get('prompt', '未设置')}",
                title=f"模板详情 (ID: {template_id})"
            ))
        else:
            console.print("[red]未找到指定的模板。[/red]")

def get_cache_path(url):
    """获取URL对应的缓存文件路径"""
    cache_dir = Path("templates/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    # 使用URL的MD5作为缓存文件名
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return cache_dir / f"{url_hash}.json"

def load_from_cache(url):
    """从缓存加载内容"""
    cache_path = get_cache_path(url)
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                # 检查缓存是否过期（这里设置7天过期）
                cache_time = datetime.fromisoformat(cache_data['cached_at'])
                if (datetime.now() - cache_time).days < 7:
                    return cache_data['content']
        except Exception as e:
            console.print(f"[yellow]读取缓存失败: {str(e)}[/yellow]")
    return None

def save_to_cache(url, content):
    """保存内容到缓存"""
    try:
        cache_path = get_cache_path(url)
        cache_data = {
            'url': url,
            'content': content,
            'cached_at': datetime.now().isoformat()
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        console.print(f"[yellow]保存缓存失败: {str(e)}[/yellow]")

def extract_content_from_url(url):
    """从URL提取文章内容，优先使用缓存"""
    # 1. 尝试从缓存加载
    cached_content = load_from_cache(url)
    if cached_content:
        console.print("[green]从缓存加载内容成功[/green]")
        return cached_content
    
    # 2. 如果没有缓存，从URL获取
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
        
        # 3. 保存到缓存
        save_to_cache(url, text)
        console.print("[green]内容已保存到缓存[/green]")
        
        return text
    except Exception as e:
        console.print(f"[red]提取文章内容失败: {str(e)}[/red]")
        return None

def analyze_template_with_gpt(content):
    """使用GPT分析文章内容生成模板"""
    try:
        config = load_config()
        client = initialize_openai_client(config)
        
        prompt = """分析以下文章内容，提取其写作模板特征。请返回JSON格式，包含以下字段：
        1. name: 模板名称（简短描述写作风格）
        2. description: 详细描述这个写作模板的特点
        3. tags: 相关标签列表
        4. prompt: 用于生成类似文章的GPT提示词
        5. structure: 文章结构分析
        6. tone: 写作语气特征
        7. techniques: 使用的写作技巧列表

        只返回JSON格式数据，不要包含其他说明文字。"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的写作模板分析专家。"},
                {"role": "user", "content": f"{prompt}\n\n文章内容：\n{content[:3000]}"}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        
        # 提取JSON内容
        response_text = response.choices[0].message.content
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
            
        return json.loads(response_text.strip())
    except Exception as e:
        console.print(f"[red]GPT分析失败: {str(e)}[/red]")
        console.print(response_text)
        return None

def add_template():
    """添加新模板"""
    url = click.prompt("请输入文章URL", type=str)
    
    with console.status("[bold green]正在分析文章...[/bold green]"):
        # 1. 提取文章内容
        content = extract_content_from_url(url)
        if not content:
            return
        
        # 2. 使用GPT分析内容
        analysis = analyze_template_with_gpt(content)
        if not analysis:
            return
        
        # 3. 显示分析结果并确认
        console.print(Panel.fit(
            f"[bold]模板名称:[/bold] {analysis['name']}\n"
            f"[bold]描述:[/bold] {analysis['description']}\n"
            f"[bold]标签:[/bold] {', '.join(analysis['tags'])}\n"
            f"[bold]写作语气:[/bold] {analysis['tone']}\n"
            f"[bold]文章结构:[/bold] {analysis['structure']}\n"
            f"[bold]写作技巧:[/bold] {', '.join(analysis['techniques'])}",
            title="模板分析结果"
        ))
        
        # if not click.confirm("是否保存该模板？"):
        #     return
        
        # 4. 保存模板
        template_data = {
            "name": analysis["name"],
            "description": analysis["description"],
            "content": content,
            "url": url,
            "tags": analysis["tags"],
            "prompt": analysis["prompt"],
            "structure": analysis["structure"],
            "tone": analysis["tone"],
            "techniques": analysis["techniques"]
        }
        
        template_id = save_template(template_data)
        if template_id:
            console.print(f"[green]模板添加成功！模板ID: {template_id}[/green]")

def edit_template():
    """编辑模板"""
    templates = load_templates()
    if not templates:
        console.print("[yellow]没有可编辑的模板。[/yellow]")
        return
        
    view_templates()
    template_id = click.prompt("请输入要编辑的模板ID", type=str)
    
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        console.print("[red]未找到指定的模板。[/red]")
        return
    
    name = click.prompt("模板名称", type=str, default=template["name"])
    description = click.prompt("模板描述", type=str, default=template["description"])
    content = click.prompt("模板内容", type=str, default=template["content"])
    
    variables = template.get("variables", [])
    if click.confirm("是否编辑变量？"):
        variables = []
        while click.confirm("是否添加变量？"):
            var_name = click.prompt("变量名", type=str)
            var_description = click.prompt("变量描述", type=str)
            variables.append({"name": var_name, "description": var_description})
    
    template_data = {
        "name": name,
        "description": description,
        "content": content,
        "variables": variables
    }
    
    save_template(template_data)
    console.print("[green]模板更新成功！[/green]")

def delete_template():
    """删除模板"""
    templates = load_templates()
    if not templates:
        console.print("[yellow]没有可删除的模板。[/yellow]")
        return
        
    view_templates()
    template_id = click.prompt("请输入要删除的模板ID", type=str)
    
    template_file = Path("templates") / f"{template_id}.json"
    if template_file.exists():
        template_file.unlink()
        console.print(f"[green]模板 {template_id} 已删除。[/green]")
    else:
        console.print("[red]未找到指定的模板。[/red]")

def manage_template_versions():
    """管理模板版本"""
    console.print("[yellow]模板版本管理功能开发中...[/yellow]") 