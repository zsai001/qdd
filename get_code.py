import base64
from playwright.sync_api import sync_playwright
import tempfile
import os
from PIL import Image
import io
import textwrap

def format_code(code, max_width=80):
    lines = code.split('\n')
    formatted_lines = []
    for line in lines:
        if len(line) > max_width:
            # Use textwrap to split long lines
            wrapped = textwrap.wrap(line, width=max_width, break_long_words=False, replace_whitespace=False)
            formatted_lines.extend(wrapped)
        else:
            formatted_lines.append(line)
    return '\n'.join(formatted_lines)

def code_to_png(code, language, save_path, max_width=80):
    formatted_code = format_code(code, max_width)
    
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Code Preview</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #b388ff 0%, #7c4dff 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            }}
            .editor-container {{
                background-color: rgba(41, 42, 48, 0.85);
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                width: 720px;
                margin: 40px;
            }}
            .window-controls {{
                background-color: rgba(58, 58, 58, 0.85);
                padding: 10px;
                display: flex;
                align-items: center;
            }}
            .control {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 6px;
            }}
            .close {{ background-color: #FF5F56; }}
            .minimize {{ background-color: #FFBD2E; }}
            .maximize {{ background-color: #27C93F; }}
            .code-content {{
                padding: 20px;
                overflow-x: auto;
            }}
            pre {{
                margin: 0;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
            code {{
                font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier', monospace;
                font-size: 18px;
                line-height: 1.5;
            }}
            .hljs {{
                background-color: transparent !important;
                padding: 0 !important;
                color: #FFFFFF;
            }}
            .hljs-keyword {{ color: #FF7AB2; }}
            .hljs-string {{ color: #FF8170; }}
            .hljs-number {{ color: #D9C97C; }}
            .hljs-built_in {{ color: #78C2B3; }}
            .hljs-function {{ color: #78C2B3; }}
        </style>
    </head>
    <body>
        <div class="editor-container">
            <div class="window-controls">
                <div class="control close"></div>
                <div class="control minimize"></div>
                <div class="control maximize"></div>
            </div>
            <div class="code-content">
                <pre><code class="language-{language}">{code}</code></pre>
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/atom-one-dark.min.css">
        <script>hljs.highlightAll();</script>
    </body>
    </html>
    """

    html_content = HTML_TEMPLATE.format(code=formatted_code, language=language)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp_file:
        tmp_file.write(html_content.encode('utf-8'))
        tmp_file_path = tmp_file.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 800, 'height': 600}, device_scale_factor=2)
            page.goto(f'file://{tmp_file_path}')
            page.wait_for_load_state('networkidle')

            page.evaluate('() => hljs.highlightAll()')

            bbox = page.evaluate('''() => {
                const container = document.querySelector('.editor-container');
                const rect = container.getBoundingClientRect();
                return {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                };
            }''')

            screenshot = page.screenshot(
                clip={
                    'x': bbox['x'] - 20,
                    'y': bbox['y'] - 20,
                    'width': bbox['width'] + 40,
                    'height': bbox['height'] + 40
                },
                path=None
            )
            browser.close()

        with Image.open(io.BytesIO(screenshot)) as img:
            img.save(save_path, format="PNG")

        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

    finally:
        os.unlink(tmp_file_path)
        
if __name__ == "__main__":
    code = """
func NewSimpleClient(addr string, interval int, logger fklog.FKLogI) *SimpleClient {
	fk := NewFkClient(addr, interval, logger)
	protocol := &SimpleClient{client: fk}
	fk.ConnectWithProtocol(protocol)
	if logger == nil {
		fk.FKLogI = fklog.AppLogger().Clone("FkClient")
		protocol.FKLogI = fklog.AppLogger().Clone("SimpleClient")
		fk.WarnWF("NewSimpleClient logger")
	} else {
		fk.FKLogI = logger.Clone("FkClient")
		protocol.FKLogI = logger.Clone("SimpleClient")
		fk.WarnWF("NewSimpleClient logger2")
	}
	return protocol
}
    """
    result = code_to_png(code=code, language="golang", save_path="code_image.png")
    if result:
        print("Image created successfully!")
    else:
        print("Failed to create image.")