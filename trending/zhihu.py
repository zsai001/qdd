import httpx
from typing import List, Dict
from dataclasses import dataclass
import json
import os

@dataclass
class ZhihuTrending:
    id: str
    title: str
    url: str
    hot: int

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
                hot=item['detail_text'].replace(' 万热度', '000') if '万' in item['detail_text'] else item['detail_text']
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
        
        table = Table(title="知乎热榜")
        table.add_column("序号", justify="right", style="cyan")
        table.add_column("标题", style="magenta")
        table.add_column("热度", style="green")
        
        for idx, item in enumerate(trending_list, 1):
            table.add_row(str(idx), item.title, str(item.hot))
        
        console.print(table)
        
        # 保存结果到文件
        save_path = "trending/cache/zhihu.json"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump([vars(item) for item in trending_list], f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        console.print(f"[red]获取知乎热榜失败: {str(e)}[/red]")

if __name__ == "__main__":
    view_zhihu_trending() 