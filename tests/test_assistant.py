from __future__ import annotations

from types import SimpleNamespace

from lol_consultor.assistant import LoLAssistant


def _tool_call(name: str, arguments: dict):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


def _response(content: str = "", tool_calls: list | None = None):
    return SimpleNamespace(
        message=SimpleNamespace(content=content, tool_calls=tool_calls or None)
    )


class _FakeOllamaClient:
    """Devuelve respuestas guionadas en orden; registra los mensajes recibidos."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls: list[list] = []

    def chat(self, model, messages, tools, think):
        self.calls.append(list(messages))
        return self._responses.pop(0)

    def list(self):
        return SimpleNamespace(models=[SimpleNamespace(model="qwen3:8b")])


def _assistant(stub_service, responses) -> tuple[LoLAssistant, _FakeOllamaClient]:
    client = _FakeOllamaClient(responses)
    return LoLAssistant(stub_service, model="qwen3:8b", client=client), client


def test_ask_direct_answer_without_tools(stub_service):
    assistant, client = _assistant(stub_service, [_response("Ahri es una maga.")])

    answer, history = assistant.ask([], "¿Quién es Ahri?")

    assert answer == "Ahri es una maga."
    assert [t["role"] for t in history] == ["user", "assistant"]
    # el system prompt va primero en los mensajes enviados al modelo
    assert client.calls[0][0]["role"] == "system"


def test_ask_executes_tool_and_returns_final_answer(stub_service):
    responses = [
        _response(tool_calls=[_tool_call("detalle_campeon", {"nombre": "Ahri"})]),
        _response("La pasiva de Ahri es Robo de esencia."),
    ]
    assistant, client = _assistant(stub_service, responses)

    answer, _history = assistant.ask([], "¿Qué hace la pasiva de Ahri?")

    assert "Robo de esencia" in answer
    # la segunda llamada incluye el resultado de la tool
    tool_messages = [m for m in client.calls[1] if isinstance(m, dict) and m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert "Robo de esencia" in tool_messages[0]["content"]


def test_ask_degrades_gracefully_when_ollama_fails(stub_service):
    class _BrokenClient:
        def chat(self, *args, **kwargs):
            raise ConnectionError("sin conexión")

    assistant = LoLAssistant(stub_service, client=_BrokenClient())

    answer, history = assistant.ask([], "hola")

    assert "Ollama" in answer
    assert len(history) == 2  # la conversación se conserva aunque falle


def test_dispatch_unknown_tool(stub_service):
    assistant, _ = _assistant(stub_service, [])
    assert "desconocida" in assistant._dispatch("tool_falsa", {})


def test_find_champion_fuzzy_match(stub_service):
    assistant, _ = _assistant(stub_service, [])
    assert assistant._find_champion("ahri")["id"] == "Ahri"
    assert assistant._find_champion("AHRI")["id"] == "Ahri"
    assert assistant._find_champion("noexiste") is None


def test_meta_campeon_reports_counters(stub_service):
    assistant, _ = _assistant(stub_service, [])

    result = assistant._meta_campeon("Ahri")

    assert "winrate 51.0%" in result
    assert "Counter" in result


def test_status_message_when_model_missing(stub_service):
    class _EmptyClient:
        def list(self):
            return SimpleNamespace(models=[])

    assistant = LoLAssistant(stub_service, model="qwen3:8b", client=_EmptyClient())

    status = assistant.status_message()

    assert status is not None and "ollama pull" in status


def test_dispatch_routes_to_ability_pattern_search(stub_service):
    assistant, _ = _assistant(stub_service, [])

    result = assistant._dispatch("buscar_habilidades_por_patron", {"patron": "inflige daño"})

    assert "Ahri" in result
    assert "Orbe del engaño" in result


def test_ask_uses_ability_search_tool_end_to_end(stub_service):
    responses = [
        _response(tool_calls=[_tool_call("buscar_habilidades_por_patron", {"patron": "daño"})]),
        _response("Ahri tiene una habilidad que inflige daño: Orbe del engaño."),
    ]
    assistant, client = _assistant(stub_service, responses)

    answer, _history = assistant.ask([], "¿Qué campeones tienen habilidades que hacen daño?")

    assert "Ahri" in answer
    tool_messages = [m for m in client.calls[1] if isinstance(m, dict) and m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert "Ahri" in tool_messages[0]["content"]
