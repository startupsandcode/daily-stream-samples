# Daily Stream Samples

Sample code I demonstrate on my daily stream. Each folder is a small, self-contained example you can run yourself, usually with nothing to install and no accounts or API keys.

## Samples

| Sample | What it shows | Needs |
| --- | --- | --- |
| [signup-retry-demo](signup-retry-demo/) | What happens when an AI agent or workflow runs the same write twice, and how a stable key plus a database `UNIQUE` constraint makes retries safe. Includes a simulated 504 after commit. | Python 3.9+ (stdlib only) |

## Run a sample

Every sample has its own README with exact steps. The short version:

```bash
git clone https://github.com/startupsandcode/daily-stream-samples.git
cd daily-stream-samples/signup-retry-demo
python3 demo.py        # Windows: py -3 demo.py
```

Then open the URL it prints (for the retry demo, http://127.0.0.1:8000).

## Layout

```
daily-stream-samples/
├── README.md              <- you are here
└── <sample-name>/         <- one folder per sample
    ├── README.md          <- what it is, how to run it, what to look at
    └── ...
```

Samples are independent: no shared dependencies, so you can copy one folder out and it still works.

## Notes

- These are demos for learning and showing ideas, not production code.
- Servers bind to localhost only.
- Data in the demos is fake.
