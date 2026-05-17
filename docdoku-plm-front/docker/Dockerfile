FROM nginx:1.19.1-alpine

# 旧 Grunt 产物（AMD 轨道）
COPY dist /usr/share/nginx/html

# Vite 产物：assets 目录（内容哈希文件名，与 Grunt 产物无冲突）
COPY dist-vite/assets /usr/share/nginx/html/assets

# Vue 3 SFC 版 account-management（新轨道，并存供验证；验证通过后覆盖旧目录即可切换）
COPY dist-vite/account-management-vue /usr/share/nginx/html/account-management-vue

# Vue 3 SFC 版 workspace-management（阶段 4，新轨道）
COPY dist-vite/workspace-management-vue /usr/share/nginx/html/workspace-management-vue

# Vue 3 SFC 版 change-management（阶段 5，新轨道）
COPY dist-vite/change-management-vue /usr/share/nginx/html/change-management-vue

# Vue 3 SFC 版 document-management（阶段 6，新轨道）
COPY dist-vite/document-management-vue /usr/share/nginx/html/document-management-vue

# Vue 3 SFC 版 main（阶段 7，Vue 版登录页 + 模块卡片菜单）
COPY dist-vite/main-vue /usr/share/nginx/html/main-vue

# Vue 3 SFC 版 organization-management（阶段 8，新轨道）
COPY dist-vite/organization-management-vue /usr/share/nginx/html/organization-management-vue

# Vite ESM 版 download（阶段 2 产物）
COPY dist-vite/download /usr/share/nginx/html/download-vite

COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
