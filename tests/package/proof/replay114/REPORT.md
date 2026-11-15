# RULING 114: V4 ON AN XINFER WORKER (the x-bf-tunnel-instance header)

deepseek/deepseek-v4-flash-0731-abliterated, response_format json_object, reasoning_effort none, each record's own max_tokens / seed / system (as replay111). 30 of replay111's 93 unclosed records, each asked WITH the header `x-bf-tunnel-instance: pinga282` and WITHOUT it, the same seed. $0.0094 reported.

| | calls | errors | unclosed | finish_reason of the unclosed | out_tokens median (unclosed) | shapes |
|---|---|---|---|---|---|---|
| with the header | 30 | 0 | 15 | {'stop': 14, 'length': 1} | 251.5 (291) | {'closed JSON': 15, 'truncated': 15} |
| without | 30 | 0 | 17 | {'stop': 17} | 191.0 (366) | {'truncated': 17, 'closed JSON': 13} |

- x-bf-* response headers and their values (every attempt), with the header: none; without: none.
- Calls retried by the gateway client (429 / 5xx; every attempt's headers kept): 0.
- Response headers whose value differs between the two legs of a record (count of records): {'x-request-id': 30, 'x-generation-id': 30, 'content-length': 30, 'date': 30, 'x-ratelimit-remaining': 27, 'x-ratelimit-reset': 24, 'vary': 5}.
- The model each response names: with {'deepseek/deepseek-v4-flash-0731-abliterated': 30}; without {'deepseek/deepseek-v4-flash-0731-abliterated': 30}.
