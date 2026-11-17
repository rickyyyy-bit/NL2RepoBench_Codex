# Codex integration submission

This submission adds a Docker-based Codex backend to NL2RepoBench. Codex generates a repository from the benchmark prompt in a fresh workspace. The shared grader evaluates a separate copy using the benchmark’s task fixtures, test commands, and passed-test scorer.

| Start here | What it covers |
| --- | --- |
| [README.md](README.md) | Install the integration and run a benchmark task |
| [ENGINEERING_EVIDENCE.md](ENGINEERING_EVIDENCE.md) | What I did well, supporting checks, and remaining limits |
| [NL2RepoBench_Codex_Results.md](NL2RepoBench_Codex_Results.md) | Measured scores, timings, and token usage by task |

The source and patch use the same Codex implementation as [my GitHub checkout](https://github.com/rickyyyy-bit/NL2RepoBench_Codex/tree/5b297651d664ca05a8a6181bcd4f6de8957c4516). The README specifies the reference revision used for setup.
