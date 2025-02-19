import re
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

class WxRenderer:
    def __init__(self, opts):
        self.opts = opts
        self.footnotes = []
        self.footnote_index = 0
        self.style_mapping = self.build_theme(opts['theme'])

    def build_theme(self, theme_tpl):
        mapping = {}
        base = {**theme_tpl['BASE'], 'font-family': self.opts['fonts'], 'font-size': self.opts['size']}
        
        for ele, style in theme_tpl['inline'].items():
            mapping[ele] = {**base, **style}
        
        base_block = {**base}
        for ele, style in theme_tpl['block'].items():
            mapping[ele] = {**base_block, **style}
        
        return mapping

    def get_styles(self, token_name, addition=''):
        styles = self.style_mapping.get(token_name, {})
        style_str = ';'.join([f"{k}:{v}" for k, v in styles.items()])
        return f'style="{style_str}{addition}"'

    def render(self, md_text):
        md = markdown.Markdown(extensions=['extra', 'codehilite'])
        html = md.convert(md_text)
        
        # Apply custom styling
        html = self.apply_custom_styling(html)
        
        return html

    def apply_custom_styling(self, html):
        # Apply heading styles
        for i in range(1, 5):
            html = re.sub(f'<h{i}>(.*?)</h{i}>', lambda m: f'<h{i} {self.get_styles(f"h{i}")}>{m.group(1)}</h{i}>', html)
        
        # Apply paragraph styles
        html = re.sub('<p>(.*?)</p>', lambda m: f'<p {self.get_styles("p")}>{m.group(1)}</p>', html)
        
        # Apply blockquote styles
        html = re.sub('<blockquote>(.*?)</blockquote>', lambda m: f'<blockquote {self.get_styles("blockquote")}>{m.group(1)}</blockquote>', html)
        
        # Apply code block styles
        html = re.sub('<pre><code.*?>(.*?)</code></pre>', self.style_code_block, html, flags=re.DOTALL)
        
        # Apply inline code styles
        html = re.sub('<code>(.*?)</code>', lambda m: f'<code {self.get_styles("codespan")}>{m.group(1)}</code>', html)
        
        # Apply list styles
        html = re.sub('<ul>(.*?)</ul>', lambda m: f'<ul {self.get_styles("ul")}>{m.group(1)}</ul>', html, flags=re.DOTALL)
        html = re.sub('<ol>(.*?)</ol>', lambda m: f'<ol {self.get_styles("ol")}>{m.group(1)}</ol>', html, flags=re.DOTALL)
        html = re.sub('<li>(.*?)</li>', lambda m: f'<li {self.get_styles("listitem")}>{m.group(1)}</li>', html)
        
        # Apply image styles
        html = re.sub('<img(.*?)>', lambda m: f'<figure {self.get_styles("figure")}><img{m.group(1)} {self.get_styles("image")}/></figure>', html)
        
        # Apply link styles
        html = re.sub('<a(.*?)>(.*?)</a>', self.style_link, html)
        
        return html

    def style_code_block(self, match):
        code = match.group(1)
        lang = re.search(r'class=".*language-(\w+)"', match.group(0))
        lang = lang.group(1) if lang else 'plaintext'
        
        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = HtmlFormatter(style=self.opts.get('code_theme', 'default'))
        highlighted_code = highlight(code, lexer, formatter)
        
        return f'<pre {self.get_styles("code_pre")}>{highlighted_code}</pre>'

    def style_link(self, match):
        attrs, text = match.groups()
        href = re.search(r'href="(.*?)"', attrs)
        href = href.group(1) if href else ''
        
        if href.startswith('https://mp.weixin.qq.com'):
            return f'<a href="{href}" {self.get_styles("wx_link")}>{text}</a>'
        return f'<span {self.get_styles("link")}>{text}</span>'

baseColor = "#3f3f3f"

theme = {
    'BASE': {
        'text-align': 'left',
        'line-height': '1.5',
    },
    'block': {
        'h1': {
            'font-size': '1.1em',
            'text-align': 'center',
            'font-weight': 'bold',
            'display': 'table',
            'margin': '1.5em auto 0.75em',
            'padding': '0 0.8em',
            'border-bottom': '2px solid rgba(0, 152, 116, 0.9)',
            'color': baseColor,
        },
        'h2': {
            'font-size': '1.1em',
            'text-align': 'center',
            'font-weight': 'bold',
            'display': 'table',
            'margin': '3em auto 1.5em',
            'padding': '0 0.2em',
            'background': 'rgba(0, 152, 116, 0.9)',
            'color': '#fff',
        },
        'h3': {
            'font-weight': 'bold',
            'font-size': '1em',
            'margin': '1.5em 6px 0.5em 0',
            'line-height': '1.2',
            'padding-left': '6px',
            'border-left': '3px solid rgba(0, 152, 116, 0.9)',
            'color': baseColor,
        },
        'h4': {
            'font-weight': 'bold',
            'font-size': '0.9em',
            'margin': '1.5em 6px 0.5em',
            'color': 'rgba(66, 185, 131, 0.9)',
        },
        'p': {
            'margin': '1em 6px',
            'letter-spacing': '0.05em',
            'color': baseColor,
            'text-align': 'justify',
        },
        'blockquote': {
            'font-style': 'normal',
            'border-left': 'none',
            'padding': '0.8em',
            'border-radius': '6px',
            'color': 'rgba(0,0,0,0.5)',
            'background': '#f7f7f7',
            'margin': '1.5em 6px',
        },
        'blockquote_p': {
            'letter-spacing': '0.05em',
            'color': 'rgb(80, 80, 80)',
            'font-size': '0.9em',
            'display': 'block',
        },
        'code_pre': {
            'font-size': '13px',
            'overflow-x': 'auto',
            'border-radius': '6px',
            'padding': '0.8em',
            'line-height': '1.4',
            'margin': '8px 6px',
        },
        'code': {
            'margin': 0,
            'white-space': 'nowrap',
            'font-family': 'Menlo, Operator Mono, Consolas, Monaco, monospace',
        },
        'image': {
            'border-radius': '4px',
            'display': 'block',
            'margin': '0.1em auto 0.4em',
            'width': '100% !important',
        },
        'ol': {
            'margin-left': '0',
            'padding-left': '0.8em',
            'color': baseColor,
        },
        'ul': {
            'margin-left': '0',
            'padding-left': '0.8em',
            'list-style': 'circle',
            'color': baseColor,
        },
        'footnotes': {
            'margin': '0.4em 6px',
            'font-size': '75%',
            'color': baseColor,
        },
        'figure': {
            'margin': '1.2em 6px',
            'color': baseColor,
        },
        'hr': {
            'border-style': 'solid',
            'border-width': '1px 0 0',
            'border-color': 'rgba(0,0,0,0.1)',
            '-webkit-transform-origin': '0 0',
            '-webkit-transform': 'scale(1, 0.5)',
            'transform-origin': '0 0',
            'transform': 'scale(1, 0.5)',
        },
    },
    'inline': {
        'listitem': {
            'text-indent': '-0.8em',
            'display': 'block',
            'margin': '0.2em 6px',
            'color': baseColor,
        },
        'codespan': {
            'font-size': '85%',
            'color': '#d14',
            'background': 'rgba(27,31,35,.05)',
            'padding': '2px 4px',
            'border-radius': '3px',
        },
        'link': {
            'color': '#576b95',
        },
        'wx_link': {
            'color': '#576b95',
            'text-decoration': 'none',
        },
        'strong': {
            'color': 'rgba(15, 76, 129, 0.9)',
            'font-weight': 'bold',
        },
        'table': {
            'border-collapse': 'collapse',
            'text-align': 'center',
            'margin': '0.8em 6px',
            'color': baseColor,
        },
        'thead': {
            'background': 'rgba(0, 0, 0, 0.05)',
            'font-weight': 'bold',
            'color': baseColor,
        },
        'td': {
            'border': '1px solid #dfdfdf',
            'padding': '0.2em 0.4em',
            'color': baseColor,
        },
        'footnote': {
            'font-size': '11px',
            'color': baseColor,
        },
        'figcaption': {
            'text-align': 'center',
            'color': '#888',
            'font-size': '0.75em',
        },
    },
}

opts = {
    'theme': theme,
    'fonts': 'Helvetica, Arial, sans-serif',
    'size': '16px',
    'code_theme': 'default',
}

renderer = WxRenderer(opts)


if __name__ == "__main__":
    import sys
    import yaml
    import codecs
    file_path = sys.argv[1]
    with codecs.open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        meta_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if meta_match:
            meta_yaml = meta_match.group(1)
            meta = yaml.safe_load(meta_yaml)
            content = content[meta_match.end():]
            renderer = WxRenderer(opts)
    html_content = renderer.render(content)
    with open('test.html', 'w') as f:
        f.write(html_content)

