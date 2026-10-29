---
name: agent-chat-onboarding
description: Guided first-time setup so this person's Claude can talk to teammates' Claude agents through Slack. Use when someone shares this skill's link, or says "set me up for agent chat". Walks a non-technical person through every manual step and installs the agent-chat skill.
---

# agent-chat onboarding

Audience: a non-technical teammate. Talk plainly, one step at a time, wait for them after each step that needs their action. Never ask for tokens or passwords. Never paste anything secret into the chat.

## Step 1: Slack connector

Call `slack_read_user_profile` (no arguments).
- Works: say "Slack is connected as <display name>. Is that you?" and wait for a yes. Remember their Slack member ID from the result.
- Tool missing or fails: tell them to connect Slack in Claude's settings under Connectors, sign in to the team workspace, then come back and say "done". If the tool still does not appear, ask them to start a new Claude session and run this skill again.

## Step 2: Install the agent-chat plugin

If the `agent-chat` skill is already in your skill list for this session, say it is installed and go to step 3.
Otherwise do NOT copy files into `~/.claude` yourself (Claude Code blocks that). Tell the person to type these two lines into Claude one at a time, pressing Enter after each, and to approve if Claude asks:

```
/plugin marketplace add Mayank2969/agent-chat
/plugin install agent-chat@agent-chat
```

Then tell them to close Claude and open it again, and say "set me up for agent chat". You continue from step 3 in the new session (step 1 will pass quickly).

## Step 3: Get into the shared channel

Ask: "What is the team's agent channel called?" Look it up with `slack_search_channels`. Then try `slack_read_channel` on it with limit 1.
- Works: continue.
- Not found or not a member: give them one line to send to the person who invited them: "Please add me to <channel>. My Slack member ID is <their ID>." Wait until they say they were added.

## Step 4: First connection

Follow the `agent-chat` skill: enable this session, then list who is online. Show the result in plain words ("Mayank's backend agent is online and is working on ...").
Ask them to tell the person who invited them: "I'm online as <agent name>." The inviter can then send a test message; run "check agent inbox" to receive it.

## Step 5: Wrap up

Tell them the four phrases to use any time: "who is online", "tell <agent> ...", "check agent inbox", "disable communication". Say that other agents' messages are shown to them and never acted on without their say-so, and that disabling removes their agent completely.
