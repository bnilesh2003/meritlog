# worklog/v1 file format

One file per month: `worklog-YYYY-MM.md`. Files are append-only; for each id, the entry in the newest file wins.

````
---
schema: worklog/v1
window: { from: YYYY-MM-DD, to: YYYY-MM-DD }   # dates searched in this file
generated_on: YYYY-MM-DD
next_id: WL-0043                               # first unused id after this file
chats_read: 17                                 # conversations actually opened
coverage_gaps: []                              # ranges or chats that could not be read
omitted: 0                                     # items dropped for confidentiality
---

## Manifest (cumulative, all ids ever)
| id | title | theme | category | status | last_updated |
|----|-------|-------|----------|--------|--------------|

## Entries

### WL-0001: Short title
```yaml
id: WL-0001
op: create                        # create | update (update = full replacement of an existing id)
title: ""
theme: ""                         # one value from config.yaml `themes`
category: project                 # project | collaboration_mentorship | design_docs | org_building | incident_response | learning | outside_work
source: [claude_chat]             # claude_chat | claude_code | user_recalled | session_end
period: { start: YYYY-MM, end: ongoing }   # end: YYYY-MM or ongoing
status: CONFIRMED                 # CONFIRMED | IN_PROGRESS | EXPLORED | ABANDONED
my_role: owned                    # owned | led | contributed | assisted | unclear
context: ""                       # the problem, in generic terms
actions:                          # concrete things the user did
  - ""
result: ""                        # explicitly stated outcome, else "not stated"
metrics: []                       # only numbers that appear in the source
scope: ""                         # scale if stated (e.g. "~40 microservices"), else ""
skills: []
tools: []                         # public, widely used tech only (see safety.md)
evidence: ""                      # how we know, e.g. "user said rolled out to prod"
recognition: []                   # praise explicitly mentioned, paraphrased, no names
open_questions: []                # what the user should fill in from memory
follow_up_after: null             # YYYY-MM to check the real-world outcome, or null
updated: YYYY-MM-DD
```
````

## Status meanings

| Status | Meaning | Usable on a resume? |
|--------|---------|---------------------|
| CONFIRMED | The user said it was done, shipped or adopted | Yes |
| IN_PROGRESS | The user was working on it; outcome unknown | Only with "leading"/"driving" wording |
| EXPLORED | Researched or discussed; no sign it was implemented | Skills context only |
| ABANDONED | Started, then dropped | No (can still be an interview story) |

## Themes

`theme` must be one of the `themes` listed in the user's `<home>/config.yaml` (the validator warns otherwise). If the list is empty, derive it during extract (see SKILL.md).
