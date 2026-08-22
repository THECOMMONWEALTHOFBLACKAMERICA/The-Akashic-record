# T.A.R. Human Interpretation Protocol

**Protocol version:** 0.1.0  
**Purpose:** Train and evaluate AI systems to reason about longitudinal human records without pretending that narrative coherence is psychological ground truth.

## Design rule

T.A.R. stores three separate layers:

1. **Observation** — what was actually recorded, observed, submitted, completed, corrected, or testified to.
2. **Interpretation** — what a human or model thinks the observation means.
3. **Revision history** — what changed when new evidence, contradiction, or direct human correction arrived.

The protocol evaluates the quality of an interpretation. It does **not** assign intelligence, personality, diagnosis, moral worth, or clinical scores to a person.

## Core principles

- Keep a revisable model of the human.
- Evidence outranks narrative.
- Track project stage instead of equating unfinished work with unserious work.
- Use the evidentiary contract appropriate to the domain.
- Distinguish AI creation from amplification or scaffolding.
- Preserve contradiction rather than forcing a clean personality theory.
- Treat long-term AI as part of the environment, not a neutral observer.
- Prefer increasing human agency and skill transfer over dependency.
- Treat direct human corrections as high-value revision data.
- Never substitute model confidence or fluent prose for evidence.

## Evidence kinds

The reference implementation uses transparent heuristic weights to identify overclaiming. They are not scientific validity coefficients.

| Kind | Reference weight |
|---|---:|
| primary_record | 1.00 |
| direct_observation | 0.90 |
| human_correction | 0.90 |
| corroborated_testimony | 0.85 |
| artifact | 0.80 |
| direct_testimony | 0.75 |
| self_report | 0.65 |
| model_output | 0.35 |
| narrative_inference | 0.25 |
| unknown | 0.20 |

Each evidence item also carries a 0–1 source confidence and a stance: `supports`, `contradicts`, or `context`. Multiple evidence items combine with a saturating function so duplicated weak evidence cannot grow without bound.

## Epistemic statuses

Claims are returned as one of:

- `unsupported`
- `tentative`
- `supported`
- `well_supported`
- `contested`
- `contradicted`

Direct corrections and unresolved contradictions are preserved in output. They are never silently merged away.

## AI influence field

A claim may describe AI's role as:

- `created`
- `amplified`
- `scaffolded`
- `unknown`

If a claim says AI **created** a trait while the record contains a pre-AI baseline for that same trait, the evaluator flags the causality claim for revision. This does not prove amplification; it only prevents an unsupported creation claim.

## Human agency check

The optional agency check records workflow signals such as whether the human originated the goal, retained the final decision, can explain the work without AI, can detect model errors, and has internalized skills. Risk signals include adopting AI-originated goals without independent endorsement, being unable to proceed without AI, or accepting output without verification.

The resulting score is explicitly labeled a **heuristic workflow signal**, not a psychological or clinical measurement.

## API

All endpoints inherit the existing T.A.R. workspace isolation and identity model.

- `GET /v1/interpretation/principles`
- `POST /v1/interpretation/evaluate`
- `POST /v1/interpretation/training-example`
- `POST /v1/interpretation/cases`
- `GET /v1/interpretation/cases`
- `GET /v1/interpretation/cases/{case_id}`

### Minimal evaluation request

```json
{
  "title": "Pre-AI creativity baseline",
  "subject_ref": "anonymous-subject-001",
  "claims": [
    {
      "statement": "AI created the subject's creativity.",
      "layer": "interpretation",
      "declared_confidence": 0.9,
      "evidence": [
        {
          "kind": "direct_testimony",
          "stance": "contradicts",
          "summary": "A long-term witness reports creativity and large imaginative ideas before sustained AI use.",
          "confidence": 0.95
        }
      ],
      "human_corrections": ["Creativity predates sustained AI use."],
      "influence": {"ai_role": "created", "pre_ai_baseline": true}
    }
  ]
}
```

The evaluator should flag the AI-creation claim, preserve the contradiction, and require revision rather than replacing it with a flattering alternative explanation.

## Training export

`POST /v1/interpretation/training-example` produces a structured example containing:

- protocol instruction,
- principles,
- original case input,
- deterministic expected checks.

That format can seed supervised examples, regression tests, model-to-model evaluations, or future human review. It is designed to teach *epistemic behavior*, not a preferred biography of any one subject.
