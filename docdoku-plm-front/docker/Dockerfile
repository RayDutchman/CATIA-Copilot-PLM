FROM nginx:1.19.1-alpine

COPY dist /usr/share/nginx/html
COPY docker/entrypoint.sh /entrypoint.sh
# 将正确的 nginx 配置打入镜像，确保离线部署无需 bind mount 也能正常工作
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
