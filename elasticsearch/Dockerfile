FROM docker.elastic.co/elasticsearch/elasticsearch:8.15.2

USER root
# 预先下载 SmartCN 插件包并离线安装，避免构建时的网络/权限问题。
ADD https://artifacts.elastic.co/downloads/elasticsearch-plugins/analysis-smartcn/analysis-smartcn-8.15.2.zip /tmp/analysis-smartcn.zip
RUN chown elasticsearch:elasticsearch /tmp/analysis-smartcn.zip && \
    su elasticsearch -c "/usr/share/elasticsearch/bin/elasticsearch-plugin install --batch file:///tmp/analysis-smartcn.zip"
USER elasticsearch
