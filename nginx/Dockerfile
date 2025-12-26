FROM nginx:alpine

# デフォルト設定を削除
RUN rm /etc/nginx/conf.d/default.conf

# カスタム設定と静的ファイルをコピー
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/build /usr/share/nginx/html

EXPOSE 80
