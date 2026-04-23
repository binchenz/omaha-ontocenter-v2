# Phase 5: Pipeline 调度引擎设计

## 背景

Phase 4 实现了 Pipeline 的 CRUD API 和手动 /run 端点，但没有后台进程按 cron 表达式自动执行 pipeline。这是 Foundry 数据底座最核心的缺失能力 — 数据不能自动流动。

## 目标

让 `status=active` 的 Pipeline 按各自的 cron schedule 自动执行，无需人工干预。

## 架构

APScheduler 进程内调度，与 FastAPI 共享进程。

```
FastAPI lifespan startup
  └→ PipelineScheduler.start()
       └→ 从 DB 加载所有 active pipelines
       └→ 为每个 pipeline 注册 CronTrigger job
       └→ APScheduler BackgroundScheduler 后台线程执行

Pipeline CRUD API (create/update/delete)
  └→ 同步更新 APScheduler job (add/modify/remove)

FastAPI lifespan shutdown
  └→ PipelineScheduler.stop()
```

## 核心组件

### `backend/app/services/scheduler.py` — PipelineScheduler

```python
class PipelineScheduler:
    def start(self):
        """初始化 APScheduler，从 DB 加载所有 active pipelines 并注册 cron jobs。"""

    def stop(self):
        """优雅关闭调度器。"""

    def add_pipeline(self, pipeline_id: int):
        """为一个 pipeline 注册 cron job。"""

    def remove_pipeline(self, pipeline_id: int):
        """移除一个 pipeline 的 job。"""

    def sync_pipeline(self, pipeline_id: int):
        """pipeline 的 schedule 或 status 变化时，更新 job。"""
```

每个 job 执行函数：
1. 创建独立的 DB session（不复用 FastAPI 的 request session）
2. 加载 pipeline + project.omaha_config
3. 调用现有的 `run_pipeline(pipeline, config_yaml, db)`
4. 关闭 session

### 保护机制

- **并发限制：** ThreadPoolExecutor max_workers=5（不抢 FastAPI 线程）
- **跳过重叠：** `coalesce=True` + `max_instances=1`（上一次还在跑就跳过本次）
- **misfire 容忍：** `misfire_grace_time=300`（5 分钟内的 misfire 仍然执行）
- **执行超时：** 不在调度器层面做超时（Python 线程无法安全 kill），而是在 `run_pipeline` 里对 Tushare/REST 等外部调用设置 request timeout

### FastAPI 集成

使用 FastAPI 的 `lifespan` 上下文管理器：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.stop()

app = FastAPI(lifespan=lifespan)
```

### API 变化

修改 `backend/app/api/pipelines.py`：
- `create_pipeline` 末尾调用 `scheduler.add_pipeline(pipeline.id)`
- `update_pipeline` 末尾调用 `scheduler.sync_pipeline(pipeline.id)`
- `delete_pipeline` 前调用 `scheduler.remove_pipeline(pipeline.id)`

### 前端变化

无。PipelineManager 已有 status/last_run_at/last_run_status 展示，调度器运行后这些字段会自动更新。

## 依赖

`apscheduler==3.10.4` 添加到 `backend/requirements.txt`

## 测试策略

- 单元测试：PipelineScheduler 的 add/remove/sync 方法（mock APScheduler）
- 集成测试：创建 pipeline → 验证 job 被注册 → 手动触发 job → 验证 pipeline 状态更新
- 现有测试：确保 Pipeline CRUD 测试不受影响

## 不在范围内

- 分布式调度（Celery）— 当前单进程足够
- 「下次运行时间」前端展示 — 简化，只显示 cron 表达式
- 增量同步 — 当前仍是全量替换（`if_exists="replace"`）
- Pipeline 执行历史表 — 当前只记录最后一次运行状态
