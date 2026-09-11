"""SQLModel + PostgreSQL 教学案例：模型、关联、增删改查和事务，接口前缀 /db。"""

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ConfigDict, field_validator
from sqlalchemy import CheckConstraint, DateTime, func, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Relationship, Session, SQLModel, col, create_engine, select


# Base 复用字段；table=True 才映射数据库表；Create/Update/Public 负责输入和输出。
class TeamBase(SQLModel):
    # 禁止客户端传入未声明的字段，并去掉字符串两端空格。
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80, unique=True, index=True)
    headquarters: str = Field(min_length=1, max_length=120)


class Team(TeamBase, table=True):
    __tablename__ = "sqlmodel_demo_team"

    id: int | None = Field(default=None, primary_key=True)
    # 和 Hero.team 双向关联；passive_deletes 让数据库执行删除限制，避免 ORM 先解绑成员。
    heroes: list["Hero"] = Relationship(
        back_populates="team", passive_deletes="all"
    )


class HeroBase(SQLModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80, unique=True, index=True)
    age: int | None = Field(default=None, ge=0, le=150)


class Hero(HeroBase, table=True):
    __tablename__ = "sqlmodel_demo_hero"
    # Field 的 ge/le 校验接口输入；CHECK 约束也能防止直接写 SQL 时存入非法年龄。
    __table_args__ = (
        CheckConstraint("age >= 0 AND age <= 150", name="ck_sqlmodel_hero_age"),
    )

    id: int | None = Field(default=None, primary_key=True)
    secret_name: str = Field(min_length=1, max_length=120)
    # team_id 是实际外键列；team 是 Python 关联对象，不会额外生成一列。
    # RESTRICT：队伍仍被英雄引用时禁止删除；team_id=None 表示未加入队伍。
    team_id: int | None = Field(
        default=None, foreign_key="sqlmodel_demo_team.id", ondelete="RESTRICT", index=True
    )
    team: Team | None = Relationship(back_populates="heroes")
    # default_factory 每次创建对象时生成时间；数据库保存带时区时间，避免时区歧义。
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )


class HeroInput(HeroBase):
    secret_name: str = Field(min_length=1, max_length=120)


class HeroCreate(HeroInput):
    team_id: int | None = Field(default=None, gt=0)


class HeroUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=80)
    secret_name: str | None = Field(default=None, min_length=1, max_length=120)
    age: int | None = Field(default=None, ge=0, le=150)
    team_id: int | None = Field(default=None, gt=0)

    # PATCH 可以省略字段，但显式传 name/secret_name=null 必须报错；默认省略值不触发此校验。
    @field_validator("name", "secret_name")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("This field may be omitted, but cannot be null")
        return value


# response_model 只输出 Public 声明的字段，所以即使返回 Hero 对象也不会暴露 secret_name。
class HeroPublic(HeroBase):
    id: int
    team_id: int | None
    created_at: datetime
    updated_at: datetime


class TeamCreate(TeamBase):
    heroes: list[HeroInput] = Field(default_factory=list, max_length=100)


class TeamUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=80)
    headquarters: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("name", "headquarters")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("This field may be omitted, but cannot be null")
        return value


class TeamPublic(TeamBase):
    id: int


# 关联响应只展开一层，避免“队伍 -> 英雄 -> 队伍”无限嵌套。
class TeamWithHeroes(TeamPublic):
    heroes: list[HeroPublic]


class HeroWithTeam(HeroPublic):
    team: TeamPublic | None


class HeroPage(SQLModel):
    items: list[HeroPublic]
    total: int
    offset: int
    limit: int


# Engine/连接池在进程内复用；Session 不能像这样全局共享。
@lru_cache
def get_engine():
    # 从当前模块目录向上查找 .env，移动文件后不再依赖固定的父目录层级。
    load_dotenv()
    database_url = os.getenv("SQLMODEL_DATABASE_URL")
    if not database_url:
        raise RuntimeError("Set SQLMODEL_DATABASE_URL in .env; see .env.example")
    return create_engine(
        database_url,
        pool_pre_ping=True,  # 从池中取连接时先检测是否存活，处理数据库重启后的旧连接。
        connect_args={"connect_timeout": 5, "options": "-c timezone=UTC"},
    )


@asynccontextmanager
async def lifespan(app):
    # 应用启动时执行 yield 前的代码，应用关闭时执行 finally；不是每次请求都建表。
    engine = get_engine()
    try:
        # ponytail: create_all 只创建缺失的表；已有表的结构变更改用 Alembic 迁移。
        SQLModel.metadata.create_all(engine, tables=[Team.__table__, Hero.__table__])
        yield
    finally:
        engine.dispose()


def get_session():
    # 每次请求注入独立 Session；yield 交给接口使用，结束后 with 自动关闭并回滚未提交事务。
    with Session(get_engine()) as session:
        yield session


# 复用依赖声明。下面用 def 接口配合同步驱动，由 FastAPI 在线程池执行数据库操作。
SessionDep = Annotated[Session, Depends(get_session)]
router = APIRouter(lifespan=lifespan)


def commit(session: Session):
    try:
        session.commit()
    except IntegrityError as exc:
        # 提交失败必须先回滚。唯一约束由数据库保证，并发时也不会写入同名记录。
        session.rollback()
        # PostgreSQL 错误码：23505 唯一约束冲突，23503 外键冲突；不把原始 SQL 返回给客户端。
        messages = {
            "23505": "A record with that name already exists",
            "23503": "Related record is missing, or the team still has heroes",
        }
        detail = messages.get(
            getattr(exc.orig, "sqlstate", None), "Database constraint conflict"
        )
        raise HTTPException(status_code=409, detail=detail) from exc


def get_team_or_404(session: Session, team_id: int) -> Team:
    team = session.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def get_hero_or_404(session: Session, hero_id: int) -> Hero:
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero


@router.get("/health")
def database_health(session: SessionDep):
    session.exec(text("SELECT 1")).one()
    return {"status": "ok", "database": "postgresql"}


@router.post("/teams/", response_model=TeamWithHeroes, status_code=201)
def create_team(data: TeamCreate, session: SessionDep):
    # 先把请求模型转成表模型，再通过关联对象添加成员；空 heroes 也可以创建独立队伍。
    print("data", data)
    team = Team.model_validate(data.model_dump(exclude={"heroes"}))
    print("team", team)
    team.heroes = [Hero.model_validate(hero) for hero in data.heroes]
    session.add(team)
    # ORM 自动填充成员的 team_id；只 commit 一次，任一成员写入失败则队伍和所有成员一起回滚。
    commit(session)
    session.refresh(team)
    return team


@router.get("/teams/", response_model=list[TeamPublic])
def list_teams(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return session.exec(select(Team).order_by(Team.id).offset(offset).limit(limit)).all()


@router.get("/teams/{team_id}", response_model=TeamWithHeroes)
def read_team(team_id: int, session: SessionDep):
    return get_team_or_404(session, team_id)


@router.patch("/teams/{team_id}", response_model=TeamPublic)
def update_team(team_id: int, data: TeamUpdate, session: SessionDep):
    team = get_team_or_404(session, team_id)
    team.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(team)
    commit(session)
    session.refresh(team)
    return team


@router.delete("/teams/{team_id}", status_code=204)
def delete_team(team_id: int, session: SessionDep):
    session.delete(get_team_or_404(session, team_id))
    commit(session)
    return Response(status_code=204)


@router.post("/heroes/", response_model=HeroPublic, status_code=201)
def create_hero(data: HeroCreate, session: SessionDep):
    if data.team_id is not None:
        get_team_or_404(session, data.team_id)
    hero = Hero.model_validate(data)
    # add 加入会话，commit 写入并提交，refresh 从数据库重新读取自增 ID 等最终值。
    session.add(hero)
    commit(session)
    session.refresh(hero)
    return hero


@router.get("/heroes/", response_model=HeroPage)
def list_heroes(
    session: SessionDep,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    team_id: Annotated[int | None, Query(gt=0)] = None,
    min_age: Annotated[int | None, Query(ge=0, le=150)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: Literal["id", "name", "age", "created_at"] = "id",
    descending: bool = False,
):
    filters = []
    if q is not None:
        # 不区分大小写的包含查询；autoescape 把用户输入的 %、_ 当成普通字符。
        filters.append(col(Hero.name).icontains(q, autoescape=True))
    if team_id is not None:
        filters.append(Hero.team_id == team_id)
    if min_age is not None:
        filters.append(col(Hero.age) >= min_age)
    # total 统计全部筛选结果，不能只统计当前页；多个 where 条件之间是 AND。
    total = session.exec(select(func.count()).select_from(Hero).where(*filters)).one()
    order = getattr(Hero, sort_by)  # Literal 限制可选列名，不能让客户端任意拼接排序 SQL。
    order = order.desc() if descending else order.asc()
    # 同值时再按 ID 排序，让数据不变时的分页顺序稳定。
    statement = (
        select(Hero).where(*filters).order_by(order, Hero.id).offset(offset).limit(limit)
    )
    return HeroPage(
        items=session.exec(statement).all(), total=total, offset=offset, limit=limit
    )


@router.get("/heroes/{hero_id}", response_model=HeroWithTeam)
def read_hero(hero_id: int, session: SessionDep):
    return get_hero_or_404(session, hero_id)


@router.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, data: HeroUpdate, session: SessionDep):
    hero = get_hero_or_404(session, hero_id)
    # exclude_unset=True 只取客户端实际传入的字段，避免默认 None 覆盖已有数据。
    changes = data.model_dump(exclude_unset=True)
    if changes.get("team_id") is not None:
        get_team_or_404(session, changes["team_id"])
    # 显式传 null 可以清空 age/team_id；空对象 {} 不修改数据，也不更新时间。
    if changes:
        hero.sqlmodel_update(changes)
        hero.updated_at = datetime.now(UTC)
    session.add(hero)
    commit(session)
    session.refresh(hero)
    return hero


@router.delete("/heroes/{hero_id}", status_code=204)
def delete_hero(hero_id: int, session: SessionDep):
    session.delete(get_hero_or_404(session, hero_id))
    commit(session)
    return Response(status_code=204)
