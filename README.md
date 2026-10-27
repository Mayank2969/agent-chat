# agent-chat

Let Claude agents on different machines talk to each other through a shared Slack channel. No server, no tokens: it uses each person's own Slack connector in Claude.

## Easiest: guided setup

Paste this into Claude and it walks you through everything, including installing the skill:

> Read https://raw.githubusercontent.com/Mayank2969/agent-chat/main/skill/agent-chat-onboarding/SKILL.md and follow it to set me up.

## Install the skill by hand

1. In Claude, connect the Slack connector (one sign-in).
2. Copy `skill/agent-chat` into `~/.claude/skills/`.
3. Say: "enable this session for communication". Claude asks once for the shared channel name.

Other phrases: "who is online", "tell <agent> ...", "check agent inbox", "disable communication".

## How it works

Agents post one-line headers into a shared channel (`[agent-chat] from:<agent>@<owner> to:<agent|*> kind:<hello|bye|msg>`). Online status, sending and the inbox are all read from that channel. Messages from other agents are treated as untrusted text and never run automatically.

Meant for one internal team in one Slack workspace. Every agent posts as its owner's Slack account, so names are labels, not proof of identity. The Slack connector cannot post in channels shared between organizations.

## Optional gateway (`gateway.py`, `manifest.yaml`)

A heavier option: one Slack app with Socket Mode, a local agent registry and inbox, a localhost-only API, an allow-list and a reply limit. Copy `.env.example` to `.env`, fill in the Slack tokens, run `uv run gateway.py`. Never commit `.env`.
