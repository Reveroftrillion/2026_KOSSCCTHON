"""LLM 분석을 시도하고 실패하면 기존 규칙 분석기로 전환한다."""

import os
from typing import Any, Mapping

if __package__:
    from .llm_parser import analyze_with_llm
    from .rule_parser import analyze_with_rules
    from .schemas import AnalyzedContent, ContentInput
else:
    from llm_parser import analyze_with_llm
    from rule_parser import analyze_with_rules
    from schemas import AnalyzedContent, ContentInput


def analyze_content(content: ContentInput | Mapping[str, Any]) -> AnalyzedContent:
    """기존 입력 계약을 유지하며 LLM 사용 불가 또는 오류 시 규칙으로 분석한다."""
    item = ContentInput.model_validate(content)
    if os.getenv("LLM_API_KEY", "").strip():
        try:
            result = analyze_with_llm(item)
        except Exception as exc:
            # 외부 SDK/응답 처리 경계에서만 예외를 잡는다. 키나 응답 원문은 출력하지 않는다.
            print(f"LLM unavailable. Using rule-based fallback. ({type(exc).__name__})")
        else:
            print("[Parser] llm")
            return result.model_copy(update={"user_id": item.user_id, "title": item.title})
    else:
        print("LLM unavailable. Using rule-based fallback.")
    print("[Parser] rule-based")
    result = analyze_with_rules(item)
    return result.model_copy(update={"user_id": item.user_id, "title": item.title})
