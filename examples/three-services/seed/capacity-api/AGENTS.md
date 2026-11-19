# 名额服务

server.py 提供内部名额接口，fixtures.json 是合成数据。python3 server.py --port 4282 可独立启动。已有单活动接口为 /internal/capacities/A102。

批量能力、剩余名额计算、越权与错误行为按工作区共同契约实现。实际 HTTP 调用必须按请求身份确定租户范围。
