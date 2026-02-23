from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from immcad_api.schemas import Citation


@dataclass(frozen=True)
class RetrievedDocument:
    source_id: str
    snippet: str
    title: str | None = None
    url: str | None = None
    pin: str | None = None


class ChatRetriever(Protocol):
    def retrieve(self, *, query: str, locale: str, limit: int = 4) -> list[RetrievedDocument]:
        ...


class NoopChatRetriever:
    def retrieve(self, *, query: str, locale: str, limit: int = 4) -> list[RetrievedDocument]:
        del query, locale, limit
        return []


def map_retrieved_documents_to_citations(documents: list[RetrievedDocument]) -> list[Citation]:
    citations: list[Citation] = []
    for index, document in enumerate(documents, start=1):
        source_id = document.source_id.strip() or f"retrieved-{index}"
        snippet = document.snippet.strip() or "Source excerpt unavailable."
        title = (document.title or "").strip() or source_id
        url = (document.url or "").strip() or "about:blank"
        pin = (document.pin or "").strip() or "n/a"
        citations.append(
            Citation(
                source_id=source_id,
                title=title,
                url=url,
                pin=pin,
                snippet=snippet,
            )
        )
    return citations


def build_grounding_context(documents: list[RetrievedDocument]) -> list[str]:
    return [document.snippet.strip() for document in documents if document.snippet.strip()]
