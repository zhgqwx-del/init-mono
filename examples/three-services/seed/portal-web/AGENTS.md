# 运营界面

public/app.js 负责编辑与已提交条件、分页及渲染。public/index.html 放表单与表格。server.py 提供本地静态资源，并为真实 campaign-api 请求附演示租户 A 身份。

python3 server.py --port 4280 --api-port 4281 可独立启动。在任务工作区核对 task.json 和跨服务契约，再修改界面与请求。分页沿用已提交条件。
