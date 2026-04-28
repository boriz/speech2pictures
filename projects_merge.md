# Speech2Pictures simple plan

## Goal

Get `web-app` working.
Then improve it.

## Steps

1. Run `web-app` in venv

   * install current deps
   * try to start app
   * see what breaks

2. Make `web-app` work

   * fix startup issues
   * fix obvious broken routes/forms
   * make basic flow work

3. Clean only painful parts

   * remove obvious duplication
   * clean config if needed
   * refactor only blockers

4. Upgrade deps and models

   * do it one piece at a time
   * test after each change

5. Add features

   * only after baseline is stable

## UI shape

Use 3 tabs.

1. Gallery

* browse generated images
* open past items

2. Generate

* enter long text
* or enter title/style/description directly
* generate image manually

3. Photo Frame

* microphone listens
* server runs speech-to-text
* transcript feeds image pipeline automatically
* current image is shown like a dynamic digital photo frame

This keeps each mode separate and easy to understand.

## Input logic

Use one internal prompt format:

* title
* style
* description

Two ways to fill it:

1. Long text input

   * app extracts title/style/description
   * user can review/edit
   * then send to image model

2. Direct prompt input

   * user enters title/style/description
   * send to image model

This keeps one pipeline instead of two separate logic paths.

## Speech-to-text plan

For speech input:

* browser captures audio
* server runs speech-to-text
* transcript goes into existing long-text flow

Preferred approach:

* use browser mic/audio features
* do STT on server, not in browser
* likely use `faster-whisper`

Reason:

* simpler product flow
* better browser compatibility
* keeps one backend-controlled transcription path

## Initial release assumption

For v1:

* only one client connected at a time
* no need for multi-user design yet
* no need for concurrency-heavy architecture yet

This keeps first version simpler.

## Possible later step

After baseline and speech-to-text are working:

* evaluate upgrading image generation model
* likely move to newer Stable Diffusion generation stack

Not immediate.
Do after app is stable.

## Rule

No big rewrite first.
Keep working baseline at each step.
