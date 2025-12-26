FROM nginx:alpine

# デフォルト設定を削除
RUN rm /etc/nginx/conf.d/default.conf

# カスタム設定をコピー
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
