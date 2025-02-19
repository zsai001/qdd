import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import os
from urllib.parse import quote
import click

@dataclass
class WeiboTrending:
    id: str
    title: str
    url: str
    mobile_url: str
    icon_url: Optional[str] = None
    hot: int = 0

async def fetch_weibo_trending() -> List[WeiboTrending]:
    """获取微博热搜榜"""
    url = "https://weibo.com/ajax/side/hotSearch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        data = response.json()
        
        trending_list = []
        for item in data['data']['realtime']:
            # 过滤广告
            if item.get('is_ad'):
                continue
                
            keyword = item.get('word_scheme', f"#{item['word']}#")
            # 获取热度值，如果没有则使用排名作为热度
            hot_value = item.get('raw_hot', item.get('num', 0))
            
            trending = WeiboTrending(
                id=item['word'],
                title=item['word'],
                url=f"https://s.weibo.com/weibo?q={quote(keyword)}",
                mobile_url=f"https://m.weibo.cn/search?containerid=231522type%3D1%26q%3D{quote(keyword)}&_T_WM=16922097837&v_p=42",
                icon_url=item.get('icon'),
                hot=hot_value
            )
            trending_list.append(trending)
            
        return trending_list

def view_weibo_trending():
    """在控制台显示微博热搜"""
    import asyncio
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    try:
        trending_list = asyncio.run(fetch_weibo_trending())
        
        while True:
            table = Table(title="微博热搜")
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
        console.print(f"[red]获取微博热搜失败: {str(e)}[/red]")
        return None

if __name__ == "__main__":
    view_weibo_trending() 