FROM docker.elastic.co/elasticsearch/elasticsearch:8.15.2

# 安装官方提供的 SmartCN 中文分词插件，确保索引阶段能识别中文词语。
RUN elasticsearch-plugin install --batch analysis-smartcn
