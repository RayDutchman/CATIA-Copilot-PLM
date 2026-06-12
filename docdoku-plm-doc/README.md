docdoku-plm-doc
===============

This project handles the DocdokuPLM user-guide and documentation.

## Build requirements

Ruby, Jekyll 2.1.0, nodejs, git, grunt, bower

### Jekyll

Install local jekyll from given ruby gem

	[sudo] gem install jekyll -v 2.1.0

### NodeJS
Use latest LTS version

### Git

Latest

### Grunt and Bower

Latest

### NPX

Latest


## Configuration

Please edit the \_config.yml file if you plan to deploy on a different path than server root

To build the doc, run 

	npm run build

To develop, use
	
	npm run dev

---

## 实际部署说明（当前环境：Ubuntu 26.04 / Jekyll 4.4.1）

原版要求 Jekyll 2.1.0 + Ruby 2.x，但 Ubuntu 26.04 的 GCC 无法编译 Ruby 2.7，
Jekyll 2.1.0 的原生扩展在 Ruby 3.x 下也无法安装。
因此对三个文件做了最小兼容性修改，使其在 Jekyll 4.4.1 + Ruby 3.3 下正常构建。

### 修改内容（相对原版）

**`app/_config.dev.yml`**
- 移除 `relative_permalinks: true`（Jekyll 3+ 已废弃此选项，会导致硬错误）

**`app/_plugins/multiple-language.rb`**
- 移除 `alias :read_posts_org :read_posts` 及对应方法（Jekyll 4 已删除 `read_posts`）
- `self.dest =` 改为 `@dest =`（Jekyll 4 的 `Site#dest` 无 setter）

**`app/_plugins/relative.rb`**
- 移除 `Jekyll::Post` 类扩展（Jekyll 3+ 已删除该类）
- `url.split("/").length-2` 加 `.max(0)` 保护，避免根路径下出现负数

### 构建步骤

```bash
# 1. 安装前端依赖（仅首次或 bower.json 变更后）
cd docdoku-plm-doc
npx bower install --allow-root

# 2. 构建静态站点
cd app
jekyll build --config _config.dev.yml

# 3. 将前端依赖复制到构建产物
# （bower_components 必须 exclude，否则 Jekyll 4 会尝试处理其中的 _layouts/_includes 文件）
cp -r bower_components _site/bower_components

# 4. 启动静态文件服务器（用 python3，避免 npx serve 的 URL 重写问题）
python3 -m http.server 4200 --directory _site --bind 0.0.0.0
```

访问地址：http://localhost:4200

### 为什么不用 jekyll serve

`jekyll serve` 会在运行时把 `url` 强制覆盖为 `http://host:port`，
而模板使用 `{{ site.url }}en/...` 拼接路径（无分隔斜杠），
导致所有内部链接变为无效地址。
`jekyll build` + 独立静态服务器可完全规避此问题。

### 为什么不用 npx serve

`serve` 14.x 会对 `.html` 文件做 URL 美化（301 去掉扩展名），
导致站点内 `/en/2.5/index.html` 等链接被重定向到不存在的路径。
`python3 -m http.server` 不做任何 URL 重写，行为与预期一致。
