import openai
import os
import re
import yaml
from datetime import datetime
from openai import OpenAI
from get_code import code_to_png
from trending import view_weibo_trending, view_zhihu_trending, view_toutiao_trending

def load_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

def initialize_openai_client(config):
    return OpenAI(
        api_key=config['openai']['api_key'],
        base_url=config['openai']['api_base']
    )

def generate_article_with_alt_text(client, title):
    prompt = f"""作为一位资深科技专家，请以人类专家的口吻写一篇关于"{title}"的微信自媒体文章。文章应该：
    1. 从浅入深地讲解主题
    2. 包含专业知识的详细解释
    3. 内容涵盖细致，全面，深入，且循序渐进
    4. 提供实例代码及其解释
    5. 避免AI式的表达，使用更自然的人类语言
    6. 使用Markdown格式
    7. 不需要大家好，这种欢迎语
    8. 不需要今天的分享就到这里，这种没有营养的结束语
    9. 不要出现告诫这种高高在上的语气
    10. 请使用最新的技术和视角来阐述
    11. 对于每个代码块，请在其后提供一个简短但描述性强的alt文本，格式为 <!-- alt: 你的alt文本 -->
    12. 代码块需要良好的格式化，最大宽度不要超过80个字符
    请确保文章结构清晰。包含引言、主体内容（可能包含多个小节）和总结。"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a professional technology writer specializing in creating in-depth articles for WeChat public accounts."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000,
        n=1,
        stop=None,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()

def generate_alt_text_with_gpt(client, code, language):
    prompt = f"""请为以下{language}代码生成一个简洁但描述性强的alt文本，适合用于图片的alt属性。alt文本应该概括代码的主要功能或目的，长度在100-150字符之间：

    ```{language}
    {code}
    ```
    """

    response = client.chat.completions.create(
        model="claude-3-5-sonnet-20240620",
        messages=[
            {"role": "system", "content": "You are an AI assistant specialized in creating concise and descriptive alt texts for code snippets."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()

def process_code_blocks(client, content, article_dir):
    def replace_code_block(match):
        language = match.group(1) or "text"
        code = match.group(2)
        alt_text_match = re.search(r'<!-- alt: (.*?) -->', match.group(0))
        
        if alt_text_match:
            alt_text = alt_text_match.group(1)
        else:
            alt_text = generate_alt_text_with_gpt(client, code, language)
        
        image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{language}.png"
        image_dir = os.path.join(article_dir, 'code_images')
        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, image_filename)
        
        success = code_to_png(code=code, language=language, save_path=image_path)
        
        if success:
            # 使用相对路径
            relative_image_path = os.path.join('code_images', image_filename)
            return f"\n![{alt_text}]({relative_image_path})\n"
        else:
            return f"\n```{language}\n{code}\n```\n<!-- alt: {alt_text} -->\n"

    pattern = r'```(\w+)?\n([\s\S]+?)\n```\s*(<!-- alt: .*? -->)?'
    return re.sub(pattern, replace_code_block, content)

def save_article(client, title, content):
    articles_dir = 'articles'
    os.makedirs(articles_dir, exist_ok=True)
    article_filename = f"{datetime.now().strftime('%Y%m%d')}_{title.replace(' ', '_')}.md"
    article_path = os.path.join(articles_dir, article_filename)
    
    # 创建文章特定的目录
    article_dir = os.path.splitext(article_path)[0]  # 移除.md扩展名
    os.makedirs(article_dir, exist_ok=True)
    
    # 处理代码块，生成图片
    processed_content = process_code_blocks(client, content, article_dir)
    
    # 保存文章到特定目录
    final_article_path = os.path.join(article_dir, f"{os.path.basename(article_dir)}.md")
    with open(final_article_path, 'w', encoding='utf-8') as file:
        file.write(processed_content)

    return final_article_path

def article():
    config = load_config()
    client = initialize_openai_client(config)

    title = input("请输入文章标题: ")
    print("正在生成文章，请稍候...")

    try:
        article_content = generate_article_with_alt_text(client, title)
        saved_file = save_article(client, title, article_content)
        print(f"文章已生成并保存至: {saved_file}")
    except Exception as e:
        print(f"生成文章时发生错误: {str(e)}")

def view_trending():
    """查看所有平台热点"""
    view_weibo_trending()
    view_zhihu_trending()
    view_toutiao_trending()

if __name__ == "__main__":
    article()