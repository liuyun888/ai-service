# app/tools/course_schedule.py
"""课次 06.05 · 按「粒度 / 幂等 / 错误可回灌 / 描述清晰」写好的课表 Tool。

本文件是「改好后」的范例：对照 lessons 里的坏 Tool，看描述和错误串怎么写。
只读、一事一工具，不在 Tool 里再调大模型。
"""

from __future__ import annotations

from langchain_core.tools import tool

# mock 课表：课程 ID → 简讯
MOCK_COURSES: dict[str, str] = {
    "CS101": "周一 09:00-11:00 / 教室 A101 / 容量 40",
    "CS201": "周三 14:00-16:00 / 教室 B203 / 容量 30",
    "MATH100": "周五 10:00-12:00 / 教室 C301 / 容量 50",
}


@tool
def get_course(course_id: str) -> str:
    """查询一门课的课表信息（只读）。

    何时用：用户给出课程编号（如 CS101）问「什么时候上 / 在哪个教室」。
    何时不用：选课下单、改课、冲突计算（应另做 write/conflict Tool）；闲聊。

    参数:
        course_id: 课程编码，大写字母+数字，例如 CS101

    返回:
        成功: 「course_id=..., schedule=...」
        失败: 「error=not_found; hint=…」或「error=empty; hint=…」（字符串，不抛异常）
    """
    key = (course_id or "").strip().upper()
    if not key:
        return "error=empty; hint=course_id 不能为空，示例 CS101"
    if key not in MOCK_COURSES:
        return (
            "error=not_found; hint=核对课程编号大小写与数字，"
            "当前目录含 CS101/CS201/MATH100"
        )
    return f"course_id={key}, schedule={MOCK_COURSES[key]}"
