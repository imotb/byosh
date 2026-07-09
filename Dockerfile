FROM alpine:edge
LABEL maintainer="Ali Mosajjal <hi@n0p.me>"

RUN apk add --no-cache nginx nginx-mod-stream py3-pip \
    && pip3 install --no-cache-dir dnslib \
    && mkdir -p /run/nginx

COPY nginx.conf /etc/nginx/nginx.conf
COPY dns.py /opt/dns.py
COPY domains /opt/domains
COPY entrypoint.sh /entrypoint.sh

RUN nginx -t && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
