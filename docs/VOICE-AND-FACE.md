# Give her a voice and a face

Out of the box she listens with Whisper and answers with the Mac's own `say`. Nothing leaves the Mac.

Two keys make her sound and look like a person. Both are optional. Skip either one and she falls back quietly.

## Her voice: ElevenLabs

Free plan: 10,000 credits a month, roughly 10 to 20 minutes of her talking.

1. Sign up at [elevenlabs.io](https://elevenlabs.io). The Free plan is enough.
2. Go to Developers, then API Keys, then Create Key. Turn on Text to Speech and Speech to Text. Voices can be Read. Nothing else.
3. Copy the key and save it:

```fish
echo "set -gx ELEVENLABS_API_KEY 'sk_...'" >> ~/.config/fish/secrets.fish
```

4. Open a new terminal and talk to her:

```bash
./.venv/bin/python app/chat.py --voice
```

Her default voice is Sarah, one of the premade voices. The Free plan can only use premade voices over the API, a library voice answers 402.

To pick another, just ask. "What voices do you have" lists the premade ones. "Change your voice to George" switches, after a yes. It is free: it only saves the voice in her `character.json`. A name she doesn't know changes nothing, and she names the close ones. `ELEVENLABS_VOICE` still wins if you set it.

With a key set, the words she says go to ElevenLabs to be voiced. That is the one thing voice mode sends off the Mac. No key, no send.

## Her face: Higgsfield

Pay as you go, no subscription. Her face is made **once**, then replayed. Nothing is rendered per reply.

| What | Cost |
|---|---|
| A portrait (Soul) | a few cents |
| A 5 second video loop (Seedance 2.5, 480p) | about $0.70 |
| A full face: portrait, idle loop, talking loop | about $1.50 |

1. Sign up at [cloud.higgsfield.ai](https://cloud.higgsfield.ai) and add $10. That is plenty for her face and a few restyles.
2. API keys, then Create key. Copy it. It looks like `id:secret`.

```fish
echo "set -gx HIGGSFIELD_API_KEY 'id:secret'" >> ~/.config/fish/secrets.fish
```

3. Make her face with the character-creator skill in Claude Code: "make her ginger", "round glasses", "new character". It writes a portrait first. When you like it, it renders the loops into `~/.samantha/characters/samantha/`.
Or just ask her. "Change your look: ginger with glasses" or "make yourself a redhead" makes a new portrait, about 5 cents, into a `staged` folder next to her current one. Her face stays the same until you say "keep that look". That renders her idle and talking loops from the new portrait, about $1.40, then swaps it in and keeps the old look in `old/`. Both ask first, and the question says the price before anything is spent.

4. Talk to her with her face on:

```bash
./.venv/bin/python app/chat.py --voice --face
```

A window opens on `localhost`. She breathes and blinks while idle, nods while you talk, and talks while her voice plays.

## In the Mac app

The window has Voice and Face buttons in its toolbar. Voice says every reply out loud. Face opens her face window. The Customize menu has Change voice... and Change look..., which send the same sentences as above.

## Keep the keys private

Both keys live in `~/.config/fish/secrets.fish`, never in the repo. Keep that file to yourself: `chmod 600 ~/.config/fish/secrets.fish`.
