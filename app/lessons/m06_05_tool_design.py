# app/lessons/m06_05_tool_design.py
"""课次 06.05 · Tool 设计原则：粒度、幂等、错误可回灌、描述清晰。

用「坏示例 vs 好示例」对照实验：
1. 打印 schema，用评审清单打分
2. 坏 Tool 抛异常 vs 好 Tool 返回可读错误串（进程不崩）
3. 超级 Tool 难控 vs 一事一工具 + Loop 组合
4. 把评审结果写入笔记（至少改好 / 新增 1 个好 Tool）

生产库存 Tool 的 ``not_found`` 契约保持不动，避免砸了前几课断言；
本课新增 ``get_course``，并在此文件里放「坏版本」作反例。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.tools import BaseTool, tool

from app.tools.course_schedule import get_course
from app.tools.inventory import get_inventory, get_shipment
from app.tools.knowledge import search_knowledge

# ---------------------------------------------------------------------------
# 评审清单（打勾项；满分 = 条目数）
# ---------------------------------------------------------------------------

CHECKLIST: list[tuple[str, str]] = [
    ("name_verb", "名字是动词短语且唯一（get_x / search_y）"),
    ("params_few", "参数少而必要，类型明确（不要一坨 free JSON）"),
    ("desc_when", "描述写清何时用 / 何时不用"),
    ("return_samples", "有成功/失败样例返回格式"),
    ("error_string", "失败返回可读字符串，不抛栈打崩进程"),
    ("readonly_split", "只读与有副作用写入分开（或声明禁止写）"),
    ("no_nested_llm", "Tool 内不再调大模型（保持确定性 I/O）"),
    ("no_secret_param", "不让模型传密钥；凭证由服务端注入"),
]


@dataclass
class ReviewResult:
    """一次 Tool 评审结果。"""

    tool_name: str
    scores: dict[str, bool]
    notes: list[str]

    @property
    def passed(self) -> int:
        return sum(1 for v in self.scores.values() if v)

    @property
    def total(self) -> int:
        return len(self.scores)

    def as_row(self) -> str:
        return f"{self.tool_name}: {self.passed}/{self.total}"


def describe_schema(t: BaseTool) -> dict[str, Any]:
    """打印模型「看得见」的说明书摘要。"""
    schema = {}
    try:
        schema = t.args_schema.model_json_schema() if t.args_schema else {}
    except Exception:  # noqa: BLE001
        schema = {"raw": str(t.args_schema)}
    return {
        "name": t.name,
        "description": (t.description or "")[:500],
        "args_schema": schema,
    }


# ---------------------------------------------------------------------------
# 坏示例（仅教学：刻意写烂，不要接到生产路由）
# ---------------------------------------------------------------------------


@tool
def manage(data: str) -> str:
    """处理商品相关。"""
    # 坏：描述像谜语；参数是自由文本；内部还假装「又查又改又发邮件」
    text = (data or "").lower()
    if "炸" in text or "raise" in text:
        # 坏：把异常抛给外层 → 循环可能直接崩
        raise RuntimeError("仓库超时 stacktrace=...")
    if "库存" in data or "stock" in text:
        return "大概还有一些吧"  # 坏：非结构化、无 sku、可瞎编
    if "退" in data:
        return "已帮你退款成功"  # 坏：假写入副作用，无 HITL
    return "ok"


@tool
def do_everything(action: str, payload: str = "") -> str:
    """一个工具干所有事：查库存、查课表、退款、发邮件都行。"""
    # 坏：超级 Tool，Loop 无法细粒度控权；失败形态混乱
    a = (action or "").strip().lower()
    if a in {"raise", "boom"}:
        raise ValueError("内部空指针")
    if a == "inventory":
        return get_inventory.invoke({"sku": payload or "EARPHONE-PRO-BK"})
    if a == "course":
        return get_course.invoke({"course_id": payload or "CS101"})
    if a == "refund":
        return "refunded=true; money=-1"  # 坏：写入伪装成功
    return f"unknown action={action!r}"


def review_tool(
    t: BaseTool,
    *,
    force_scores: dict[str, bool] | None = None,
) -> ReviewResult:
    """按清单给 Tool 打分（教学用启发式 + 可手工覆盖）。"""
    name = t.name or ""
    desc = (t.description or "").strip()
    desc_l = desc.lower()

    # 参数个数
    n_params = 0
    try:
        props = (t.args_schema.model_json_schema() if t.args_schema else {}).get(
            "properties"
        ) or {}
        n_params = len(props)
    except Exception:  # noqa: BLE001
        n_params = 99

    scores: dict[str, bool] = {
        "name_verb": name.startswith(("get_", "search_", "list_", "check_"))
        and "everything" not in name
        and name != "manage",
        "params_few": 1 <= n_params <= 3,
        "desc_when": ("何时用" in desc or "when" in desc_l) and ("何时不用" in desc or "不用" in desc),
        "return_samples": "返回" in desc or "成功" in desc or "error=" in desc,
        "error_string": True,  # 默认信任；抛异常的用例在 invoke 实验里另验
        "readonly_split": "只读" in desc or "不得" in desc or "禁止" in desc or "write" not in name,
        "no_nested_llm": "大模型" not in desc and "llm" not in desc_l,
        "no_secret_param": "api_key" not in name and "secret" not in desc_l and "密钥" not in desc,
    }
    if force_scores:
        scores.update(force_scores)

    notes: list[str] = []
    if not scores["name_verb"]:
        notes.append("名字不像单一动词短语，或过于含糊（manage/do_everything）")
    if not scores["params_few"]:
        notes.append(f"参数个数可疑：{n_params}（宜少而明确）")
    if not scores["desc_when"]:
        notes.append("描述缺少「何时用 / 何时不用」")
    if not scores["return_samples"]:
        notes.append("描述未说明成功/失败返回格式")

    return ReviewResult(tool_name=name, scores=scores, notes=notes)


def safe_invoke(fn: Callable[..., Any], args: dict[str, Any]) -> dict[str, Any]:
    """调用 Tool：捕获异常，模拟「错误应回灌字符串」的工程要求。"""
    try:
        out = fn.invoke(args)
        return {"ok": True, "observation": str(out), "raised": None}
    except Exception as exc:  # noqa: BLE001 — 正是坏例子要演示的
        return {
            "ok": False,
            "observation": None,
            "raised": f"{type(exc).__name__}: {exc}",
        }


def demo_error_path_contrast() -> dict[str, Any]:
    """坏：抛栈；好：error=...; hint=... 字符串。"""
    bad = safe_invoke(manage, {"data": "raise 炸一下"})
    good = safe_invoke(get_course, {"course_id": "NO-SUCH"})
    empty = safe_invoke(get_course, {"course_id": "  "})
    return {"bad_manage": bad, "good_not_found": good, "good_empty": empty}


def demo_granularity_contrast() -> dict[str, Any]:
    """同一用户目标：超级 Tool vs 两个细粒度 Tool。"""
    user_goal = "查 EARPHONE-PRO-BK 库存，并查 CS101 什么时候上课"
    mega = safe_invoke(
        do_everything, {"action": "inventory", "payload": "EARPHONE-PRO-BK"}
    )
    # 超级 Tool 一次只能塞一个 action——要课表还得再调且仍混在同一工具里
    mega2 = safe_invoke(do_everything, {"action": "course", "payload": "CS101"})
    fine1 = safe_invoke(get_inventory, {"sku": "EARPHONE-PRO-BK"})
    fine2 = safe_invoke(get_course, {"course_id": "CS101"})
    return {
        "user_goal": user_goal,
        "mega_calls": [mega, mega2],
        "fine_calls": [fine1, fine2],
        "lesson": "组合由 Loop 做；不要把工作流藏进 do_everything",
    }


def demo_side_effect_warning() -> dict[str, Any]:
    """写入副作用不该伪装成普通 Tool 成功。"""
    refund = safe_invoke(do_everything, {"action": "refund", "payload": "order-1"})
    return {
        "bad_refund_observation": refund,
        "lesson": "有副作用 → 默认禁止或 HITL（06.06），勿与只读查询混在同一超级 Tool",
    }


def review_suite() -> list[ReviewResult]:
    """对坏/好/现网 Tool 批量评审。"""
    items: list[tuple[BaseTool, dict[str, bool] | None]] = [
        (
            manage,
            {
                "name_verb": False,
                "params_few": True,
                "desc_when": False,
                "return_samples": False,
                "error_string": False,  # 会抛异常
                "readonly_split": False,
                "no_nested_llm": True,
                "no_secret_param": True,
            },
        ),
        (
            do_everything,
            {
                "name_verb": False,
                "params_few": True,
                "desc_when": False,
                "return_samples": False,
                "error_string": False,
                "readonly_split": False,
                "no_nested_llm": True,
                "no_secret_param": True,
            },
        ),
        (get_inventory, None),
        (get_shipment, None),
        (search_knowledge, None),
        (get_course, None),
    ]
    return [review_tool(t, force_scores=force) for t, force in items]


def improve_inventory_error_demo(sku: str = "EARPHONE") -> dict[str, Any]:
    """对照：现网 not_found vs 带 hint 的「改进返回」示意（不改坏旧契约）。"""
    old = get_inventory.invoke({"sku": sku})
    # 改进形态——给模型可行动的 hint（本课推荐格式）
    improved = (
        f"error=not_found; hint=检查 sku 是否含颜色后缀如 -BK/-WH；"
        f"你传入的是 {sku!r}，目录示例 EARPHONE-PRO-BK"
    )
    return {
        "sku": sku,
        "before": old,
        "after_recommended": improved,
        "note": "生产 get_inventory 仍返回精确 not_found 以兼容前几课；新 Tool 请用 error=/hint= 格式",
    }
