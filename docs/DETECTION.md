# Detection

What Conformance detects, how each layer works, and how to tune it.

## Regular expressions or a guard model?

Both, because they answer different questions.

| Question | Right tool | Why |
|---|---|---|
| Is there a card number, an IBAN, an access key in this text? | Patterns with validation | These have a fixed structure and often a checksum. A pattern finds them in under a millisecond, with near perfect precision, and can say exactly where the value starts and ends so it can be masked |
| Is there a person's name or an address in this text? | A named entity model | Names have no structure. A statistical model is needed, and it will make some mistakes |
| Is this request asking for something harmful? | A guard model such as Llama Guard | This is a judgement about meaning, not about a string. No pattern can make it |
| Is this text trying to manipulate the model? | Heuristics first, a classifier for higher recall | Known attack phrasings are cheap to catch. Novel ones need a model |
| Does this mention our secret project? | A list you maintain | Only you know your code names |

A guard model alone would be the wrong design for data protection. Llama Guard classifies a conversation as safe or unsafe by hazard category. It does not return the position of a card number, so it cannot mask one. It adds hundreds of milliseconds, and it needs a GPU to do that at volume. A pattern engine alone would be blind to intent. So the layers are stacked, cheapest first:

```text
every request ──► patterns ──► credentials ──► injection ──► custom terms      always on, under 1 ms each
                                                   │
new content only ─────────────────────────────────►├──► named entities         optional, 5 to 30 ms
                                                   │
latest user message ──────────────────────────────►└──► guard model            optional, off the request path by default
```

## Layer 1: PII patterns

File: `backend/app/detection/patterns.py`

| Entity | Category | Validation |
|---|---|---|
| Payment card number | Financial identifiers | Luhn checksum, plausible issuer prefix, 13 to 19 digits |
| IBAN | Financial identifiers | Country-specific length and the mod 97 check |
| Italian fiscal code | Government and national IDs | Check character |
| US social security number | Government and national IDs | Valid area, group and serial ranges. Without dashes only next to the words SSN or social security |
| Spanish DNI and NIE | Government and national IDs | Check letter, plus a context word |
| French social security number | Government and national IDs | Control key |
| UK national insurance number | Government and national IDs | Valid prefix rules |
| German tax ID, passport number | Government and national IDs | Context word required |
| Date of birth | Government and national IDs | Only after words such as "born on" or "date of birth" |
| Medical record number | Health information | Only after "MRN", "medical record" or "patient id" |
| Email address, phone number, public IP address | Contact details | Phone numbers need an international prefix or a context word. Private IP ranges are ignored |
| Confidentiality markings | Confidential business data | Phrases such as "strictly confidential", "internal use only", "attorney-client privileged" |

Validation is what keeps false positives low. A 16 digit order number is not reported as a card because it fails the Luhn check. A version string is not reported as an IP address. The test suite checks the whole benign prompt corpus for zero findings.

## Layer 2: Credentials and secrets

File: `backend/app/detection/credentials.py`

- **Known formats:** AWS access keys and secret keys, GitHub tokens, Slack tokens, OpenAI and Anthropic API keys, Google API keys, Stripe live keys, Azure storage keys, JSON web tokens, private key blocks, and database connection strings that contain a password.
- **Generic secrets:** an assignment to a name like `password`, `secret`, `api_key` or `token` is reported when the value has high entropy and mixes letters and digits. Placeholders such as `changeme`, `${API_KEY}` or `os.environ[...]` are ignored.

Credentials are the one category the default policy blocks. A leaked key is immediately exploitable and there is no reason for a model to see one.

## Layer 3: Prompt injection heuristics

File: `backend/app/detection/injection.py`

Weighted signals for instruction override ("ignore all previous instructions"), system prompt extraction, role hijacking ("you are now in developer mode"), chat template delimiters, credential exfiltration requests, policy evasion and encoded payloads. Signals combine as independent evidence, so one strong signal or two weaker ones cross the threshold.

This layer matters most for tool results and retrieved documents, where text written by an outsider reaches the model. It catches common phrasings cheaply. It will not catch a novel or obfuscated attack: treat it as an early warning, not a guarantee.

## Layer 4: Custom terms

Defined per policy in the dashboard: keywords or regular expressions with a label and a severity. Use them for project code names, customer account number formats, internal classification labels and product names under embargo. Matches fall under the "Confidential business data" category.

## Layer 5: Named entities (optional)

File: `backend/app/detection/ner.py`

Microsoft Presidio with a spaCy model finds names of people and places. It is included in the default image and can be switched off with `NER_ENABLED=false`.

- It runs on new content only (the latest turn and tool results) and on a bounded amount of text, because it is far slower than the pattern layers.
- The default policy only **logs** names. Masking every name makes ordinary work impossible ("write to Anna about the meeting"). Mask names only for tools where that is the point, such as an HR screening assistant.
- The default model is English. For other languages set `NER_MODEL` and `NER_LANGUAGE` to a spaCy model for that language and add it to the image. Expect lower accuracy from small models.
- To detect more entity types set `NER_ENTITIES`.

## Layer 6: Guard model (optional)

File: `backend/app/detection/guard_llm.py`

Llama Guard, served by Ollama or any OpenAI-compatible server, classifies the latest user message into hazard categories (violent crime, weapons, hate, self-harm, privacy, code interpreter abuse and others). Findings fall under "Unsafe content".

| Setting | Effect |
|---|---|
| `GUARD_LLM_MODE=async` (default) | Classification runs in parallel with the model call. No added latency. A finding raises an alert but cannot block that request |
| `GUARD_LLM_MODE=inline` | The gateway waits for the verdict, so the policy can block. Adds the guard's latency to every request. Use a GPU |
| Guard unreachable or slow | Fails open after `GUARD_LLM_TIMEOUT_SECONDS`. The detector shows as unavailable under Settings |

When is it worth enabling? For internal productivity tools the main risk is data leaving the company, which layers 1 to 4 cover. Enable the guard model when a tool is exposed to customers or the public, when a tool can take actions, or when your acceptable use policy needs evidence about misuse.

## How findings become decisions

1. Overlapping matches are resolved to the strongest one (severity, then confidence, then length).
2. The tool's policy assigns each finding an action by category: ignore, log, mask or block.
3. The request gets the strongest action among its findings. In monitor mode the action is recorded but not applied.
4. A keyed fingerprint of each value marks it as new or already seen for that user. Alerts and risk scores use new findings only.

Severity levels:

| Severity | Examples |
|---|---|
| Critical | Private keys, cloud provider keys, model provider keys |
| High | Card numbers, IBANs, national IDs, medical record numbers, database passwords |
| Medium | Confidentiality markings, dates of birth, injection attempts |
| Low | Email addresses, phone numbers, names |

## Tuning

Run every new tool in monitor mode first and look at what fires.

| Observation | Action |
|---|---|
| A category is noise for this tool, for example email addresses in a sales assistant | Set the category to Ignore in that tool's policy |
| One alert rule fires too often | Raise its minimum severity or switch it off under Settings |
| A specific pattern misfires on your data | Mark the alerts as false positive so the rate is measured, then adjust or remove the pattern in `patterns.py`. Add a test with the misfiring text |
| Something sensitive is missed | Add a custom term if it is a fixed string or pattern. Add a pattern with a validator if it is a structured identifier |
| Unsure what a policy would do | Paste the text into **Policies, Test a prompt** |

To add a pattern, append a `PatternSpec` in `patterns.py` with the entity name, category, severity, a regular expression and, where the format has one, a checksum validator or a required context word. Add a positive and a negative case to `backend/tests/test_detection.py`.

## What is not detected in this version

- Text inside images, PDFs and other attachments.
- Sensitive content that has been paraphrased, translated or encoded.
- Structured identifiers of countries that are not listed above.
- Exact matches against your own databases (for example your real customer list).

The [roadmap](ROADMAP.md) lists the planned additions: file and image scanning, exact data matching, a dedicated injection classifier and more national identifiers.
