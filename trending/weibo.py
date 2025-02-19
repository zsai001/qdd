import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import os
from urllib.parse import quote

@dataclass
class WeiboTrending:
    id: str
    title: str
    url: str
    mobile_url: str
    icon_url: Optional[str] = None

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
            trending = WeiboTrending(
                id=item['word'],
                title=item['word'],
                url=f"https://s.weibo.com/weibo?q={quote(keyword)}",
                mobile_url=f"https://m.weibo.cn/search?containerid=231522type%3D1%26q%3D{quote(keyword)}&_T_WM=16922097837&v_p=42",
                icon_url=item.get('icon')
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
        
        table = Table(title="微博热搜榜")
        table.add_column("序号", justify="right", style="cyan")
        table.add_column("标题", style="magenta")
        table.add_column("热度", style="green")
        
        for idx, item in enumerate(trending_list, 1):
            icon = "🔥" if item.icon_url else ""
            table.add_row(str(idx), f"{icon} {item.title}", "")
        
        console.print(table)
        
        # 保存结果到文件
        save_path = "trending/cache/weibo.json"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump([vars(item) for item in trending_list], f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        console.print(f"[red]获取微博热搜失败: {str(e)}[/red]")

if __name__ == "__main__":
    view_weibo_trending() 