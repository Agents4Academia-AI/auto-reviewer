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

Judge whether the work is genuinely new compared with prior work in deep learning.

If you have access to a web search tool, use it to look up the most relevant prior work on arXiv, OpenReview, Papers With Code, and venue proceedings. Compare against the closest matches.

If no search tool is available, rely on your own knowledge but mark conclusions as "from-model-knowledge" so reviewers can verify.

Return JSON:
{
  "similar_prior_work": [
    {"title": "...", "venue_or_source": "...", "year": "...", "similarity_summary": "...", "key_difference": "..."}
  ],
  "potential_missing_citations": ["..."],
  "novelty_type": "conceptual | technical | empirical | theoretical | application_driven | none",
  "novelty_assessment": "strong | moderate | incremental | derivative",
  "novelty_risk_level": "low | medium | high",
  "incrementality_judgment": "...",
  "rationale": "...",
  "source_of_judgment": "web_search | model_knowledge"
}

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


