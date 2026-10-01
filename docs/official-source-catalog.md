# Official Source Catalog: Global Starting Set

**Research checked:** 2026-10-01
**Purpose:** Initial source discovery for TrustSignal design, not proof that connectors, commercial rights, or API credentials are available.

## 1. How to read this catalog

There is no single government database for all legal entities or adverse events worldwide. Company registration is generally maintained by national or subnational authorities. Even within a country, companies, nonprofits, financial institutions, charities, and public bodies may use different registers. Access ranges from public APIs and bulk downloads to authenticated, metered, paid, or browser-only portals.

The links below are official authority or public-sector portal entry points. Before production ingestion, each connector needs a recorded review of terms, data licensing, personal-data rules, rate limits, authentication, permitted retention, refresh cadence, and machine-readable access. A searchable webpage alone is not authorization to scrape or re-publish its contents.

Access labels:

- **API / data:** official API, machine-readable download, or official bulk data is documented.
- **Portal / gated:** official search exists, but API, bulk, or reuse access may need account approval, fees, or separate terms.
- **Coverage boundary:** the source covers only a defined population or jurisdiction.

## 2. Cross-border and multi-jurisdiction sources

| Source | What it can support | Access and limits |
|---|---|---|
| [GLEIF LEI data / API](https://www.gleif.org/en/lei-data/access-and-use-lei-data) | LEI legal-entity reference data and parent/child relationship reporting where entities have LEIs. | Global identifier network, not a complete register of every company. Coverage depends on LEI adoption and reported relationship data. Use as a strong cross-border key, not a universal identity oracle. |
| [EU e-Justice: Find a company / BRIS](https://e-justice.europa.eu/topics/registers-business-insolvency-land/business-registers-search-company-eu/general-information-find-company_en) | Search company records in EU, Iceland, Liechtenstein, and Norway; retrieve available national filings and legal-representative information. | Portal search obtains information in real time from participating registers, but available details/documents vary by register. Do not assume public bulk API access. |
| [EU insolvency registers](https://webgate.ec.europa.eu/iri/index.html) | Search insolvency records from participating EU national registers. | Not all Member States are connected; Denmark is excluded from this interface and national search rules differ. Treat uncovered countries as gaps. |
| [EU Beneficial Ownership Registers Interconnection System (BORIS)](https://e-justice.europa.eu/sitemap_en) | Discovery of beneficial-ownership register access points. | Access is governed by EU and national law and is not generally equivalent to unrestricted public bulk access. Verify current lawful access before integration. |
| [UN Security Council Consolidated List](https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list) | UN-designated persons and entities; XML, HTML, and PDF publications. | Official sanctions evidence. Preserve regime/reference number and listing measures; it is not a complete list of national or regional sanctions. |
| [FATF high-risk and increased-monitoring jurisdictions](https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html) | Jurisdiction-level AML/CFT context. | It is a jurisdiction assessment, not a company/watchlist database. Display as jurisdiction context only, never as a company finding. |
| [EU financial sanctions list / data portal](https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions) | EU financial-sanctions designations. | Official data portal; verify the current delivery format, update method, reuse terms, and list scope before building a feed. |

## 3. National and regional company identity sources

| Jurisdiction | Official source | Available route / useful identifiers | Integration note |
|---|---|---|---|
| United States | [SEC EDGAR](https://www.sec.gov/edgar/sec-api-documentation) | Company submissions and XBRL APIs; CIK. | Retain as the existing listed-company/filing adapter. It is not a general US business register; state-level incorporation registries are separate. SEC requests require a declared user agent and rate-aware access. |
| United Kingdom | [Companies House API](https://developer.company-information.service.gov.uk/overview/) | REST API for company records; company number. | API key/account registration is required. Official docs describe public data as live/real-time. Add filing-history and persons-with-significant-control routes subject to field-level access and lawful-use review. |
| France | [INSEE SIRENE API and data](https://www.insee.fr/fr/information/3591226) | API query and bulk files; SIREN/SIRET. | INSEE describes free API and bulk data, daily updates, historical data and succession links. Legal data uses French identifiers and terminology; retain source-native values. |
| Norway | [Brønnøysund Register Centre open-data API](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html) | REST search/detail, change/update endpoints, bulk downloads; organisation number. | Open-data API documents NLOD 2.0. Some person/role details require authorized access. Avoid collecting restricted personal identifiers. |
| European Union / EEA | [BRIS company search](https://e-justice.europa.eu/topics/registers-business-insolvency-land/business-registers-search-company-eu/general-information-find-company_en) | Cross-border company-number search and available national documents; EUID where supplied. | Use as a user-assisted or targeted retrieval path until machine access and terms are confirmed. National registers remain authoritative for full detail. |
| Singapore | [ACRA API Marketplace](https://www.acra.gov.sg/resources/eservice-tools-portals/api-marketplace/) | Entity Information Query, Business Profile Data, financial information, profile/certificate verification. | API subscription is managed through ACRA; some personal information is restricted. A strong candidate for the first Asia-Pacific connector after access approval. |
| Canada (federal) | [Corporations Canada data services](https://ised-isde.canada.ca/site/corporations-canada/en/data-services) | Real-time API / open dataset; corporation number or business number. | Explicitly covers federal corporations, not all provincial/territorial entities or financial institutions. Canada's Business Registries helps route to provincial sources. |
| Australia | [ABN Lookup web services](https://data.gov.au/data/en/dataset/abn-lookup-web-services) | Name/ABN search; hourly-updated service. | API registration is required. ABN is a tax/business identifier, not a substitute for ASIC company registration. ASIC company extracts and search have separate access/fee terms. |
| India | [MCA Company Master Data on data.gov.in](https://www.data.gov.in/catalog/company-master-data) and [MCA Corporate Data Management](https://www.mcacdm.nic.in/company-master-details) | CIN and ROC-wise company data; data API/download catalog and portal. | Public dataset is marked open, but catalog notes a data cutoff for some fields; verify resource-level freshness and schema. Detailed MCA filings may have separate login/fee rules. |
| Japan | [National Tax Agency Corporate Number Web API](https://www.houjin-bangou.nta.go.jp/webapi/index.html) | REST search/detail and change-diff retrieval; 13-digit corporate number. | API application registration/ID is needed. [EDINET](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WEEK0060.html) separately provides listed-company disclosure APIs and requires API registration. |
| South Korea | [Open DART API](https://engopendart.fss.or.kr/intro/main.do) | Corporate overview, filing search, original XML disclosures, and financial data; DART corporation code. | FSS provides API documentation and requires an authentication key. This is a corporate disclosure source, not a complete all-entity corporate register. |
| Brazil | [Receita Federal CNPJ services](https://www.gov.br/receitafederal/pt-br/assuntos/cadastros-e-registros-especiais/cnpj) | CNPJ registration and status; official online lookup and government CNPJ APIs/data services. | Some API catalog services are scoped to federal public bodies; do not assume commercial third-party access. Confirm current official public bulk-data channel, schema, and terms before implementation. |
| New Zealand | [NZBN API](https://portal.api.business.govt.nz/api/nzbn) and [Companies Office APIs](https://www.companiesoffice.govt.nz/data-services/ways-to-get-our-data/using-our-data-through-apis/) | NZBN public data, watchlists/change-event search, bulk data by approval; company register searches. | NZBN says there is no fee for the API; subscription/approval is required. Some Companies Register operations are authenticated, consent-based, or fee-bearing. |
| South Africa | [CIPC APIVerse](https://developer.cipc.co.za/) | Read-only API suite for company search/retrieval and director disqualification. | Official developer portal exists; confirm subscriptions, production access, dataset coverage, and terms. |
| Nigeria | [Corporate Affairs Commission public search](https://icrp.cac.gov.ng/public-search/) and [Beneficial Ownership Register](https://bor.cac.gov.ng/) | Search registered entities by name/registration key and public persons-with-significant-control records. | Official search portals are available. Confirm terms, bulk/API availability, personal-data restrictions, and whether a human-facing portal permits automated use. |
| Saudi Arabia | [Ministry of Commerce commercial registration query](https://mc.gov.sa/en/eservices/Pages/ServiceDetails.aspx?quot=&sID=91) | Search by establishment name or unified national number. | Official portal requires a verification code; treat as portal/manual verification until an authorized machine interface is confirmed. Arabic is the service language. |
| Hong Kong SAR | [Companies Registry e-Search services](https://www.cr.gov.hk/en/electronic/docs/services-e.pdf) | Company existence/status/name history and electronic records. | Official electronic search and documents; fees/access conditions may apply. Treat as portal/gated until a permitted machine interface is confirmed. |

## 4. Official event and risk-evidence sources

| Event family | Starting authorities and source links | Product handling |
|---|---|---|
| Sanctions | [UN Security Council](https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list), [US OFAC Sanctions List Service](https://sanctionslist.ofac.treas.gov/Home/ConsolidatedList), [UK Sanctions List](https://www.gov.uk/government/collections/uk-sanctions), [Australia DFAT Consolidated List](https://www.dfat.gov.au/international-relations/security/sanctions/consolidated-list), [EU list portal](https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions) | Capture issuing authority, regime, listed identifier/aliases, effective dates, measures, source version, and update time. A name hit is a candidate requiring identity resolution; not a final match. |
| Financial / securities regulator enforcement | SEC (US), [FCA register and warning list](https://www.fca.org.uk/consumers/warning-list-unauthorised-firms), [MAS investor alerts](https://www.mas.gov.sg/investor-alert-list), [Japan FSA](https://www.fsa.go.jp/en/), [EU ESMA](https://www.esma.europa.eu/) and national regulator registers | Prefer published decisions, notices, and issuer records. Distinguish investigation, proposed action, final order, appeal, and withdrawal. |
| Court / litigation | [EU e-Justice portal](https://e-justice.europa.eu/sitemap_en), [US PACER](https://pacer.uscourts.gov/), national court repositories | Court records can be costly, access-controlled, incomplete, and hard to match. Record docket/court/jurisdiction and procedural posture; do not label a filing as a judgment. |
| Insolvency / dissolution | [EU insolvency registers](https://webgate.ec.europa.eu/iri/index.html), national business registers, official gazettes and insolvency services | Capture notice date, effective date, status, proceeding type, and register coverage. A dissolved/insolvent status must be tied to a specific legal entity. |
| Corporate crime / enforcement | [US DOJ Corporate Crime Case Database](https://www.justice.gov/corporate-crime/corporate-crime-case-database), national prosecution and regulator sites | Separate charge/complaint, plea, conviction, settlement, and appeal. Store the source document and named party role. |
| Product safety / recall | [EU Safety Gate](https://ec.europa.eu/safety-gate/), national product-safety regulators, [US CPSC recalls](https://www.cpsc.gov/Recalls) | Link the affected product/brand/manufacturer/importer to a legal entity only when evidence supports the connection. Preserve recall status and updates. |
| Public procurement / debarment | [World Bank sanctioned firms and individuals](https://www.worldbank.org/en/projects-operations/procurement/debarred-firms), national procurement/debarment registers, [US SAM.gov exclusions](https://sam.gov/content/exclusions) | Store authority, program, effective/expiration dates, basis, and appeal/status changes. Do not conflate a debarred affiliate with the target without a verified relationship. |
| AML jurisdiction context | [FATF public statements](https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html) | Attribute to country/jurisdiction only. Never convert the country-level classification into a negative fact about an individual business. |

## 5. Search and news sources

Search providers and reputable media can discover reports that official-source adapters have not found. They are a discovery layer, not the source of truth. For each candidate report:

1. Save publisher, canonical URL, headline, publication time, retrieval time, language, excerpt, and content hash where the license permits.
2. Determine whether the article identifies the same legal entity, an affiliate, an officer, or only a similar name.
3. Seek the underlying official filing, regulator notice, court record, company statement, or direct source.
4. Label an item `reported`, `officially alleged`, `officially determined`, `resolved`, or `unverified` as applicable; preserve updates and corrections.
5. Respect publisher robots, API terms, copyright, paywalls, and retention/republication rules. Prefer licensed feeds or metadata/link-only storage when full text reuse is not permitted.

Do not use search-engine snippets as proof of an event. Store a coverage record for each source/check and retain the exact retrieved artifact or a lawful reference to it.

## 6. Recommended hackathon source starter set

For a demo that is global in design but honest about coverage, select a small set with official machine-readable access:

1. **US identity/disclosures:** SEC EDGAR, retaining the current adapter and CIK workflow.
2. **Cross-border identity:** GLEIF LEI records and relationship reporting.
3. **Europe:** France SIRENE API for a non-US national identity source, plus BRIS as a portal discovery path and EU sanctions/insolvency sources as available.
4. **Asia-Pacific:** Singapore ACRA API Marketplace or Japan NTA Corporate Number API, subject to required registration/access approval.
5. **Global event evidence:** UN sanctions XML and official regulator/procurement notices.

The exact demo sources should be chosen based on credentials and terms actually available to the team. If no access approval exists, use permitted public sample/static files and clearly label the demo's source mode and retrieval timestamp.

## 7. Maintain this catalog as data

For each source, maintain these operational fields in a versioned `SOURCE` table or reviewed seed file:

```text
source_id, authority, jurisdiction, source_class, supported_entity_types,
supported_event_types, canonical_url, access_mode, auth_method, license_or_terms_url,
reuse_constraints, format, language, expected_refresh, rate_limit,
last_terms_reviewed_at, last_connector_test_at, status, owner, notes
```

Connector status values should distinguish `planned`, `access_requested`, `approved`, `available`, `degraded`, `paused`, and `retired`. Only `available` sources with a recent successful run should appear as currently covered.

## 8. Source research links

- Snowflake [Snowpipe Streaming](https://docs.snowflake.com/en/user-guide/snowpipe-streaming/data-load-snowpipe-streaming-overview), [Dynamic Tables decision guide](https://docs.snowflake.com/en/user-guide/dynamic-tables/decision-guide), [Cortex Search](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview), and [Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents).
- Primary links in this catalog were checked on 2026-10-01. Portals, access policy, API availability, and terms can change; connector implementation requires a fresh source-by-source check.
