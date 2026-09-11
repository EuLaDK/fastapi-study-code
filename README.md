# FastAPI 学习案例

每个主题在 `main.py` 中注册路由，`test.http` 提供 REST Client 请求。

## SQLModel + PostgreSQL

示例集中在 `src/routers/sqlmodel_example.py`，入口是 `/db`，使用 FastAPI 官方教程的
`SQLModel`、`Session`、`Depends`、`model_validate()` 和 `sqlmodel_update()` 写法。

### 本地启动

```powershell
uv sync
# 首次配置时复制模板；已配置 .env 时不要覆盖。
Copy-Item .env.example .env
# 编辑 .env，填写自己的 PostgreSQL 密码。
uv run fastapi dev main.py --host 127.0.0.1 --port 8000
```

`.env` 中的连接变量如下（密码如果包含 @、:、/ 等 URL 特殊字符，需要 URL 编码）：

```dotenv
SQLMODEL_DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@127.0.0.1:5432/fastapi_sqlmodel_demo
```

本机已创建独立的 `fastapi_sqlmodel_demo` 数据库并配置 `.env`。
换电脑时，需要先在 PostgreSQL 创建同名空数据库。应用启动时通过 router 的
`lifespan` 自动创建 `sqlmodel_demo_team` 和 `sqlmodel_demo_hero` 两张表，数据库必须可连接。
`.env` 已被 Git 忽略，仓库只保留不含真实密码的 `.env.example`。

启动后打开 http://127.0.0.1:8000/docs 中的“SQLModel数据库”，或者按顺序执行
`test.http` 的 SQLModel 请求。先运行命名的 `createSqlTeam`、`createSqlHero` 请求，
后面的请求会自动引用响应里的 ID，无需手动填写。

### 覆盖的开发用法

| 用法 | 代码或接口 |
| --- | --- |
| 数据库健康检查 | `GET /db/health` 执行真实 SQL |
| 建表、主键、索引和唯一约束 | `Team`、`Hero` 的 `table=True`、`Field` |
| 请求/数据库/响应模型分离 | Create、Update、Public 模型；响应隐藏 `secret_name` |
| 每个请求独立会话 | `get_session()` 用 `yield` 注入，结束后自动关闭 |
| 创建队伍和成员 | `POST /db/teams/`；`heroes` 可省略，也可一次创建多个 |
| 队伍查询、修改、删除 | `GET /db/teams/`、`GET/PATCH/DELETE /db/teams/{id}` |
| 英雄增删改查 | `POST/GET /db/heroes/`、`GET/PATCH/DELETE /db/heroes/{id}` |
| 分页和总数 | `offset`、`limit`；英雄列表返回 `items/total/offset/limit` |
| 筛选和稳定排序 | `q`、`team_id`、`min_age`、`sort_by`、`descending` |
| 一对多关系 | 一个队伍多个英雄；详情返回关联模型，不递归嵌套 |
| 原子事务与回滚 | 创建队伍及成员只提交一次，其中一个重名则整批回滚 |
| 数据完整性 | 数据库唯一约束和外键；有英雄的队伍禁止删除，返回 409 |
| 日期时间 | PostgreSQL 带时区时间列，接口统一使用 UTC |
| 错误处理 | 不存在 404、数据库约束冲突 409、请求校验失败 422 |

`PATCH` 使用 `model_dump(exclude_unset=True)`：不传的字段保持原值；
`age` 和 `team_id` 可以传 `null` 清空；`name`、`secret_name`、`headquarters` 不能为 `null`。
输入模型禁止额外字段，客户端不能修改 `id` 或创建时间。

同步 PostgreSQL 驱动配合 `def` 接口，由 FastAPI 在线程池执行。
写入在接口返回前 `commit()`；约束失败先 `rollback()` 再返回 409，
关闭会话时也会回滚尚未提交的事务。

### 自动验证

```powershell
uv run python -B test_sqlmodel.py
```

检查真实 PostgreSQL 上的 CRUD、关联、分页筛选、PATCH、约束冲突和整批回滚。
测试使用外层事务和 savepoint，结束后回滚测试数据，不清空已有表。
PostgreSQL 自增序列不随回滚还原，因此测试后 ID 不连续是正常现象。

这是本地教学案例，数据库接口尚未加登录权限；需要受保护的接口时，可组合已有的认证依赖。
`create_all()` 只创建缺失的表，不会修改已存在的列；后续改表结构时应使用 Alembic 迁移。

参考：[FastAPI SQL 数据库教程](https://fastapi.tiangolo.com/tutorial/sql-databases/)、
[SQLModel 官方文档](https://sqlmodel.tiangolo.com/)。
