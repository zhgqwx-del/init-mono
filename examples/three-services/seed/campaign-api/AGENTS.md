# 活动服务

server.py 负责 GET /ops/api/v1/campaigns。fixtures.json 保存两个租户的活动。python3 server.py --port 4281 --capacity-port 4282 启动本地服务。

查询条件、total 与分页必须按同一组可见范围处理。增加可选能力时保留旧调用的响应结构。需要名额时通过 HTTP 访问 capacity-api，并沿用调用方演示身份。仓外 tasks/FEAT-301 维护共同契约与验收。
