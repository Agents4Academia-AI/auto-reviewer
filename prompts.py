"""Prompt templates for each stage of the reviewer pipeline.

Each STAGE_*_PROMPT is the user-turn instruction. The paper PDF is attached
separately as a cached document block (see llm_client.build_user_content).
Stages take the prior stages' structured outputs as context.
"""

REVIEWER_SYSTEM = """You are an expert peer reviewer for top-tier deep learning conferences (NeurIPS, ICML, ICLR, CVPR, ACL).

You are rigorous, fair, and grounded in evidence from the paper itself. You distinguish factual issues from subjective judgments, separate fatal flaws from minor issues, and avoid vague criticism.

When asked, respond with valid JSON only. Do not wrap JSON in markdown fences. Do not add commentary before or after the JSON object.
"""


STAGE_0_PARSE = """Stage 0 — Structured paper parsing.

Read the attached paper and extract a structured representation.

Return JSON with this schema:
{
  "title": "...",
  "authors": ["..."] or [],
  "venue_hint": "guessed venue / category, or null",
  "paper_date": "submission / arXiv / publication date if stated, otherwise null",
  "field": "subfield of deep learning",
  "abstract": "...",
  "sections": {
    "introduction": "1-2 paragraph summary",
    "related_work": "...",
    "method": "...",
    "theory": "... or null",
    "experiments": "...",
    "results": "...",
    "limitations": "... or null",
    "conclusion": "..."
  },
  "main_claims": ["claim 1", "claim 2", ...],
  "key_contributions": ["..."],
  "experimental_results": ["concise summary of each key result"],
  "assumptions_and_limitations": ["..."],
  "figures_tables": ["short descriptions of important figures/tables"],
  "equations_algorithms": ["short descriptions of important equations/algorithms"]
}
"""


STAGE_1_OVERALL = """Stage 1 — Overall understanding.

Using the structured representation, produce a high-level understanding before passing judgment.

Return JSON:
{
  "field_and_subfield": "...",
  "problem_addressed": "...",
  "research_question": "...",
  "one_paragraph_summary": "...",
  "problem_statement": "...",
  "main_contributions": ["..."],
  "claim_evidence_map": [
    {"claim": "...", "evidence_in_paper": "..."}
  ]
}

Prior context (Stage 0 structured paper):
{stage_0}
"""


STAGE_2_SECTIONS = """Stage 2 — Section-level analysis.

For each major section, analyze clarity, completeness, internal consistency, and flag any unclear definitions, missing assumptions, weak arguments, or unsupported statements.

Return JSON:
{
  "sections": [
    {
      "name": "Abstract | Introduction | Related Work | Method | Theory | Experiments | Results | Limitations | Conclusion | Supplementary",
      "summary": "...",
      "key_claims": ["..."],
      "supporting_evidence": ["..."],
      "issues": ["..."],
      "missing_information": ["..."],
      "ambiguous_or_unsupported": ["..."]
    }
  ]
}

Prior context (Stage 0):
{stage_0}
"""


STAGE_3_CLAIMS = """Stage 3 — Claim extraction and evidence mapping.

Extract all major claims and categorize each. For every claim, identify the evidence and rate it.

Return JSON:
{
  "claims": [
    {
      "claim": "...",
      "category": "novelty | technical_correctness | empirical_performance | theoretical | practical_impact | generalization",
      "evidence_in_paper": "...",
      "evidence_strength": "strong | weak | missing | irrelevant",
      "notes": "..."
    }
  ],
  "unsupported_claims": ["..."],
  "overstated_claims": ["..."],
  "claims_requiring_external_verification": ["..."]
}

Prior context (Stage 1):
{stage_1}
"""


STAGE_4_NOVELTY = """Stage 4 — Novelty check.

Judge whether the work is genuinely new compared with prior work in deep learning. Do not collapse the paper into a single "is it novel?" verdict — a paper can be novel on one axis (e.g., method) while derivative on another (e.g., problem framing). Decompose first, then search, then judge.
Review date: {review_date}.

First infer the paper's own date from the attached PDF or prior context: use a submission date, arXiv first-posted date, camera-ready/publication date, or version date if one is stated. 
If no paper date is inferable, use the review date above as the cutoff and say so.

Novelty must be judged against work available on or before the cutoff date. Do not penalize the paper's novelty for papers, blog posts, code releases, or benchmarks that appeared after the cutoff. 
Put post-cutoff or clearly concurrent work in a separate context list and use it only to calibrate importance, adoption, or how the field evolved. 
If a related work is concurrent or has uncertain timing, mark it explicitly as "concurrent_or_uncertain" and do not treat it as definitive prior art.

You have a web search tool. You MUST actually run searches before judging novelty — do not answer from your own knowledge. Use it to look up the most relevant prior work on arXiv, OpenReview, Papers With Code, and venue proceedings. Prefer sources with dates and URLs. Compare against the closest matches. Set `source_of_judgment` to "web_search" only after you have executed at least one search.
Only if every search attempt fails should you fall back to your own knowledge, and then mark conclusions as "from-model-knowledge" so reviewers can verify.

STEP 1 — Decompose into novelty axes.
From the paper's contributions and claims, identify the distinct axes on which the paper might claim novelty. Use only the axes that actually apply. Candidate axes:
- problem / task formulation (a new problem, setting, or framing)
- method / architecture (a new model, module, mechanism, or algorithm)
- theory (a new analysis, bound, guarantee, or proof technique)
- training / optimization (a new objective, regularizer, or training procedure)
- data / benchmark (a new dataset, benchmark, or evaluation protocol)
- empirical finding (a new result, phenomenon, or state-of-the-art claim)
- application domain (applying known techniques to a new domain)

STEP 2 — For each axis, formulate targeted searches.
Write specific search keywords and a precise search question per axis. Avoid generic queries (e.g., "deep learning attention"); name the specific mechanism, problem, or claim.

EXEMPLAR (for a paper proposing a self-attention-only sequence model):
- axis: "method / architecture"
  why_it_matters: "The core contribution is replacing recurrence/convolution entirely with attention; novelty hinges on whether prior models already did this."
  search_keywords: ["attention without recurrence sequence model", "self-attention only encoder decoder", "attention replace convolution translation"]
  search_question: "Did any prior work build a sequence transduction model using only attention, with no recurrent or convolutional layers?"
- axis: "empirical finding"
  why_it_matters: "Claims SOTA on WMT translation; novelty of the result depends on the prior SOTA."
  search_keywords: ["WMT 2014 English-German BLEU state of the art", "machine translation BLEU benchmark 2017"]
  search_question: "What was the best published BLEU on WMT14 EN-DE before this work, and by which model?"

STEP 3 — Search (multi-round). You have a web search tool — use it; do not skip this step.
Run the per-axis queries against arXiv, OpenReview, Papers With Code, Semantic Scholar / Google Scholar, and venue proceedings. Do at least one refinement round: after the first results, tighten queries toward the closest matches you found (chase the specific competing method by name, check its citations). Record the exact queries you actually ran in `novelty_axes_searched`.

Only if every search attempt fails should you rely on your own knowledge and set `source_of_judgment` to "model_knowledge" so reviewers know conclusions are unverified.

STEP 4 — Compare against closest prior work.
For each axis, identify the closest prior work and state precisely what this paper does that the prior work does not (or why it is in fact subsumed). Record the FULL bibliographic entry + difference ONCE in `similar_prior_work` at the bottom of the JSON. In each `novelty_axes` entry, reference that prior work by a SHORT pointer (e.g., `"Parikh 2016 [similar_prior_work #1]"`) — do not repeat title/venue/diff text inside the axis. This keeps the output single-source for any downstream stage that consumes prior-work details.

STEP 5 — Judge per axis, then overall.
Give a per-axis verdict, then synthesize ONE overall assessment in `rationale`. Be concrete about what is genuinely new versus repackaged.



Return JSON:
{
  "cutoff_date": "YYYY-MM-DD or best-effort date string",
  "cutoff_basis": "paper_submission | arxiv_first_posted | publication | paper_version | review_date_fallback | uncertain",
  "novelty_axes": [
    {
      "axis": "problem | method | theory | training | data | empirical | application",
      "claimed_contribution": "what the paper claims is new on this axis",
      "why_it_matters": "why novelty on this axis is load-bearing for the paper",
      "search_keywords": ["..."],
      "search_question": "...",
      "closest_prior_work_ref": "short pointer into similar_prior_work, e.g. 'Parikh 2016 [similar_prior_work #1]' or 'none found' — do NOT duplicate full bibliographic details or the diff here",
      "axis_verdict": "novel | incremental | derivative"
    }
  ],
  "novelty_axes_searched": ["exact query strings actually run, in order; empty list if no search tool"],
  "similar_prior_work": [
    {"title": "...", "venue_or_source": "...", "year": "...", "date_relation_to_cutoff": "before_cutoff | after_cutoff | concurrent_or_uncertain", "similarity_summary": "...", "key_difference": "..."}
  ],
  "post_cutoff_or_concurrent_context": [
    {"title": "...", "venue_or_source": "...", "year": "...", "date_relation_to_cutoff": "after_cutoff | concurrent_or_uncertain", "why_not_used_as_prior_art": "..."}
  ],
  "novelty_type": "conceptual | technical | empirical | theoretical | application_driven | none",
  "novelty_assessment": "strong | moderate | incremental | derivative",
  "novelty_risk_level": "low | medium | high",
  "incrementality_judgment": "...",
  "rationale": "Explain the novelty judgment using only before-cutoff prior work; separately mention any post-cutoff/concurrent context without penalizing the paper.",
  "source_of_judgment": "web_search | model_knowledge"
}

Prior context (Stage 0 structured paper):
{stage_0}

Prior context (Stage 3 claims):
{stage_3}

"""


STAGE_5_SIGNIFICANCE = """Stage 5 — Significance and impact analysis (multi-perspective).

Adopt FIVE specialized personas in turn and have each independently answer the questions. Then synthesize consensus and disagreement.

Personas:
- domain_expert
- methodology_expert
- empirical_evaluation_expert
- skeptical_reviewer
- practical_impact_expert

For each persona, address:
1. What does this work add to the field?
2. Who would benefit from it?
3. Does it solve an important problem?
4. Is the improvement meaningful?
5. Could the idea influence future work?

Separate effect size from evidence certainty. If reported improvements are
large or practically important, say so directly even when there are limitations
such as missing seeds, imperfect baselines, or restricted settings. Criticize
the strength of evidence separately from the magnitude of the claimed gains.
Do not describe substantial empirical gains as "marginal" merely because the
paper needs more ablations, variance reporting, or baseline coverage.

Return JSON:
{
  "perspectives": {
    "domain_expert": {"add_to_field": "...", "beneficiaries": "...", "importance": "...", "improvement_meaningful": "...", "future_influence": "..."},
    "methodology_expert": { ... same keys ... },
    "empirical_evaluation_expert": { ... },
    "skeptical_reviewer": { ... },
    "practical_impact_expert": { ... }
  },
  "consensus": ["..."],
  "disagreement": ["..."],
  "significance_score_1_to_10": 0,
  "impact_assessment": "low | moderate | high | transformative"
}

Prior context (Stage 1 summary):
{stage_1}
"""


STAGE_6_RIGOR = """Stage 6 - Rigor check.

Evaluate four dimensions:
(A) Problem and solution formulation: for each major problem, check whether definitions are clear, whether assumptions are made clear, whether derivations and algorithms are clear.
(B) Theoretical support: if theoretical claims are made, for each major theoretical claim, decide whether the statement and proof is correct.
(C) Experimental support: if experimental support is provided, for each major claim, decide if it is supported, partially supported, or unsupported by the experiments. Consider experimental procedures, hidden assumptions, possible failure cases, reproducibility.
(D) Experimental rigor: if experimental support is provided, check the rigor in the use of baselines, datasets, metrics, ablations, statistical significance / uncertainty, hyperparameters, negative results, confounders.

When judging experiments, keep these concepts separate:
- effect magnitude: how large, consistent, or practically meaningful the reported gains are;
- evidence strength: whether the experimental design, baselines, seeds, and statistics justify the claim;
- claim scope: the conditions under which the result is valid.

Do not collapse a large conditional improvement into "marginal" because of
missing error bars or incomplete baselines. Instead say "large but currently
conditioned on ..." or "substantial effect with limited statistical support".

Return JSON:
{
  "problem_and_solution_formulation": {
    "definitions_clear": ["..."],
    "assumptions_clear": ["..."],
    "derivations_algorithms_clear": ["..."]
    "suggested_improvements_for_formulation": ["..."] or [],
  },
  "theoretical_support": {
    "correct": ["..."],
    "partially_correct": ["..."],
    "suggested_improvements_for_theoretical_support": ["..."] or [],
  } or null,
  "experimental_support": {
    "supported": ["..."],
    "partially_supported": ["..."],
    "unsupported_or_overstated": ["..."],
    "effect_size_assessment": ["large/substantial/modest/marginal effect, with the conditions under which that label is justified"],
    "suggested_improvements_for_claim_support": ["..."] or [],
  } or null,
  "experimental_rigor": {
    "baseline_quality": "...",
    "missing_baselines": ["..."],
    "dataset_quality": "...",
    "better_datasets": ["..."] or [],
    "metric_appropriateness": "...",
    "better_metric": ["..."] or []
    "missing_ablations": ["..."],
    "statistical_significance": "...",
    "better_significance_test_or_confidence_interval": ["..."] or [],
    "hyperparameter_clarity": "...",
    "negative_results_discussed": "yes | no | partial",
    "possible_confounders": ["..."],
    "confounder_reduction_alternatives": ["..."] or [],
    "reproducibility_score_1_to_10": 0,
    "suggestions_for_improving_reproducibility": ["..."] or []
  } or null 
}

Prior context (Stage 3 claims, Stage 2 sections):
Stage 3 claims:
{stage_3}

Stage 2 sections:
{stage_2}
"""


STAGE_7_PLAN = """Stage 7 — Review planning.

Synthesize a coherent reviewer perspective from all prior stages.

Recommendation calibration:
- Reward substantial, well-supported, practically meaningful results even when
  the paper has fixable rigor gaps.
- Penalize overclaiming by narrowing the claim scope, not by pretending large
  reported effects are small.
- Separate "result is strong under stated conditions" from "evidence is not yet
  complete enough for a stronger recommendation".

Return JSON:
{
  "strengths": ["..."],
  "weaknesses": ["..."],
  "fatal_flaws": ["..." or empty list],
  "minor_issues": ["..."],
  "questions_for_authors": ["..."],
  "recommendation": "strong_accept | accept | weak_accept | borderline | weak_reject | reject | strong_reject",
  "recommendation_rationale": "...",
  "confidence_1_to_5": 0
}

Prior context (Stages 1, 3, 5, 6):
Stage 1: {stage_1}
Stage 3: {stage_3}
Stage 5: {stage_5}
Stage 6: {stage_6}
"""


STAGE_8_DRAFT = """Stage 8 — Draft review (author-facing).

Generate a structured peer review for the authors. Be specific and evidence-based. Avoid vague criticism. Separate factual issues from subjective judgments. Be constructive and respectful. Mention both positive and negative aspects.
When discussing experiments, distinguish effect size from evidence certainty:
large conditional gains should be described as large conditional gains, with
limitations stated separately.

Return JSON:
{
  "summary_of_paper": "1-2 paragraphs",
  "main_strengths": ["..."],
  "main_weaknesses": ["..."],
  "detailed_comments": ["..."],
  "questions_for_authors": ["..."],
  "suggestions_for_improvement": ["..."],
  "overall_recommendation": "...",
  "reviewer_confidence_1_to_5": 0,
  "score_card": {
    "soundness_1_to_4": 0,
    "presentation_1_to_4": 0,
    "contribution_1_to_4": 0,
    "overall_1_to_10": 0
  }
}

Prior context (Stage 7 plan, Stage 1 summary):
Stage 7: {stage_7}
Stage 1: {stage_1}
"""


STAGE_9_CRITIQUE = """Stage 9 — Self-critique and verification.

Audit the draft review. Verify every criticism against the paper. Check whether the review misrepresents the authors' claims, missed important strengths/weaknesses, has hallucinations, makes too-strong claims, or has an inconsistent recommendation.

Return JSON:
{
  "hallucinated_comments": ["..."],
  "misrepresentations": ["..."],
  "missed_strengths": ["..."],
  "missed_weaknesses": ["..."],
  "too_strong_claims": ["..."],
  "non_actionable_criticisms": ["..."],
  "tone_issues": ["..."],
  "consistency_between_summary_weaknesses_and_recommendation": "consistent | inconsistent",
  "external_novelty_claims_supported": "yes | partial | no | n/a",
  "corrections_needed": ["specific correction items the next stage must apply"]
}

Prior context (Stage 8 draft):
{stage_8}
"""


STAGE_10_FINAL = """Stage 10 — Finalization.

Apply the corrections from the self-critique. Remove unsupported criticism, clarify vague comments, strengthen evidence-based reasoning, and ensure consistency between summary, weaknesses, score, and recommendation.
Before finalizing, check that the review does not call substantial empirical
effects "marginal" merely because the evidence has limitations. If a result is
large but conditionally supported, say exactly that and scope the claim.

Return JSON:
{
  "final_review": {
    "summary_of_paper": "...",
    "main_strengths": ["..."],
    "main_weaknesses": ["..."],
    "detailed_comments": ["..."],
    "questions_for_authors": ["..."],
    "suggestions_for_improvement": ["..."],
    "overall_recommendation": "...",
    "reviewer_confidence_1_to_5": 0,
    "score_card": {
      "soundness_1_to_4": 0,
      "presentation_1_to_4": 0,
      "contribution_1_to_4": 0,
      "overall_1_to_10": 0
    }
  },
  "author_facing_improvement_checklist": ["..."],
  "changes_from_draft": ["..."]
}

Prior context:
Stage 8 draft: {stage_8}
Stage 9 critique: {stage_9}
"""

