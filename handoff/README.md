# Claude clip handoff

With `LLM=handoff` in `.env`, the app does not call any AI API. When a clip job
reaches the "pick the best moments" step, the worker writes
`<id>.request.md` here (transcript + full selection brief + JSON schema) and
waits up to `HANDOFF_TIMEOUT_SECONDS` (default ~2h45m) for `<id>.response.json`.

## Isaac's side
1. Start ClipCreator, open http://localhost:3107.
2. Paste a YouTube link (or drag in a video file) and start the job.
3. Tell Claude in chat: "pick my clips". Claude must have this folder
   (`supoclip-main`) connected.
4. When Claude has answered, the job continues on its own: cutting,
   vertical crop, word-synced subtitles, hook titles.

## Claude's side
1. Read the newest `*.request.md` in this folder (ignore ones with a matching
   `.done.json`).
2. Follow its brief exactly: contiguous ranges, timestamps that exist in the
   transcript, 15-60 s, start on a self-contained sentence, end on a finished
   thought, strong hook, honest scores, a 3-9 word `hook_title`.
3. Write one JSON object to `<id>.response.json` (write to a temp name, then
   rename, so the worker never reads a half-written file).
4. If `<id>.error.txt` appears, fix the problem it names and write the
   response again.
5. `<id>.done.json` means it was accepted.
