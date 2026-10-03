# Personas

The same worker answers as two people. Samantha is the default. Joshua is a persona the portfolio switches on. Nothing else in the pipeline changes.

## How a request picks one

Joshua Tree's chat sends an Ollama-shaped body to `/api/chat`. The portfolio adds one field:

```
{"model":"samantha","persona":"joshua","stream":false,"think":false,"messages":[...]}
```

The worker reads it in one place (`worker.js`): `persona = body.persona === "joshua" ? "joshua" : ""`. Anything else is Samantha. Only the newest user message is answered, capped at 200 characters; earlier turns are context.

## How Joshua answers

`chatAnswer(env, question, persona)` tries these in order:

1. **Fixed lines** (`JOSHUA_TALK`). Greetings, thanks, "who are you", "show me around", and the phone demo's rotating questions (Vancouver, his life, what he is building, what to look at first, what he does for fun). Exact, instant, no model.
2. **The pack** (`JOSHUA_DOCS`). A short third-person page about him and what he has built, read by the grounded reader. `asJoshua` then turns "Joshua is a developer" into "I'm a developer" so the answer is in his voice.
3. **Everything else**: the normal Joshua Tree pipeline, then the general one. A question that names Joshua Tree never falls through to the web: declining is honest, a stray hit on the wrong page is not.

To teach him a new answer, add a line to `JOSHUA_TALK` if it must be exact, or a sentence to `JOSHUA_DOCS` if the reader should find it.

## The cache

Replies are cached by question. Joshua's key is `chat-joshua2`, Samantha's is `chat`. When you change what he says, change the suffix (`joshua2` to `joshua3`), or the old answers, including declines, keep coming back. This bit us once on 2026-10-03: new fixed lines did nothing until the key changed.

## His voice

`/api/speak` takes `{"text":"...","format":"pcm8","voice":"joshua"}`. `voice: "joshua"` uses his cloned ElevenLabs voice (`JOSHUA_VOICE`), anything else uses Samantha's (`SPEAK_VOICE`). The audio cache key includes the voice id, so the two never mix. Joshua Tree's site worker forwards `?v=joshua` on `/api/speak` as that field.

## Where it is used

Joshua Tree's portfolio mode (`docs/PORTFOLIO.md` in that repo): the chat is titled Joshua, sends `persona: joshua`, and asks for his voice. Tests are in `tests/`; run the suite before pushing, then check `/stats.json` for the live version.
