"""Case-based retrieval by symptom similarity.

This is intentionally not BM25: cases are short symptom signatures, so weighted
Jaccard + cause-type boost is easier to explain and gives a distinct retrieval
path for the AIOps project.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import get_settings
from app.schemas import CaseMatch, CaseRecord

_ASCII_RE = re.compile(r"[a-zA-Z0-9]+")
_CHINESE_RE = re.compile(r"[\u4e00-\u9fa5]+")


def _tokens(text: str) -> set[str]:
    text = text.lower()
    tokens = set(_ASCII_RE.findall(text))
    for segment in _CHINESE_RE.findall(text):
        if len(segment) == 1:
            tokens.add(segment)
        else:
            tokens.update(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens


def load_cases(path: Path | None = None) -> list[CaseRecord]:
    target = Path(path or get_settings().cases_path)
    cases: list[CaseRecord] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(CaseRecord.model_validate_json(line))
        except Exception:
            continue
    return cases


class CaseRetriever:
    def __init__(self, cases: list[CaseRecord] | None = None) -> None:
        self.cases = cases if cases is not None else load_cases()
        self._tokens = [
            _tokens(" ".join(case.symptoms + case.tags + [case.title])) for case in self.cases
        ]

    @property
    def count(self) -> int:
        return len(self.cases)

    def search(
        self,
        cause_type: str,
        symptom_text: str,
        root_ne_type: str = "",
        top_k: int = 3,
    ) -> list[CaseMatch]:
        query = _tokens(f"{cause_type} {symptom_text} {root_ne_type}")
        matches: list[CaseMatch] = []
        for index, case in enumerate(self.cases):
            case_tokens = self._tokens[index]
            union = query | case_tokens
            jaccard = len(query & case_tokens) / max(1, len(union))
            cause_bonus = 0.40 if case.cause_type == cause_type else 0.0
            ne_bonus = 0.10 if root_ne_type and case.root_ne_type == root_ne_type else 0.0
            score = min(1.0, 0.50 * jaccard + cause_bonus + ne_bonus)
            if score <= 0:
                continue
            matches.append(CaseMatch(case=case, score=round(score, 3)))
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[:top_k]


_retriever: CaseRetriever | None = None


def get_case_retriever() -> CaseRetriever:
    global _retriever
    if _retriever is None:
        _retriever = CaseRetriever()
    return _retriever
