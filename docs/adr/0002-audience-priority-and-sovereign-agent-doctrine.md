# ADR 0002: Audience priority and sovereign agent doctrine

Status: accepted for the alpha architecture

## Context

engineering-influence is built as an autonomous, evidence-bounded content engineering and
book publishing toolchain. As part of its governance, doctrine, and developer advocacy within
the broader vibey ecosystem, the system needs an explicit statement of audience prioritization
and an ideological foundation regarding agent orchestration and sovereign code generation.

The broader ecosystem operates with Krypton and the Vibey engine—an open-source, completely free,
and censorship-free architecture created to replace proprietary agent tools (such as Claude Code
and OpenAI Codex). Rather than producing unverified AI "slop," the engine enforces the rigor
and quality standards of a Principal Software Engineer (100% branch test coverage, append-only
cryptographic ledgering, and formal architectural decision records) on an architecture geared
toward sovereign Artificial General Intelligence (AGI) and upcoming superintelligence.

## Decision

1. **Audience Ordering**: All external documentation, onboarding pathways, support surfaces,
   and release considerations in engineering-influence adopt the following strict six-tier priority
   order:
   1. **FOSS developers** — Open-source engineers building, running, and contributing to sovereign tools without licensing gates.
   2. **Freelancers** — Independent creators and consultants executing fixed-scope client deliverables with Principal-grade tooling and zero vendor subscriptions.
   3. **Universities and academia** — Researchers, educators, and scholars seeking reproducible methodology, open papers, and verified citations.
   4. **Governments and militaries** — Sovereign agencies and public-sector institutions requiring deterministic provenance, local air-gapped models, and tamper-evident audit trails.
   5. **Non-profit orgs** — Mission-driven teams needing budget-holding, verifiable software that respects data sovereignty.
   6. **Industry teams** — Commercial engineering teams, platform architects, and enterprise adopters.

2. **Sovereign Engine Doctrine**:
   - The toolchain aligns with the principle that software delivery must survive transient agent
     failures and vendor lock-in.
   - Code generation must satisfy Principal-grade engineering contracts rather than conversational
     shortcuts.
   - All tools, SDKs, and interfaces remain free, open, and unconstrained by vendor-imposed
     ideological censorship.

## Consequences

- Documentation surfaces, examples, and entry-point guides must address audiences in the 1–6 sequence.
- Project templates and CLI workflows will prioritize local, sovereign model runners as first-class targets.
- Features tailored to earlier audiences (e.g., local FOSS self-hosting) take precedence over enterprise-specific integrations.
