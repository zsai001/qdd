import httpx
from typing import List, Dict
from dataclasses import dataclass
import json
import os
import click

@dataclass
class ToutiaoTrending:
    id: str
    title: str
    url: str
    hot: int

async def fetch_toutiao_trending() -> List[ToutiaoTrending]:
    """获取今日头条热榜"""
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        data = response.json()
        
        trending_list = []
        for item in data['data']:
            trending = ToutiaoTrending(
                id=str(item['ClusterId']),
                title=item['Title'],
                url=f"https://www.toutiao.com/trending/{item['ClusterId']}",
                hot=item['HotValue']
            )
            trending_list.append(trending)
            
        return trending_list

def view_toutiao_trending():
    """在控制台显示今日头条热榜"""
    import asyncio
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    try:
        trending_list = asyncio.run(fetch_toutiao_trending())
        
        while True:
            table = Table(title="今日头条热榜")
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
                    'description': '',
                    'url': selected.url
                }
            else:
                console.print("[red]无效的序号，请重新选择[/red]")
        
    except Exception as e:
        console.print(f"[red]获取今日头条热榜失败: {str(e)}[/red]")
        return None

if __name__ == "__main__":
    view_toutiao_trending() 