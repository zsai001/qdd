const fs = require('fs');
const path = require('path');
const fetch = require('node-fetch');
const { exec } = require('child_process');
const { JSDOM } = require('jsdom');


// 读取 test.md 文件
const markdownContent = fs.readFileSync(path.join(__dirname, 'test.md'), 'utf-8');

function processHtmlForWechat(htmlString) {
    const dom = new JSDOM(htmlString);
    const document = dom.window.document;

    // 修改HTML结构
    function modifyHtmlStructure() {
        const originalItems = document.querySelectorAll('li > ul, li > ol');
        originalItems.forEach((originalItem) => {
            originalItem.parentElement.insertAdjacentElement('afterend', originalItem);
        });
    }

    // 调整KaTeX公式元素
    function adjustKatexElements() {
        const katexElements = document.querySelectorAll('.base');
        katexElements.forEach(element => {
            element.style.display = 'inline';
            const topStyle = element.style.top;
            if (topStyle) {
                const emValue = topStyle.replace('em', '').trim();
                element.style.transform = `translateY(${emValue}em)`;
                element.style.removeProperty('top');
            }
        });
    }

    // 替换颜色变量
    function replaceColorVariables() {
        const elementsWithColor = document.querySelectorAll('[style*="var(--el-text-color-regular)"]');
        elementsWithColor.forEach(element => {
            element.style.color = '#3f3f3f';
        });
    }

    // 执行修改
    modifyHtmlStructure();
    adjustKatexElements();
    replaceColorVariables();

    return dom.serialize();
}


// 调用 RPC 服务
fetch('http://localhost:3000/render', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        markdown: markdownContent,
        color: '#FF5733',
        fontSize: '16px',
        customCss: JSON.stringify({
            'block.h1': { 'border-bottom': '2px solid #FF5733' }
        })
    }),
})
    .then(response => response.json())
    .then(data => {
        // 直接将返回的完整HTML写入文件
        fs.writeFileSync(path.join(__dirname, 'out.txt'), data.html);
        console.log('HTML has been saved to out.html');

        const wxCompatibleHtml = processHtmlForWechat(data.html);

        // 将处理后的HTML保存到wxout.txt文件
        fs.writeFileSync(path.join(__dirname, 'wxout.txt'), wxCompatibleHtml);

        // 构建完整的HTML，包括样式
        const fullHtml = `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Rendered Markdown</title>
                <style>
                    /* 添加额外的全局样式 */
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
                        line-height: 1.6;
                        padding: 20px;
                        max-width: 800px;
                        margin: 0 auto;
                    }
                </style>
                <link type="text/css" rel="stylesheet" href="https://cdn-doocs.oss-cn-shenzhen.aliyuncs.com/npm/highlight.js@11.5.1/styles/atom-one-dark.min.css" id="hljs">
            </head>
            <body>
                ${data.html}
            </body>
            </html>
            `;
        fs.writeFileSync(path.join(__dirname, 'out.html'), fullHtml);
        // 使用默认浏览器打开 out.html
        const outPath = path.join(__dirname, 'out.html');
        switch (process.platform) {
            case 'darwin':
                exec(`open ${outPath}`);
                break;
            case 'win32':
                exec(`start ${outPath}`);
                break;
            default:
                exec(`xdg-open ${outPath}`);
        }
    })
    .catch(error => console.error('Error:', error));