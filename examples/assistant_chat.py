"""Ask the CogniChem Assistant a question and review any run proposals.

Chat is JWT-only: set ``COGNICHEM_ACCESS_TOKEN`` (or sign in on a client with
``client.auth.login_email(email, password)``, which stores the token).
"""

from __future__ import annotations

import os

from cognichem_client import CogniChem


def main() -> None:
    client = CogniChem(access_token=os.environ["COGNICHEM_ACCESS_TOKEN"])

    session = client.chat.sessions.create("Docking plan")
    question = "How should I dock aspirin against COX-1? Estimate the cost."
    quote = client.chat.estimate(session.id, question)
    print(f"turn hold ${quote.hold_usd:.4f} ({quote.reasoning_effort})")

    for event in client.chat.stream(session.id, question):
        if event.event == "token":
            print(event.data["delta"], end="", flush=True)
        elif event.event == "done":
            print(f"\nbilled ${event.data['billed_usd']:.4f}")

    for proposal in client.chat.proposals.list(session.id).items:
        print(proposal.id, proposal.kind, proposal.status, proposal.estimate_usd)
        # To run it: client.chat.proposals.approve(
        #     session.id, proposal.id, proposal.estimate_usd
        # )


if __name__ == "__main__":
    main()
