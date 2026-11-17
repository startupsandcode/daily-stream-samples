# Run It Twice: the signup retry demo

A self-contained companion to **What If Your AI Runs the Same Task Twice?** Click a fake workshop signup and see the HTTP response and the real SQLite rows side by side. No AI account, API key, email, container, or package install. The demo isolates the write an agent or workflow would call.

## Start it

Install Python 3.9+ if it isn't already on the recording computer. From this folder:

```powershell
# Windows
py -3 demo.py
```

```bash
# macOS or Linux
python3 demo.py
```

Open **http://127.0.0.1:8000**. Keep the terminal open. Press Ctrl+C to stop.
If port 8000 is busy, add `--port 8001` and open **http://127.0.0.1:8001**.
Don't open `index.html` directly: the Python process serves the page and API.

## What to click on stream

| Part | Click | What to point at |
| --- | --- | --- |
| 1. Show the bug | **Reset demo**, then **Send / replay signup-42** under *Blind insert* twice. | HTTP **201** twice. Two distinct task IDs for the same signup. |
| 2. Show the fix | **Reset demo**, then **Send / retry signup-42** under *Stable key + database constraint* twice. | HTTP **201**, then **200 / Reused**. Both point to task #1; the table has **one** row with key `welcome-task:signup-42`. |
| 3. Show it isn't blocking new work | **Send new signup-43**. | HTTP **201**. The table has two rows, one per signup. Gaps between task IDs are normal after an insert conflict. |
| 4. Show the hard case | **Reset demo**, then **Send signup-42 + simulate 504**. Pause. | The caller gets HTTP **504**, with no task ID. The separate table read still shows one saved task. The demo deliberately returns a 504 after commit; it does not wait for a real gateway or network to fail. |
| 5. Recover | **Send / retry signup-42** once, without the 504 button. | HTTP **200 / Reused task #1**. There is still **one** row. |

**Say it plainly:** “The caller doesn't know if the write happened. But it can retry with the same key. The database won't create another row.”

## Where is the destination table?

The Python server creates **`.demo/signup.sqlite3`** beside `demo.py` on first launch. The destination is the **`welcome_tasks`** table in that file. The browser panel reads it from **`GET /api/tasks`**. The data stays local and survives restarting the server. **Reset demo** clears only the demo table.

To inspect it without the UI, open **http://127.0.0.1:8000/api/tasks** for the raw JSON, or use any SQLite viewer with:

```sql
SELECT task_id, mode, signup_id, task, action_key
FROM welcome_tasks ORDER BY task_id;
```

## Where is the code?

- [`demo.py`](demo.py): `Store.create()` shows the stable key and the `UNIQUE` constraint with `ON CONFLICT DO NOTHING`. The HTTP handler returns the simulated 504 only after `Store.create()` commits.
- [`index.html`](index.html): the buttons, the caller's response, and the separately fetched table.
- [`test_demo.py`](test_demo.py): HTTP integration tests for duplication, safe retries, new signups, reset, and the 504-after-commit case. The timeout test also checks the on-disk SQLite file independently.

Run tests with `py -3 -m unittest -v` (Windows) or `python3 -m unittest -v` (macOS/Linux). Tests use a temporary database and don't touch your show data. This demo binds only to localhost and is not a production app.
