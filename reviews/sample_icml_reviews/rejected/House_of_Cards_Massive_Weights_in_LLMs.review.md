# Reviewer Agent Report
**Paper file:** `House_of_Cards_Massive_Weights_in_LLMs.pdf`  **Generated:** 2026-06-21T16:03:38.715339Z
---
## Summary of the Paper
The paper extends prior work on massive activations and attention sinks in LLMs by tracing their origin to the intermediate state of an early-layer feed-forward network (FFN). The authors define 'top-k massive weights' as the rows of W_up and W_gate at this specific layer whose outputs produce the top-k magnitudes of the intermediate state when probed with the bos token. They show via two opposing attacks (top-k zeroing vs. top-k retaining) that this tiny set of weights (~0.0005% of parameters in Llama-3-8B) dominates model functionality in Llama-2/3/3.1, Mistral, Mixtral, and Phi-3-mini families, while Gemma-2 (extra LN) and Phi-3-medium (residual dropout) are robust. Building on this, they propose MacDrop, a curriculum dropout applied to pre-trained massive-weight rows during LoRA/DoRA fine-tuning, with the dropout probability decaying from a high initial value to zero by the end of training. MacDrop is evaluated on zero-shot tasks, LongBench, and Spec-Bench generation across multiple model families. It yields modest improvements on zero-shot tasks (typically 0.3–0.9 points on the average), mixed improvements on LongBench, and large robustness gains when the resulting fine-tuned models are subjected to the authors' own top-k zeroing attack. The method does not help families that lack the massive-activation phenomenon (Gemma-2, Phi-3-medium), which the authors transparently report.
## Recommendation
**Borderline. The analysis contribution (localizing massive activations to specific FFN rows and demonstrating their outsized influence) is interesting and well-executed, but conceptually incremental over Sun et al. (2024a) and concurrent 'super weight' work. The proposed MacDrop method shows only modest clean-task gains without statistical reporting, and the most dramatic robustness gains defend against the authors' own attack. Lean reject in current form; would lean accept with the requested random-row baseline, multi-seed reporting, and robustness evaluation against non-zeroing perturbations.**  (confidence 4/5)
### Score Card
- Soundness: 2/4
- Presentation: 3/4
- Contribution: 2/4
- Overall: 5/10
### Main Strengths
- Clean and reproducible localization of massive activations to specific rows of W_up and W_gate at a single early FFN layer, refining the activation-level findings of Sun et al. (2024a).
- Broad empirical coverage across many LLM families (Llama-2/3/3.1 up to 405B, Mistral, Mixtral, Phi-3, Gemma-2), including informative negative cases where the phenomenon does not occur.
- Two complementary attacks (top-k zeroing vs. top-k retaining) provide striking, well-presented evidence that ~0.0005% of parameters dominate functionality in vulnerable families.
- Novel observation (Figure 5) that in Mixtral's MoE architecture, the layer containing massive weights exhibits highly skewed router probabilities concentrating on a single expert — an interesting connection between massive activations and expert routing.
- Operationally simple bos-token probe for identifying critical weights, with thorough Appendix C documentation of per-family caveats and Appendix D per-family visualizations that aid reproducibility.
- MacDrop is simple, plug-and-play, with low overhead (~0.35s/step) and clear pseudo-code; ablations cover scope, probability, and curriculum schedule.
- Architectural attribution (extra LN in Gemma-2, residual dropout in Phi-3-medium) provides actionable design insight, even if not causally tested.
- Honest reporting of limitations: MacDrop fails on Gemma-2 and Phi-3-medium and shows only marginal gains on generation tasks; the authors do not overclaim.

### Main Weaknesses
- Conceptual novelty over Sun et al. (2024a) and concurrent Yu et al. (2024a) 'super weight' work is incremental. Moreover, the definition of massive weights as 'rows of W_up and W_gate producing the top-k output magnitudes' is partly tautological given prior characterization of massive-activation feature dimensions: the row index is, by construction, the same as the feature-dimension index identified by prior work.
- MacDrop's clean-task improvements are small (typically 0.3–0.9 points on zero-shot averages) and reported with no multi-seed runs, error bars, or significance tests, making it difficult to assess whether gains are statistically meaningful.
- The most dramatic results (robustness in Table 4) defend specifically against the authors' own attack; no other perturbation types (random noise, quantization, adversarial weight perturbations) are evaluated, making the robustness claim partially circular.
- A critical baseline is missing: dropout on a random row subset of W_up/W_gate matched in element count to massive weights. Without this, target specificity cannot be distinguished from generic regularization at the same layer.
- No empirical comparison or overlap analysis with related weight-importance methods (Wanda, AWQ), despite Appendix H discussing their conceptual relationship.
- The claim that massive weights are 'predominantly learned during pre-training' is interpretive: only post-hoc attack asymmetry is shown, with no training-dynamics or gradient-trajectory evidence.
- Architectural attribution of robustness (extra LN, residual dropout) is plausible but not causally tested via controlled training experiments.
- Layer l and Mixtral expert selection rely on post-hoc visual inspection of magnitude plots and bos-token routing only; an algorithmic selection criterion and alternative calibration procedures are not validated.
- MacDrop is restricted to dropping weights in a single layer l; multi-layer variants or sensitivity to the layer choice are not explored.
- Aggregate LongBench gains are small and per-subtask results are mixed; Spec-Bench (Appendix G) shows essentially flat performance. The abstract framing of 'generally improves performance' is somewhat stronger than the evidence supports.
- The 'house of cards' threat model assumes white-box weight access plus surgical zeroing, which is non-standard and limits the practical urgency of the robustness contribution.

### Detailed Comments
- Section 2.2 / Figure 3: The decomposition tracing massive activations to FFN(LN(ĥ_2)) → h_2 is convincing for Llama-3-8B, and Appendix D extends this nicely across families. However, the procedure for selecting the specific layer l is implicit (visual inspection of the top-3 magnitudes). An algorithmic criterion (e.g., layer with maximum intermediate-state max/median ratio above a threshold) would make the work more reproducible.
- Section 2.3 / Table 1: The contrast between top-5 zeroing and top-5 retaining is the paper's strongest empirical result and is well-framed. It would be even more compelling with a 'random-5 retaining' baseline (keep 5 random rows, zero the rest) to confirm that the 5 specific rows, rather than any 5 rows, are sufficient to preserve some functionality.
- Section 2.3 / Figure 4: The robustness curves across families are very informative. Adding a control where the same number of weights are zeroed at non-massive layers would strengthen the claim that the layer-specific localization is what matters.
- Section 3 / Algorithm 1: Could the authors clarify whether the dropout uses inverted scaling (multiplying surviving weights by 1/(1-p))? Weight-level dropout (DropConnect-style) often omits inverted scaling, but a brief discussion of the chosen convention and its effect on intermediate-state magnitudes during training vs. inference would aid reproducibility.
- Section 4.1 / Tables 3 and 4: The clean-task improvements are modest, while the under-attack robustness gains are large. Because the attack is the very phenomenon MacDrop is designed to mitigate, the robustness contribution is somewhat circular. Robustness to other perturbation types (Gaussian weight noise of matched norm, low-bit quantization, gradient-based adversarial perturbations) would meaningfully strengthen the case.
- Section 4.2 / Table 2: LongBench gains are uneven across subtasks (e.g., large improvements on TriviaQA and Musique, but drops on NrtvQA and PCount). It would be useful to discuss why MacDrop helps disproportionately on certain task types.
- Section 4.3 / Table 5: Differences across curriculum schedules are small (~1 point), yet specific recommendations (Step or Exp with small α from moderately high p_0) are made. Multi-seed experiments or statistical tests would strengthen these recommendations.
- Appendix F / Table 8: The honest reporting that MacDrop does not help Gemma-2 / Phi-3-medium is appreciated, but it raises the question of whether MacDrop is best understood as a fix for a specific family of architectures rather than a general PEFT improvement.
- Appendix G: The Spec-Bench results (Table 9) show essentially flat performance with MacDrop. This should be reflected more clearly in the abstract/intro framing.
- Appendix H: The discussion of the relationship to Wanda, AWQ, and 'super weight' is helpful, but a quantitative overlap analysis (do top-k massive weight rows fall within the top-X% of Wanda or AWQ importance scores?) would situate the contribution more concretely.

### Questions for Authors
- How does MacDrop compare against a control where dropout is applied to a random row subset of equal size in W_up / W_gate at the same layer l? This is essential to isolate target specificity from generic regularization.
- Can you report multi-seed runs with confidence intervals or paired significance tests for Tables 2, 3, 4, and 5?
- Does MacDrop improve robustness against attacks other than top-k zeroing (e.g., random Gaussian weight perturbations of matched norm, low-bit quantization, adversarial weight perturbations)?
- What is the empirical overlap between top-k massive weight rows and weights selected by Wanda or AWQ in the same projection matrices?
- Is dropout applied with inverted scaling (mask / (1-p))? If not, how do you address the activation-magnitude shift this introduces during training versus inference?
- How are the identified massive-weight indices affected if probing uses calibration inputs other than the bos token alone (e.g., a small natural-text corpus or multiple delimiter tokens)?
- What evidence supports the claim that massive weights are 'predominantly learned during pre-training'? Have you traced the magnitude trajectory of these weights during a smaller-scale pre-training run?
- How is layer l selected algorithmically? Is the selection stable across pre-trained vs instruction-tuned checkpoints of the same model?
- Why are the Mixtral attacks restricted to expert 4? Do results change when routing is analyzed using diverse content tokens rather than just bos?
- Have you considered applying MacDrop to multiple candidate layers, or analyzed sensitivity to misidentification of layer l?
- Can you provide a controlled experiment (e.g., re-training a small Llama-like model with extra LN or residual dropout) to causally test the architectural attribution for Gemma-2 / Phi-3-medium robustness?
- After fine-tuning (with and without MacDrop), do the identified massive-weight indices remain the same, or shift? This would help interpret what MacDrop is doing mechanistically.

### Suggestions for Improvement
- Add a random-row-dropout baseline matched in element count to massive weights to establish target specificity; this is the single most important experiment to add.
- Report multi-seed averages with standard deviations or 95% CIs for all main tables (2, 3, 4, 5); add paired significance tests for comparisons claiming improvement.
- Evaluate MacDrop's robustness against non-zeroing perturbations (Gaussian noise, low-bit quantization, adversarial weight perturbations) to demonstrate that gains generalize beyond the self-designed attack.
- Add a quantitative comparison/overlap analysis with Wanda and AWQ on the same projection matrices.
- Clarify the dropout scaling convention in Algorithm 1 and discuss any activation-magnitude shift between training and inference.
- Provide an algorithmic procedure for selecting layer l rather than visual inspection, and validate that the bos-only probe agrees with multi-token calibration probes.
- Soften the abstract/intro framing about 'generally improves performance' to reflect that improvements are modest, mixed on LongBench/Spec-Bench, and absent on Gemma-2 / Phi-3-medium.
- Consider a controlled small-scale retraining experiment to causally test whether adding LN or residual dropout suppresses massive-weight formation.
- Add an ablation over k (the number of dropped massive-weight rows) and over the choice of probing input, as well as over applying MacDrop to multiple layers.
- Move the threat-model framing ('house of cards') into context: discuss when white-box weight-level attacks are realistic, and contrast with practical settings.

### Improvement Checklist
- Add a random-row dropout baseline (same element count, same layer l) to isolate target specificity of MacDrop.
- Run multi-seed experiments and report means ± std (or 95% CI) for all main tables; add paired significance tests for headline claims.
- Evaluate robustness under perturbations other than top-k zeroing: matched-norm Gaussian weight noise, low-bit quantization, and gradient-based weight perturbations.
- Quantitatively compare massive-weight identification to Wanda and AWQ importance rankings on the same matrices (overlap analysis).
- Clarify the dropout scaling convention used in Algorithm 1 and discuss training/inference magnitude consistency.
- Provide an algorithmic, threshold-based criterion for selecting layer l and validate stability of the bos-only probe against multi-token calibration sets.
- Soften abstract/intro language about generalized performance gains to match the mixed LongBench and flat Spec-Bench results.
- Add ablations over k, over the probing input, and over applying MacDrop at multiple candidate layers.
- Consider controlled small-scale retraining to causally test the architectural attribution (extra LN, residual dropout) for Gemma-2 / Phi-3-medium robustness.
- Discuss the realism of the white-box surgical-zeroing threat model to contextualize the robustness contribution.
- Report whether identified massive-weight indices shift after fine-tuning, with and without MacDrop.

