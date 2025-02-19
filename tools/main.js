const express = require('express');
const { marked } = require('marked');
const hljs = require('highlight.js');
const markedKatex = require('marked-katex-extension');
const WxRenderer = require('./wx-renderer');
const { setColorWithTemplate, setFontSizeWithTemplate } = require('./util');
const defaultTheme = require('./theme')

const app = express();
app.use(express.json());

// 配置marked
marked.use(markedKatex({
    throwOnError: false,
    output: 'html'
}));

// 创建WxRenderer实例
const wxRenderer = new WxRenderer({
    theme: defaultTheme,
    fonts: 'default-font',
    size: '14px'
});

app.post('/render', (req, res) => {
    const { markdown, color, fontSize, customCss } = req.body;

    if (!markdown) {
        return res.status(400).json({ error: 'Markdown content is required' });
    }

    // 配置渲染器
    const renderer = wxRenderer.getRenderer(true);
    marked.use({ renderer });
    marked.setOptions({
        highlight: (code, lang) => {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        }
    });

    // 应用自定义样式
    let theme = defaultTheme;
    if (color) {
        theme = setColorWithTemplate(theme)(color);
    }
    if (fontSize) {
        theme = setFontSizeWithTemplate(theme)(fontSize);
    }
    if (customCss) {
        theme = { ...theme, ...JSON.parse(customCss) };
    }
    wxRenderer.setOptions({ theme });

    // 渲染Markdown
    let html = marked.parse(markdown);

    // 添加脚注和额外样式
    html += wxRenderer.buildFootnotes();
    html += wxRenderer.buildAddition();

    html += `
            <style>
                .hljs.code__pre::before {
                position: initial;
                padding: initial;
                content: '';
                display: block;
                height: 25px;
                background-color: transparent;
                background-image: url("https://doocs.oss-cn-shenzhen.aliyuncs.com/img/123.svg");
                background-position: 14px 10px!important;
                background-repeat: no-repeat;
                background-size: 40px!important;
                }

                .hljs.code__pre {
                padding: 0!important;
                }

                .hljs.code__pre code {
                display: -webkit-box;
                padding: 0.5em 1em 1em;
                overflow-x: auto;
                text-indent: 0;
                }
            </style>
            `

    // 获取主题样式
    // const themeStyles = wxRenderer.getThemeStyle();

    // 返回渲染后的完整HTML
    res.json({ html: html });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});