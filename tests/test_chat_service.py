from __future__ import annotations

from dataclasses import dataclass, field

from immcad_api.providers import ProviderResult, RoutingResult
from immcad_api.retrieval import RetrievedDocument
from immcad_api.schemas import ChatRequest, Citation
from immcad_api.services.chat_service import ChatService


@dataclass
class _RecordingRetriever:
    documents: list[RetrievedDocument]
    call_log: list[str]

    def retrieve(self, *, query: str, locale: str, limit: int = 4) -> list[RetrievedDocument]:
        del query, locale, limit
        self.call_log.append("retrieve")
        return self.documents


@dataclass
class _RecordingRouter:
    call_log: list[str]
    received_citations: list[Citation] = field(default_factory=list)
    received_context: list[str] | None = None

    def generate(
        self,
        *,
        message: str,
        citations: list[Citation],
        locale: str,
        grounding_context: list[str] | None = None,
    ) -> RoutingResult:
        del message, locale
        self.call_log.append("generate")
        self.received_citations = citations
        self.received_context = grounding_context
        return RoutingResult(
            result=ProviderResult(
                provider="scaffold",
                answer="Grounded answer",
                citations=citations,
                confidence="medium",
            ),
            fallback_used=False,
            fallback_reason=None,
        )


def test_chat_service_grounds_with_retrieved_documents() -> None:
    call_log: list[str] = []
    retriever = _RecordingRetriever(
        documents=[
            RetrievedDocument(
                source_id="IRPA-11",
                snippet="IRPA section 11 describes visa requirements.",
                title="Immigration and Refugee Protection Act",
                url="https://laws-lois.justice.gc.ca/eng/acts/I-2.5/",
                pin="s. 11",
            )
        ],
        call_log=call_log,
    )
    router = _RecordingRouter(call_log=call_log)
    service = ChatService(
        provider_router=router,  # type: ignore[arg-type]
        retriever=retriever,
        enable_grounding=True,
        allow_scaffold_synthetic_citations=False,
    )

    response = service.handle_chat(
        ChatRequest(
            session_id="session-123456",
            message="What does IRPA section 11 require?",
            locale="en-CA",
            mode="standard",
        )
    )

    assert call_log == ["retrieve", "generate"]
    assert router.received_context == ["IRPA section 11 describes visa requirements."]
    assert response.citations[0].source_id == "IRPA-11"
    assert response.citations[0].title == "Immigration and Refugee Protection Act"


def test_chat_service_uses_default_citations_when_retriever_is_empty() -> None:
    call_log: list[str] = []
    retriever = _RecordingRetriever(documents=[], call_log=call_log)
    router = _RecordingRouter(call_log=call_log)
    service = ChatService(
        provider_router=router,  # type: ignore[arg-type]
        retriever=retriever,
        enable_grounding=True,
        allow_scaffold_synthetic_citations=True,
    )

    response = service.handle_chat(
        ChatRequest(
            session_id="session-123456",
            message="Summarize PR pathways in Canada.",
            locale="en-CA",
            mode="standard",
        )
    )

    assert call_log == ["retrieve", "generate"]
    assert router.received_context is None
    assert router.received_citations[0].source_id == "IRPA"
    assert response.citations[0].source_id == "IRPA"


def test_chat_service_skips_grounding_for_non_factual_modes() -> None:
    call_log: list[str] = []
    retriever = _RecordingRetriever(documents=[], call_log=call_log)
    router = _RecordingRouter(call_log=call_log)
    service = ChatService(
        provider_router=router,  # type: ignore[arg-type]
        retriever=retriever,
        enable_grounding=True,
    )

    service.handle_chat(
        ChatRequest(
            session_id="session-123456",
            message="Hello there.",
            locale="en-CA",
            mode="casual",
        )
    )

    assert call_log == ["generate"]
