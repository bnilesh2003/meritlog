# Compile strategies

All strategies follow the evidence rules in SKILL.md: CONFIRMED entries only, no invented numbers, `[NEEDS METRIC: …]` where a number is missing, source ids on every line, and a safety pass at the end.

## xyz (default): resume bullets
Laszlo Bock's (former Google SVP of People Operations) formula:
**"Accomplished [X] as measured by [Y], by doing [Z]."**

- X = the outcome (`result`), Y = the number (`metrics`/`scope`), Z = the actions (`actions`).
- Start with a strong past-tense verb; one line, about 25 words at most.
- No Y available → write it as CAR and add `[NEEDS METRIC: <specific question>]`.

> Reduced critical-vulnerability remediation time by ~50% across ~40 services by building an automated SAST triage pipeline in CI. [WL-0012]

## car: Challenge → Action → Result
For strong work that has no metric. Good when the challenge itself shows seniority.

> Faced with inconsistent secrets handling across teams, designed and rolled out a centralized secrets-management pattern, now the default for new services. [WL-0007]

## star: interview stories (not resume bullets)
Situation, Task, Action, Result, written as 4 short paragraphs per entry, each 150-200 words in total. Use it for the user's strongest 5-8 entries. Include ABANDONED or partly successful work when it makes a good "what did you learn" story, and label it as such. Add a "Likely follow-up questions" list under each story.

## summary: profile / LinkedIn "About"
3-4 sentences built from patterns across themes (what the user does most, at what scale, with what results), then a skills line drawn from `skills` and `tools`. No single-entry claims that aren't backed by an id. List the ids used at the end.

## all
Produce xyz bullets grouped by theme, then STAR stories for the top 5, then the summary, in one file.

## With a job description
1. Pull out the JD's top 6-8 requirements.
2. Map each requirement to supporting entries; report requirements with **no** supporting entry as gaps (don't paper over them).
3. Order bullets by requirement coverage, and use the JD's vocabulary only where the entry supports it.
