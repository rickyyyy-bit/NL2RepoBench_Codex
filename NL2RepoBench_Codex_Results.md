# NL2RepoBench Codex results

GPT-6.1 Sol via ELM ran four repository tasks three times each using medium reasoning, a context window of 200,000 tokens and Codex CLI 0.167.2.

## Findings

Across the 12 trials, jsonlines consistently passed 26 of 27 tests and boltons averaged 99.61%. Parse showed the largest variation, with scores from 70 to 92 out of 96.

The reported scores came from the Codex-only runner used for these experiments. The submission connects the same generation backend to Dalongbao's shared runner. Generation had network access.

## jsonlines

| Metric | Trial 1 | Trial 2 | Trial 3 | Mean | Sample SD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pass rate | 26/27 (96.30%) | 26/27 (96.30%) | 26/27 (96.30%) | 96.30% | 0.00 pp |
| Generation time (s) | 348.838 | 347.176 | 301.567 | 332.527 | 26.825 |
| Pytest time (s) | 0.06 | 0.07 | 0.07 | 0.067 | 0.006 |
| Input tokens | 687,513 | 856,319 | 605,305 | 716,379.0 | 127,972.4 |
| Cached input tokens | 632,506 | 797,033 | 552,912 | 660,817.0 | 124,498.6 |
| Output tokens | 23,876 | 23,574 | 21,288 | 22,912.7 | 1,415.1 |

## parse

| Metric | Trial 1 | Trial 2 | Trial 3 | Mean | Sample SD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pass rate | 92/96 (95.83%) | 70/96 (72.92%) | 87/96 (90.63%) | 86.46% | 12.01 pp |
| Generation time (s) | 439.042 | 511.039 | 377.200 | 442.427 | 66.984 |
| Pytest time (s) | 0.15 | 0.23 | 0.14 | 0.173 | 0.049 |
| Input tokens | 1,349,975 | 1,065,872 | 1,319,787 | 1,245,211.3 | 156,044.1 |
| Cached input tokens | 1,272,816 | 997,082 | 1,236,827 | 1,168,908.3 | 149,890.0 |
| Output tokens | 24,818 | 34,717 | 24,850 | 28,128.3 | 5,706.0 |

**Trial 2 (70/96).** Pytest recorded 26 failures, 22 more than in trial 1. The additional failures included regex pattern generation, number and date parsing, and access to parsed results. Pytest also reported one skipped test. The benchmark's denominator of 96 counts the 70 passes and 26 failures.

## math-verify

| Metric | Trial 1 | Trial 2 | Trial 3 | Mean | Sample SD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pass rate | 163/192 (84.90%) | 165/192 (85.94%) | 176/192 (91.67%) | 87.50% | 3.65 pp |
| Generation time (s) | 621.760 | 589.747 | 678.281 | 629.929 | 44.829 |
| Pytest time (s) | 7.26 | 7.74 | 7.14 | 7.380 | 0.317 |
| Input tokens | 1,542,996 | 1,853,273 | 2,211,738 | 1,869,335.7 | 334,660.2 |
| Cached input tokens | 1,453,749 | 1,764,131 | 2,114,440 | 1,777,440.0 | 330,546.5 |
| Output tokens | 45,461 | 43,069 | 47,235 | 45,255.0 | 2,090.6 |

## boltons

| Metric | Trial 1 | Trial 2 | Trial 3 | Mean | Sample SD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pass rate | 420/423 (99.29%) | 422/423 (99.76%) | 422/423 (99.76%) | 99.61% | 0.27 pp |
| Generation time (s) | 598.124 | 494.860 | 451.014 | 514.666 | 75.528 |
| Pytest time (s) | 1.88 | 1.64 | 1.71 | 1.743 | 0.123 |
| Input tokens | 4,614,224 | 3,966,890 | 3,230,743 | 3,937,285.7 | 692,215.5 |
| Cached input tokens | 4,470,852 | 3,832,069 | 3,110,069 | 3,804,330.0 | 680,815.5 |
| Output tokens | 40,058 | 34,071 | 31,881 | 35,336.7 | 4,232.9 |

Pass rates use the benchmark's configured test counts. The mean and sample standard deviation use the unrounded trial pass rates. Pass-rate SD is measured in percentage points (pp).

Pytest time measures test execution. Generation time covers the generation container lifecycle and excludes grading. The runner reports token usage summed across completed turns. Cached input tokens are included in the input token count.
