const { marked } = require("marked");
const hljs = require("highlight.js");
const markedKatex = require("marked-katex-extension");

marked.use(markedKatex({
  throwOnError: false,
  output: `html`
}));

codeThemeOption: [
  {
    label: `github`,
    value: `https://cdn-doocs.oss-cn-shenzhen.aliyuncs.com/npm/highlight.js@11.5.1/styles/github.min.css`,
    desc: `light`,
  },
  {
    label: `solarized-light`,
    value: `https://cdn-doocs.oss-cn-shenzhen.aliyuncs.com/npm/highlight.js@11.5.1/styles/solarized-light.min.css`,
    desc: `light`,
  },
  {
    label: `atom-one-dark`,
    value: `https://cdn-doocs.oss-cn-shenzhen.aliyuncs.com/npm/highlight.js@11.5.1/styles/atom-one-dark.min.css`,
    desc: `dark`,
  },
  {
    label: `obsidian`,
    value: `https://cdn-doocs.oss-cn-shenzhen.aliyuncs.com/npm/highlight.js@11.5.1/styles/obsidian.min.css`,
    desc: `dark`,
  },
  {
    label: `vs2015`,
    value: `https://cdn-doocs.oss-cn-shenzhen.aliyuncs.com/npm/highlight.js@11.5.1/styles/vs2015.min.css`,
    desc: `dark`,
  },
],

class WxRenderer {
  constructor(opts) {
    this.opts = opts;
    this.footnotes = [];
    this.footnoteIndex = 0;
    this.styleMapping = new Map();

    this.buildTheme = this.buildTheme.bind(this);
    this.getStyles = this.getStyles.bind(this);
    this.addFootnote = this.addFootnote.bind(this);
    this.buildFootnotes = this.buildFootnotes.bind(this);
    this.buildAddition = this.buildAddition.bind(this);
    this.setOptions = this.setOptions.bind(this);
    this.hasFootnotes = this.hasFootnotes.bind(this);
    this.getRenderer = this.getRenderer.bind(this);
  }

  buildTheme(themeTpl) {
    let mapping = {};
    let base = Object.assign({}, themeTpl.BASE, {
      "font-family": this.opts.fonts,
      "font-size": this.opts.size
    });
    for (let ele in themeTpl.inline) {
      if (themeTpl.inline.hasOwnProperty(ele)) {
        let style = themeTpl.inline[ele];
        mapping[ele] = Object.assign({}, base, style);
      }
    }

    let base_block = Object.assign({}, base);
    for (let ele in themeTpl.block) {
      if (themeTpl.block.hasOwnProperty(ele)) {
        let style = themeTpl.block[ele];
        mapping[ele] = Object.assign({}, base_block, style);
      }
    }
    return mapping;
  }

  getStyles(tokenName, addition) {
    let arr = [];
    let dict = this.styleMapping[tokenName];
    if (!dict) return "";
    for (const key in dict) {
      arr.push(key + ":" + dict[key]);
    }
    return `style="${arr.join(";") + (addition || "")}"`;
  }

  addFootnote(title, link) {
    this.footnotes.push([++this.footnoteIndex, title, link]);
    return this.footnoteIndex;
  }

  buildFootnotes() {
    let footnoteArray = this.footnotes.map((x) => {
      if (x[1] === x[2]) {
        return `<code style="font-size: 90%; opacity: 0.6;">[${x[0]}]</code>: <i>${x[1]}</i><br/>`;
      }
      return `<code style="font-size: 90%; opacity: 0.6;">[${x[0]}]</code> ${x[1]}: <i>${x[2]}</i><br/>`;
    });
    if (!footnoteArray.length) {
      return "";
    }
    return `<h4 ${this.getStyles("h4")}>引用链接</h4><p ${this.getStyles("footnotes")}>${footnoteArray.join("\n")}</p>`;
  }

  buildAddition() {
    return `
      <style>
      .preview-wrapper pre::before {
          position: absolute;
          top: 0;
          right: 0;
          color: #ccc;
          text-align: center;
          font-size: 0.8em;
          padding: 5px 10px 0;
          line-height: 15px;
          height: 15px;
          font-weight: 600;
      }
      </style>
    `;
  }

  setOptions(newOpts) {
    this.opts = Object.assign({}, this.opts, newOpts);
  }

  hasFootnotes() {
    return this.footnotes.length !== 0;
  }

  getRenderer(status) {
    this.footnotes = [];
    this.footnoteIndex = 0;

    this.styleMapping = this.buildTheme(this.opts.theme);
    let renderer = new marked.Renderer();

    renderer.heading = (text, level) => {
      switch (level) {
        case 1:
          return `<h1 ${this.getStyles("h1")}>${text}</h1>`;
        case 2:
          return `<h2 ${this.getStyles("h2")}>${text}</h2>`;
        case 3:
          return `<h3 ${this.getStyles("h3")}>${text}</h3>`;
        default:
          return `<h4 ${this.getStyles("h4")}>${text}</h4>`;
      }
    };

    renderer.paragraph = (text) => {
      if (text.indexOf("<figure") != -1 && text.indexOf("<img") != -1) {
        return text;
      }
      return text.replace(/ /g, "") === ""
        ? ""
        : `<p ${this.getStyles("p")}>${text}</p>`;
    };

    renderer.blockquote = (text) => {
      text = text.replace(/<p.*?>/g, `<p ${this.getStyles("blockquote_p")}>`);
      return `<blockquote ${this.getStyles("blockquote")}>${text}</blockquote>`;
    };

    renderer.code = (text, lang = "") => {
      if (lang.startsWith("mermaid")) {
        return `<center><pre class="mermaid">${text}</pre></center>`;
      }
      lang = lang.split(" ")[0];
      lang = hljs.getLanguage(lang) ? lang : "plaintext";
      text = hljs.highlight(text, { language: lang }).value;
      text = text
        .replace(/\r\n/g, "<br/>")
        .replace(/\n/g, "<br/>")
        .replace(/(>[^<]+)|(^[^<]+)/g, function (str) {
          return str.replace(/\s/g, "&nbsp;");
        });

      return `<pre class="hljs code__pre" ${this.getStyles("code_pre")}><code class="language-${lang}" ${this.getStyles("code")}>${text}</code></pre>`;
    };

    renderer.codespan = (text) =>
      `<code ${this.getStyles("codespan")}>${text}</code>`;

    renderer.listitem = (text) =>
      `<li ${this.getStyles("listitem")}><span><%s/></span>${text}</li>`;

    renderer.list = (text, ordered, start) => {
      text = text.replace(/<\/*p .*?>/g, "").replace(/<\/*p>/g, "");
      let segments = text.split(`<%s/>`);
      if (!ordered) {
        text = segments.join("• ");
        return `<ul ${this.getStyles("ul")}>${text}</ul>`;
      }
      text = segments[0];
      for (let i = 1; i < segments.length; i++) {
        text = text + i + ". " + segments[i];
      }
      return `<ol ${this.getStyles("ol")}>${text}</ol>`;
    };

    renderer.image = (href, title, text) => {
      const subText = this.createSubText(this.transform(title, text));
      const figureStyles = this.getStyles("figure");
      const imgStyles = this.getStyles("image");
      return `<figure ${figureStyles}><img ${imgStyles} src="${href}" title="${title}" alt="${text}"/>${subText}</figure>`;
    };

    renderer.link = (href, title, text) => {
      if (href.startsWith("https://mp.weixin.qq.com")) {
        return `<a href="${href}" title="${title || text}" ${this.getStyles("wx_link")}>${text}</a>`;
      }
      if (href === text) {
        return text;
      }
      if (status) {
        let ref = this.addFootnote(title || text, href);
        return `<span ${this.getStyles("link")}>${text}<sup>[${ref}]</sup></span>`;
      }
      return `<span ${this.getStyles("link")}>${text}</span>`;
    };

    renderer.strong = (text) =>
      `<strong ${this.getStyles("strong")}>${text}</strong>`;

    renderer.em = (text) =>
      `<span style="font-style: italic;">${text}</span>`;

    renderer.table = (header, body) =>
      `<section style="padding:0 8px;"><table class="preview-table"><thead ${this.getStyles("thead")}>${header}</thead><tbody>${body}</tbody></table></section>`;

    renderer.tablecell = (text, flags) =>
      `<td ${this.getStyles("td")}>${text}</td>`;

    renderer.hr = () => `<hr ${this.getStyles("hr")}>`;

    return renderer;
  }

  createSubText(s) {
    return s ? `<figcaption ${this.getStyles("figcaption")}>${s}</figcaption>` : "";
  }

  transform(title, alt) {
    // const legend = localStorage.getItem("legend");
    const legend = 'alt-title';
    switch (legend) {
      case "alt":
        return alt;
      case "title":
        return title;
      case "alt-title":
        return alt || title;
      case "title-alt":
        return title || alt;
      default:
        return "";
    }
  }

  getThemeStyle() {
    let style = '';
    for (const [selector, rules] of Object.entries(this.theme)) {
        style += `${selector} {\n`;
        for (const [property, value] of Object.entries(rules)) {
            style += `  ${property}: ${value};\n`;
        }
        style += '}\n';
    }
    return style;
}
}

module.exports = WxRenderer;