const prettier = require('prettier/standalone');
const prettierCss = require('prettier/parser-postcss');
const prettierMarkdown = require('prettier/parser-markdown');
const defaultTheme = require('./theme');

const createCustomTheme = (theme, color) => {
    const customTheme = JSON.parse(JSON.stringify(theme));
    customTheme.block.h1['border-bottom'] = `2px solid ${color}`;
    customTheme.block.h2['background'] = color;
    customTheme.block.h3['border-left'] = `3px solid ${color}`;
    customTheme.block.h4['color'] = color;
    customTheme.inline.strong['color'] = color;
    return customTheme;
};

function setColorWithTemplate(theme) {
    return (color) => {
        return createCustomTheme(theme, color);
    };
}

function setColorWithCustomTemplate(theme, color) {
    return createCustomTheme(theme, color);
}

function setFontSizeWithTemplate(template) {
    return function (fontSize) {
        const customTheme = JSON.parse(JSON.stringify(template));
        customTheme.block.h1['font-size'] = `${fontSize * 1.14}px`;
        customTheme.block.h2['font-size'] = `${fontSize * 1.1}px`;
        customTheme.block.h3['font-size'] = `${fontSize}px`;
        customTheme.block.h4['font-size'] = `${fontSize}px`;
        return customTheme;
    };
}

function formatDoc(content) {
    return prettier.format(content, {
        parser: 'markdown',
        plugins: [prettierMarkdown],
    });
}

function formatCss(content) {
    return prettier.format(content, {
        parser: 'css',
        plugins: [prettierCss],
    });
}

// 导出所有函数
module.exports = {
    setColorWithTemplate,
    setColorWithCustomTemplate,
    setFontSizeWithTemplate,
    formatDoc,
    formatCss,
    // 如果还有其他函数，也在这里导出
};