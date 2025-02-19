import httpx
from typing import List, Dict
from dataclasses import dataclass
import json
import os
import click

@dataclass
class ZhihuTrending:
    id: str
    title: str
    url: str
    hot: int
    excerpt: str

async def fetch_zhihu_trending() -> List[ZhihuTrending]:
    """获取知乎热榜"""
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        data = response.json()
        
        trending_list = []
        for item in data['data']:
            trending = ZhihuTrending(
                id=str(item['target']['id']),
                title=item['target']['title'],
                url=f"https://www.zhihu.com/question/{item['target']['id']}",
                hot=item['detail_text'].replace(' 万热度', '000') if '万' in item['detail_text'] else item['detail_text'],
                excerpt=item['target']['excerpt'] if 'excerpt' in item['target'] else ''
            )
            trending_list.append(trending)
            
        return trending_list

def view_zhihu_trending():
    """在控制台显示知乎热榜"""
    import asyncio
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    try:
        trending_list = asyncio.run(fetch_zhihu_trending())
        
        while True:
            table = Table(title="知乎热榜")
            table.add_column("序号", justify="right", style="cyan")
            table.add_column("标题", style="magenta")
            table.add_column("热度", style="green")
            
            for idx, item in enumerate(trending_list, 1):
                table.add_row(str(idx), item.title, str(item.hot))
            
            console.print(table)
            console.print("\n[yellow]输入序号选择热点，输入0返回上级菜单[/yellow]")
            
            choice = click.prompt("请选择", type=int, default=0)
            
            if choice == 0:
                return None
            elif 1 <= choice <= len(trending_list):
                selected = trending_list[choice-1]
                return {
                    'title': selected.title,
                    'hot': str(selected.hot),
                    'description': selected.excerpt if hasattr(selected, 'excerpt') else '',
                    'url': selected.url
                }
            else:
                console.print("[red]无效的序号，请重新选择[/red]")
        
    except Exception as e:
        console.print(f"[red]获取知乎热榜失败: {str(e)}[/red]")
        return None

if __name__ == "__main__":
    view_zhihu_trending() 