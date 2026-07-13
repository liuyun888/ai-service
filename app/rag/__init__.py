# app/rag/__init__.py
"""RAG 包：统一从 app/lessons/ 课次文件 re-export，勿在本目录新增无编号文件。

跟课请直接打开 app/lessons/m03_0N_*.py，见 app/lessons/README.md。
"""

from app.lessons.m03_02_ingest import InMemoryIndex, build_index
from app.lessons.m03_02_splitters import Chunk, split_by_heading, split_fixed
from app.lessons.m03_04_ingest import ingest_paths
from app.lessons.m03_05_ingest_batch import chunks_from_markdown_dir
from app.lessons.m03_05_retriever import RetrievedHit, format_hit, retrieve

__all__ = [
    "Chunk",
    "InMemoryIndex",
    "RetrievedHit",
    "build_index",
    "chunks_from_markdown_dir",
    "format_hit",
    "ingest_paths",
    "retrieve",
    "split_by_heading",
    "split_fixed",
]
