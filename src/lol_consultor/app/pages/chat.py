"""Página 'Asistente IA': chat en lenguaje natural respaldado por Ollama + tools."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html, no_update

from lol_consultor.assistant import LoLAssistant

_WELCOME = (
    "Pregúntame sobre League of Legends: campeones, habilidades, counters, "
    "ítems, runas o cambios de parche. Ejemplos: '¿quién counterea a Yasuo?', "
    "'¿qué hace la R de Ahri?', '¿qué ítems dan robo de vida?'"
)


def _bubble(role: str, text: str) -> html.Div:
    if role == "user":
        classes = "bg-primary text-white ms-auto"
    else:
        classes = "bg-secondary bg-opacity-25"
    return html.Div(
        text,
        className=f"rounded p-2 px-3 my-1 {classes}",
        style={"maxWidth": "80%", "whiteSpace": "pre-wrap", "width": "fit-content"},
    )


def layout(assistant: LoLAssistant) -> html.Div:
    status = assistant.status_message()
    banner = (
        dbc.Alert(status, color="warning", class_name="small")
        if status
        else dbc.Alert(
            f"Asistente local activo (modelo {assistant.model} vía Ollama, sin costo).",
            color="info",
            class_name="small",
        )
    )
    return html.Div(
        [
            banner,
            html.P(_WELCOME, className="small text-muted"),
            dcc.Store(id="chat-history", data=[]),
            html.Div(
                id="chat-messages",
                className="d-flex flex-column mb-3",
                style={"minHeight": "200px", "maxHeight": "55vh", "overflowY": "auto"},
            ),
            dcc.Loading(html.Div(id="chat-pending"), type="dot"),
            dbc.InputGroup(
                [
                    dbc.Input(
                        id="chat-input",
                        placeholder="Escribe tu pregunta...",
                        type="text",
                        debounce=True,
                    ),
                    dbc.Button("Enviar", id="chat-send", color="primary"),
                ]
            ),
        ]
    )


def register_callbacks(app: Dash, assistant: LoLAssistant) -> None:
    @app.callback(
        Output("chat-messages", "children"),
        Output("chat-history", "data"),
        Output("chat-input", "value"),
        Output("chat-pending", "children"),
        Input("chat-send", "n_clicks"),
        Input("chat-input", "n_submit"),
        State("chat-input", "value"),
        State("chat-history", "data"),
        prevent_initial_call=True,
    )
    def _send(_clicks: int | None, _submit: int | None, question: str | None, history: list):
        question = (question or "").strip()
        if not question:
            return no_update, no_update, no_update, ""

        history = history or []
        _answer, new_history = assistant.ask(history, question)
        bubbles = [_bubble(turn["role"], turn["content"]) for turn in new_history]
        return bubbles, new_history, "", ""
