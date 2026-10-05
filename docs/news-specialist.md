# News Specialist

## Flow

Confirmed persisted identity -> explicit source requests -> existing RAW storage and
OPS run verification -> metadata validation -> bounded title-name relevance ->
reviewable candidates -> aggregator -> unscored analyst review.

`NewsSpecialist` uses the portable `ResearchProvider` interface. The existing
`PipelineResearchProvider` supplies verified evidence. The local graph and durable
stage runner accept it under the `news` branch/stage. Deployment and UI are unchanged.

## Sources And Limits

- `gdelt_doc_news`: bounded last-24-hour discovery, at most 50 results per request;
  worldwide discovery is not complete global coverage. Publisher trust remains
  `not_assessed`, even when the provider returns an article.
- `uk_fca_newsroom`: official recent-news supplement, not comprehensive enforcement
  history or worldwide official-newsroom coverage. Official origin does not establish
  the truth, legal finality or adverse interpretation of a headline.
- Metadata and links only. No article bodies are downloaded, summarized or treated
  as licensed. Wider official feeds and a licensed content provider remain future work.

## Policy

All findings remain identity-pending with no confirmed `subject_id`. Full bounded
legal-name/alias title mentions indicate relevance only; party role and article claims
require review. Short aliases, translation, sentiment and fraud inference are not used.
This policy can miss abbreviated/transliterated names and body-only mentions.

Language, country, publisher and provider-seen metadata are retained. Seen time is
not publication time; no event date is invented. Exact URL repeats within a source
are suppressed; normalized-title groups indicate possible duplicates, not proven
syndication or independent corroboration. Cross-source records remain auditable.

Missing lineage, invalid URLs/schema and duplicate record IDs withhold the source
dataset. Stale retrievals over 24 hours or more than five minutes in the future are
withheld. Failures/partial coverage remain explicit while other sources continue.
Verified empty searches do not establish absence of news or adverse risk.

Unsupported GDELT query syntax is blocked rather than rewriting the legal name.
No automatic retries, full-text fetching, scoring or rejection are introduced.

## Usage

```bash
.venv/bin/trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live --news
```

Use repeatable `--news-source` to select GDELT and/or FCA. Add `--sanctions`,
`--ownership`, and `--legal` to enable all four research specialists. The shared
pipeline serializes source runs on its Snowflake session. Commands perform network
requests and existing RAW/OPS writes; they do not deploy infrastructure.

Tests cover metadata/trust boundaries, relevance, duplicate hints, provenance
failures, freshness, empty results, source outages, identity gating, CLI validation,
graph aggregation and durable stage retries. Live provider availability and deployed
Snowflake execution were not verified in this change.

Remaining: multilingual attribution, alias query planning, licensed content access,
broader official newsroom coverage, publisher policy, publication-date extraction,
syndication analysis, cached replay and deployed runtime wiring.
