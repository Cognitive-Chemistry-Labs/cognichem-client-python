from __future__ import annotations

import json

import httpx
import pytest
import respx

from cognichem_client import AsyncCogniChem, CogniChem
from cognichem_client.errors import (
    CogniChemError,
    ConflictError,
    PaymentRequiredError,
)

BASE = "https://api.test.cognichem.com"
API = f"{BASE}/api/v1"


def _lookup(source: str) -> dict[str, object]:
    return {
        "results": [
            {
                "source": source,
                "operation": "entry",
                "query": "q",
                "status": "found",
                "license": "CC BY 4.0",
                "data": {"x": 1},
            }
        ],
        "attribution": f"Data from {source}",
    }


@respx.mock
def test_lookups_send_expected_bodies() -> None:
    pubchem = respx.post(f"{API}/lookup/pubchem").mock(
        return_value=httpx.Response(
            200,
            json={
                "compounds": [
                    {
                        "name": "aspirin",
                        "status": "found",
                        "cid": 2244,
                        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
                        "license": "Public domain",
                    }
                ],
                "attribution": "Data from PubChem",
            },
        )
    )
    chembl = respx.post(f"{API}/lookup/chembl").mock(
        return_value=httpx.Response(200, json=_lookup("ChEMBL"))
    )
    targets = respx.post(f"{API}/lookup/targets").mock(
        return_value=httpx.Response(200, json=_lookup("Open Targets"))
    )
    uniprot = respx.post(f"{API}/lookup/uniprot").mock(
        return_value=httpx.Response(200, json=_lookup("UniProt"))
    )
    pdb = respx.post(f"{API}/lookup/pdb").mock(
        return_value=httpx.Response(200, json=_lookup("RCSB PDB"))
    )
    props = respx.post(f"{API}/lookup/properties").mock(
        return_value=httpx.Response(200, json=_lookup("PubChem"))
    )
    client = CogniChem(api_key="k", base_url=BASE)

    assert client.lookup.pubchem("aspirin").compounds[0].cid == 2244
    assert json.loads(pubchem.calls.last.request.content) == {"names": ["aspirin"]}

    result = client.lookup.chembl("similarity", ["CCO"], limit=5, threshold=80)
    assert result.results[0].source == "ChEMBL"
    assert json.loads(chembl.calls.last.request.content) == {
        "operation": "similarity",
        "queries": ["CCO"],
        "limit": 5,
        "threshold": 80,
    }

    client.lookup.targets("target_diseases", "EGFR")
    assert json.loads(targets.calls.last.request.content) == {
        "operation": "target_diseases",
        "queries": ["EGFR"],
    }
    client.lookup.uniprot("search", ["EGFR"], organism="9606")
    assert json.loads(uniprot.calls.last.request.content)["organism"] == "9606"
    client.lookup.pdb("entry", ["1M17"])
    assert json.loads(pdb.calls.last.request.content)["queries"] == ["1M17"]
    client.lookup.properties(["methanol"], properties=["boiling_point"], limit=2)
    assert json.loads(props.calls.last.request.content) == {
        "operation": "experimental",
        "queries": ["methanol"],
        "properties": ["boiling_point"],
        "limit": 2,
    }


@respx.mock
def test_wallet_and_reference() -> None:
    respx.get(f"{API}/wallet").mock(
        return_value=httpx.Response(200, json={"balance": 12.5, "active_reserved": 1})
    )
    paper = {"id": "paper:propka", "title": "PROPKA3", "paper_set": "method"}
    search = respx.get(f"{API}/reference/papers").mock(
        return_value=httpx.Response(
            200, json={"query": "pKa", "mode": "hybrid", "papers": [paper]}
        )
    )
    respx.get(f"{API}/reference/papers/paper:propka").mock(
        return_value=httpx.Response(
            200,
            json={
                "paper": paper,
                "edges": [
                    {
                        "src_paper_id": "paper:propka",
                        "dst_kind": "product_node",
                        "dst_id": "job_type:protein-prepare",
                        "kind": "method_of",
                    }
                ],
                "cited_by_count": 3,
                "provenance": {"entity_ids": ["paper:propka"]},
            },
        )
    )
    hood = respx.get(f"{API}/reference/neighborhood").mock(
        return_value=httpx.Response(
            200,
            json={"center": "job_type:protein-prepare", "papers": [paper]},
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    assert client.wallet.balance().balance == 12.5

    hits = client.reference.search("pKa", paper_set="method", limit=5)
    assert hits.mode == "hybrid" and hits.papers[0].id == "paper:propka"
    assert search.calls.last.request.url.params["paper_set"] == "method"
    detail = client.reference.get("paper:propka")
    assert detail.edges[0].kind == "method_of" and detail.cited_by_count == 3
    client.reference.neighborhood(node_id="job_type:protein-prepare")
    params = hood.calls.last.request.url.params
    assert params["node_id"] == "job_type:protein-prepare"
    assert "paper_id" not in params


def _event(event_id: int) -> dict[str, object]:
    return {
        "event_id": event_id,
        "cursor": f"c{event_id}",
        "kind": "job",
        "subject_id": f"job-{event_id}",
        "status": "completed",
        "occurred_at": "2026-09-27T12:00:00Z",
    }


@respx.mock
def test_events_list_and_listen_dedupes() -> None:
    pages = iter(
        [
            {"events": [_event(1), _event(2)], "next_cursor": "c2"},
            {"events": [_event(2), _event(3)], "next_cursor": "c3"},
        ]
    )
    route = respx.get(f"{API}/events").mock(
        side_effect=lambda request: httpx.Response(200, json=next(pages))
    )
    client = CogniChem(api_key="k", base_url=BASE)
    received = []
    for event in client.events.listen(kind="job", wait=1):
        received.append(event.event_id)
        if len(received) == 3:
            break
    assert received == [1, 2, 3]
    first, second = (call.request.url.params for call in route.calls)
    assert "after" not in first and first["kind"] == "job" and first["wait"] == "1"
    assert second["after"] == "c2"


def _sse(*frames: tuple[str, dict[str, object]]) -> bytes:
    return "".join(
        f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in frames
    ).encode()


TURN = _sse(
    ("hold", {"turn_id": "t-1", "hold_usd": 0.05, "reasoning_effort": "low"}),
    ("token", {"delta": "Use "}),
    ("tool_call", {"name": "kg_product_how_to_run", "id": "call-1"}),
    ("token", {"delta": "autodockvina."}),
    ("proposal", {"id": "prop-1", "estimate_usd": 0.12}),
    (
        "done",
        {
            "turn_id": "t-1",
            "billed_usd": 0.01,
            "held_usd": 0.05,
            "citations": [{"url": "https://app.cognichem.com/tool/autodockvina"}],
        },
    ),
)


@respx.mock
def test_chat_send_collects_stream_with_bearer() -> None:
    route = respx.post(f"{API}/chat/sessions/s-1/turns").mock(
        return_value=httpx.Response(
            200, content=TURN, headers={"Content-Type": "text/event-stream"}
        )
    )
    client = CogniChem(api_key="k", access_token="jwt", base_url=BASE)
    result = client.chat.send("s-1", "How do I dock?", reasoning_effort="medium")
    assert result.turn_id == "t-1"
    assert result.content == "Use autodockvina."
    assert result.billed_usd == 0.01
    assert result.tool_calls[0]["name"] == "kg_product_how_to_run"
    assert result.proposals[0]["id"] == "prop-1"
    assert result.citations[0]["url"].endswith("autodockvina")
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer jwt"
    assert "X-Api-Key" not in request.headers
    assert json.loads(request.content) == {
        "message": "How do I dock?",
        "model_id": "cognichem-assistant",
        "artifact_ids": [],
        "reasoning_effort": "medium",
    }


@respx.mock
def test_chat_stream_errors() -> None:
    respx.post(f"{API}/chat/sessions/s-1/turns").mock(
        return_value=httpx.Response(
            402,
            json={
                "type": "/api/v1/problems/insufficient-wallet",
                "status": 402,
                "detail": "Top up",
            },
        )
    )
    respx.post(f"{API}/chat/sessions/s-2/turns").mock(
        return_value=httpx.Response(
            409,
            json={
                "type": "/api/v1/problems/session-spend-cap",
                "status": 409,
                "detail": "Cap reached",
                "cap_usd": 1.0,
                "step_usd": 1.0,
            },
        )
    )
    respx.post(f"{API}/chat/sessions/s-3/turns").mock(
        return_value=httpx.Response(
            200, content=_sse(("error", {"detail": "Assistant turn failed"}))
        )
    )
    client = CogniChem(access_token="jwt", base_url=BASE)
    with pytest.raises(PaymentRequiredError) as paid:
        client.chat.send("s-1", "hi")
    assert paid.value.code == "insufficient-wallet"
    with pytest.raises(ConflictError) as cap:
        list(client.chat.stream("s-2", "hi"))
    assert cap.value.code == "session-spend-cap"
    assert cap.value.body["cap_usd"] == 1.0
    with pytest.raises(CogniChemError) as failed:
        client.chat.send("s-3", "hi")
    assert failed.value.code == "assistant-turn-error"


@respx.mock
def test_chat_sessions_spend_cap_and_proposals() -> None:
    session = {
        "id": "s-1",
        "title": "Docking",
        "created_at": "2026-09-27T00:00:00Z",
        "updated_at": "2026-09-27T00:00:00Z",
    }
    proposal = {
        "id": "p-1",
        "session_id": "s-1",
        "kind": "job",
        "status": "pending",
        "estimate_usd": 0.12,
        "expires_at": "2026-09-28T00:00:00Z",
        "created_at": "2026-09-27T00:00:00Z",
    }
    respx.post(f"{API}/chat/sessions").mock(
        return_value=httpx.Response(201, json=session)
    )
    respx.get(f"{API}/chat/sessions").mock(
        return_value=httpx.Response(200, json={"items": [session]})
    )
    patch = respx.patch(f"{API}/chat/sessions/s-1").mock(
        return_value=httpx.Response(
            200, json={**session, "allow_structure_search": True}
        )
    )
    respx.delete(f"{API}/chat/sessions/s-1").mock(return_value=httpx.Response(204))
    respx.get(f"{API}/chat/sessions/s-1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "m-1",
                        "session_id": "s-1",
                        "role": "user",
                        "content": "hi",
                        "created_at": "2026-09-27T00:00:00Z",
                    }
                ]
            },
        )
    )
    respx.post(f"{API}/chat/sessions/s-1/estimate").mock(
        return_value=httpx.Response(
            200,
            json={
                "model_id": "cognichem-assistant",
                "reasoning_effort": "low",
                "tier": 1,
                "prompt_tokens": 100,
                "max_completion_tokens": 2000,
                "hold_usd": 0.03,
            },
        )
    )
    respx.get(f"{API}/chat/sessions/s-1/spend-cap").mock(
        return_value=httpx.Response(
            200,
            json={"spent_usd": 1, "held_usd": 0, "cap_usd": 1, "step_usd": 1},
        )
    )
    cont = respx.post(f"{API}/chat/sessions/s-1/spend-cap/continue").mock(
        return_value=httpx.Response(
            200,
            json={
                "spent_usd": 1,
                "held_usd": 0,
                "cap_usd": 2,
                "step_usd": 1,
                "raised": True,
            },
        )
    )
    respx.post(f"{API}/chat/sessions/s-1/turns/t-1/stop").mock(
        return_value=httpx.Response(200, json={"status": "stopping", "turn_id": "t-1"})
    )
    respx.get(f"{API}/chat/sessions/s-1/proposals").mock(
        return_value=httpx.Response(200, json={"items": [proposal]})
    )
    get_prop = respx.get(f"{API}/chat/sessions/s-1/proposals/p-1").mock(
        return_value=httpx.Response(200, json=proposal)
    )
    approve = respx.post(f"{API}/chat/sessions/s-1/proposals/p-1/approve").mock(
        return_value=httpx.Response(
            200, json={**proposal, "status": "submitted", "job_id": "job-9"}
        )
    )
    respx.post(f"{API}/chat/sessions/s-1/proposals/p-1/reject").mock(
        return_value=httpx.Response(200, json={**proposal, "status": "rejected"})
    )
    client = CogniChem(access_token="jwt", base_url=BASE)
    chat = client.chat

    assert chat.sessions.create("Docking").id == "s-1"
    assert chat.sessions.list().items[0].title == "Docking"
    assert chat.sessions.update("s-1", allow_structure_search=True)
    assert json.loads(patch.calls.last.request.content) == {
        "allow_structure_search": True
    }
    assert chat.sessions.messages("s-1").items[0].role == "user"
    assert chat.sessions.delete("s-1") is None
    assert chat.estimate("s-1", "hi").hold_usd == 0.03
    assert chat.spend_cap("s-1").cap_usd == 1
    assert chat.continue_spend_cap("s-1", 1.0).raised is True
    assert json.loads(cont.calls.last.request.content)["current_cap_usd"] == 1.0
    assert chat.stop("s-1", "t-1")["status"] == "stopping"
    assert chat.proposals.list("s-1").items[0].id == "p-1"
    chat.proposals.get("s-1", "p-1", include_spec=True)
    assert get_prop.calls.last.request.url.params["include_spec"] == "true"
    approved = chat.proposals.approve("s-1", "p-1", 0.12)
    assert approved.job_id == "job-9"
    assert approve.calls.last.request.headers["Idempotency-Key"]
    assert json.loads(approve.calls.last.request.content) == {
        "accepted_estimate_usd": 0.12,
        "max_run_cost_usd": None,
    }
    assert chat.proposals.reject("s-1", "p-1").status == "rejected"


@respx.mock
async def test_async_chat_stream_and_events() -> None:
    respx.post(f"{API}/chat/sessions/s-1/turns").mock(
        return_value=httpx.Response(200, content=TURN)
    )
    respx.get(f"{API}/events").mock(
        return_value=httpx.Response(
            200, json={"events": [_event(7)], "next_cursor": "c7"}
        )
    )
    async with AsyncCogniChem(access_token="jwt", base_url=BASE) as client:
        names = [event.event async for event in client.chat.stream("s-1", "hi")]
        result = await client.chat.send("s-1", "hi")
        page = await client.events.list(after="c6")
    assert names == ["hold", "token", "tool_call", "token", "proposal", "done"]
    assert result.content == "Use autodockvina."
    assert page.events[0].event_id == 7
