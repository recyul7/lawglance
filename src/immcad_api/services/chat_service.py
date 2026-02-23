from __future__ import annotations

from immcad_api.policy.compliance import (
    DISCLAIMER_TEXT,
    POLICY_REFUSAL_TEXT,
    enforce_citation_requirement,
    should_refuse_for_policy,
)
from immcad_api.errors import ProviderApiError
from immcad_api.providers import ProviderError, ProviderRouter
from immcad_api.retrieval import (
    ChatRetriever,
    NoopChatRetriever,
    build_grounding_context,
    map_retrieved_documents_to_citations,
)
from immcad_api.schemas import ChatRequest, ChatResponse, Citation, FallbackUsed


class ChatService:
    def __init__(
        self,
        provider_router: ProviderRouter,
        *,
        retriever: ChatRetriever | None = None,
        enable_grounding: bool = True,
        grounding_result_limit: int = 4,
        allow_scaffold_synthetic_citations: bool = True,
    ) -> None:
        self.provider_router = provider_router
        self.retriever = retriever or NoopChatRetriever()
        self.enable_grounding = enable_grounding
        self.grounding_result_limit = grounding_result_limit
        self.allow_scaffold_synthetic_citations = allow_scaffold_synthetic_citations

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        if should_refuse_for_policy(request.message):
            return ChatResponse(
                answer=POLICY_REFUSAL_TEXT,
                citations=[],
                confidence="low",
                disclaimer=DISCLAIMER_TEXT,
                fallback_used=FallbackUsed(
                    used=False,
                    provider=None,
                    reason="policy_block",
                ),
            )

        citations = self._default_citations(request.message)
        grounding_context: list[str] | None = None
        if self._requires_grounding(request):
            retrieved = self.retriever.retrieve(
                query=request.message,
                locale=request.locale,
                limit=self.grounding_result_limit,
            )
            if retrieved:
                citations = map_retrieved_documents_to_citations(retrieved)
                grounding_context = build_grounding_context(retrieved)

        try:
            routed = self.provider_router.generate(
                message=request.message,
                citations=citations,
                locale=request.locale,
                grounding_context=grounding_context,
            )
        except ProviderError as exc:
            raise ProviderApiError(exc.message) from exc

        answer, validated_citations, confidence = enforce_citation_requirement(
            routed.result.answer,
            routed.result.citations,
        )

        fallback_provider = routed.result.provider if routed.fallback_used else None
        fallback_reason = routed.fallback_reason if routed.fallback_used else None

        return ChatResponse(
            answer=answer,
            citations=validated_citations,
            confidence=confidence,
            disclaimer=DISCLAIMER_TEXT,
            fallback_used=FallbackUsed(
                used=routed.fallback_used,
                provider=fallback_provider,
                reason=fallback_reason,
            ),
        )

    def _requires_grounding(self, request: ChatRequest) -> bool:
        if not self.enable_grounding:
            return False
        return request.mode.strip().lower() in {"standard", "grounded", "factual"}

    def _default_citations(self, message: str) -> list[Citation]:
        del message
        if not self.allow_scaffold_synthetic_citations:
            return []

        snippet = "Reference to IRPA; user context omitted for privacy."
        return [
            Citation(
                source_id="IRPA",
                snippet=snippet,
                title="Immigration and Refugee Protection Act",
                url="https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
                pin="s. 11",
            )
        ]
