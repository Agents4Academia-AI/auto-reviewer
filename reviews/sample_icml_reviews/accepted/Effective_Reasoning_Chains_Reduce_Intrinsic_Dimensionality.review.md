# Reviewer Agent Report
**Paper file:** `Effective_Reasoning_Chains_Reduce_Intrinsic_Dimensionality.pdf`  **Generated:** 2026-06-21T16:04:00.037829Z
---
## Summary of the Paper
The paper proposes intrinsic dimensionality—operationalized as the minimum number of LoRA-trainable parameters needed to reach a fixed training-accuracy threshold—as a quantitative predictor of how well a chain-of-thought (CoT) reasoning strategy will generalize when used as fine-tuning supervision. Departing from prior intrinsic-dimension work that varies the model with fixed data, the authors fix the base model (Gemma-3 1B and 4B) and vary the reasoning-chain format across 14 strategies (No CoT, Short/Very Short CoT, distractor-injected CoT, Executed/Simulated PoT, Plan-and-Solve, Critical CoT, High-Review-Ratio CoT, Gemini/Gemma teacher CoT, etc.) applied to the same GSM8K questions.

On GSM8K and five OOD math stress tests, intrinsic dimensionality shows a strong inverse correlation with overall accuracy (Spearman 0.93 on 4B; 0.75 on 1B), substantially exceeding length (0.31/0.24), token perplexity (0.82/0.63), sequence NLL/'KL' (~0), and LongPPL (0.60–0.62, Appendix D). The result is robust across threshold choices (Table 3), holds qualitatively on Reasoning Gym algorithmic and cognitive tasks (Table 4), and degrades when training-data correctness is corrupted (Table 5). The authors frame the finding via the Minimum Description Length principle: effective reasoning chains, despite producing longer outputs, make the underlying input→answer mapping more compressible.
## Recommendation
**Weak Accept. The paper makes a genuinely novel conceptual contribution (inverting the intrinsic-dimensionality framing to characterize reasoning strategies rather than models) backed by strong, well-designed empirical correlations and useful robustness/correctness ablations. The main limitations—single model family with a stated conflict of interest, statistically underpowered cross-domain evidence, an unaddressed potential circularity with base-model proximity, confounds in two key strategy comparisons (Executed PoT, Gemini CoT), high cost of the metric with no cheap surrogate explored, informal MDL grounding, and absence of variance estimates and significance tests—do not undermine the core finding but meaningfully scope its claimed generality and practical utility. With additional model families, variance reporting, a base-model-proximity control, and tighter handling of confounds, this would be a clear accept.**  (confidence 4/5)
### Score Card
- Soundness: 3/4
- Presentation: 3/4
- Contribution: 3/4
- Overall: 6/10
### Main Strengths
- Conceptually novel reframing of intrinsic dimensionality as a property of the reasoning supervision (with the model fixed), rather than of the model (with data fixed). This is a clean and useful inversion of prior work that yields a non-obvious empirical signal.
- Strong and consistent empirical results: Spearman 0.93 on Gemma-3 4B and 0.75 on 1B across 14 diverse strategies, substantially outperforming all alternative quantitative metrics considered (length, token PPL, sequence NLL, LongPPL).
- Thoughtful threshold-robustness study (Table 3): correlations remain 0.72–0.94 across multiple reasonable threshold definitions. Notably, the epoch-1 training-accuracy threshold enables computing intrinsic dimensionality entirely from training curves—no validation/OOD evaluation needed—broadening applicability to settings without held-out labeled data.
- Useful controls: training-set size differences across strategies are shown not to drive the ordering (Spearman ~−0.11 with accuracy), and a correctness-corruption ablation (Table 5) provides supportive evidence that the metric reflects coherence of the input→output mapping rather than surface statistics.
- Broad strategy coverage (14 strategies spanning length, format, distractors, decomposition, verification, code), an extension to Reasoning Gym, and clear visualizations (Figures 1–3) that make the measurement procedure transparent.
- Thorough baseline comparison set, including the LongPPL variant (Appendix D) targeted at the most plausible per-trajectory alternative metric—strengthening the case that intrinsic dimensionality captures something distinct from perplexity.
- Clean MDL-grounded conceptual narrative that contextualizes the empirical finding within an established information-theoretic framework.

### Main Weaknesses
- Single model family. All experiments use Gemma-3 (1B and 4B), and the authors note a conflict of interest with Gemma development. Without at least one non-Gemma family (Llama, Qwen, Mistral), the generality of the central claim—and the strength of the headline 0.93 correlation—remains unestablished.
- Reasoning Gym cross-domain claim is statistically underpowered: rank correlations are computed over only n=4 strategies per category, yielding very wide confidence intervals. The cross-domain claim should be qualified accordingly.
- Potential circularity concern: strategies with higher base/zero-shot accuracy on the CoT format may reach a fixed absolute training-accuracy threshold at lower parameter counts almost by construction, since they need to move the model less from initialization. The paper does not explicitly disentangle 'compressibility of the input→output mapping' from 'proximity of the strategy to the base model's existing competence', and an ablation controlling for base-model zero-shot accuracy on each strategy's format would clarify this.
- Confounded strategy comparisons. (a) Executed PoT offloads arithmetic to a Python interpreter, so its 'low intrinsic dim + high accuracy' result may reflect circumvented computation rather than greater compressibility under the model. (b) Gemini CoT, although framed as a separate teacher-model comparison rather than a strategy-isolated condition, still cannot cleanly attribute differences to strategy vs. teacher quality.
- No cheap surrogate predictors are benchmarked. Obvious alternatives—training loss at a small fixed LoRA rank, base-model zero-shot accuracy on the CoT format, or early-step loss decay—would test whether the same ordering can be obtained at a small fraction of the LoRA sweep's cost. The authors note the computational cost in Section 6 but do not investigate such alternatives empirically.
- MDL grounding is informal. LoRA provides only an upper bound on description length—as the authors themselves note—so the MDL connection is motivational rather than rigorous. No formal claim links the LoRA-sweep estimator to a Kolmogorov/MDL quantity.
- Metric mislabeling and clarity issues. What is called 'sequence KL divergence' is in fact average sequence-level negative log-likelihood (cross-entropy under a uniform empirical distribution); the footnote about assuming teacher-token probability = 1 should be more prominently noted in the main text.
- No reported variance. Intrinsic-dim estimates and accuracies are not reported with seed variance or bootstrap CIs, leaving robustness to training stochasticity and confidence on the headline correlation difference unquantified. With n=14 strategies, the 0.93 vs 0.82 correlation gap is not subjected to a significance test (e.g., Steiger/Williams).
- Cross-scale 'larger models compress more efficiently' claim compares parameter counts measured at different absolute thresholds (63.0% for 4B vs 24.3% for 1B), so the comparison is not clean as currently presented.
- Limited ablation on the LoRA sweep design itself: the choice of module groups (attention-only vs MLP vs all) and the greedy selection of (rank, modules) at each parameter target qualitatively change which subspace is being explored. No analysis of how this affects the strategy ordering.

### Detailed Comments
- Section 2.3 / Section 4.3: The decision to use epoch-1 maximum training accuracy to set τ is well motivated and the robustness table (Table 3) is convincing within the considered range. Please specify what happens when a strategy never reaches τ in the swept range (e.g., No CoT at the upper bound of the sweep)—the reported d_int values appear to saturate at the sweep ceiling for several strategies, which could inflate the apparent spread.
- Section 4.1 / Tables 1–2: The headline correlation difference between intrinsic dim (0.93) and token perplexity (0.82) is large in magnitude but not tested for statistical significance. With n=14 strategies, a Steiger/Williams test for correlated correlations or a bootstrap CI would strengthen the comparison considerably.
- Section 4.2 (Gemma-3 1B): Several strategies score in the 1–5% range on overall accuracy, suggesting partial floor effects. It is worth checking whether the 0.75 correlation is dominated by which strategies clear the floor versus a graded ordering within the non-floor regime.
- Section 4.4 (cross-scale claim): As written, the 4B vs 1B compression comparison uses different absolute thresholds and is not a clean apples-to-apples statement. A re-analysis at a normalized threshold (e.g., 50% of each model's own maximum train accuracy) would substantiate the claim.
- Section 4.4 (Executed PoT): The interpretation 'code-based reasoning with execution provides a particularly compressible representation' should be tempered: Executed PoT replaces in-model arithmetic with deterministic external execution. Contrasting Executed PoT and Simulated PoT on arithmetic-heavy vs arithmetic-light subsets would clarify which mechanism is at play.
- Section 4.5: The Reasoning Gym extension is conceptually nice, but n=4 strategies per category yields wide CIs on rank correlations. Either expand the strategy set or weaken the framing.
- Potential circularity: strategies closer to the base model's output distribution (high zero-shot accuracy on the format) may require fewer LoRA degrees of freedom to push training accuracy above τ. Consider adding base-model zero-shot accuracy on each strategy's CoT format as both a baseline predictor and a control variable.
- Cheap surrogates: it would substantially increase the metric's practical relevance to report whether (i) training loss after K early steps at a small fixed LoRA rank, or (ii) base-model zero-shot accuracy on each format, can recover the strategy ordering at much lower cost.
- Sections 3 and Appendix: Please report decoding settings (temperature/greedy), validation-set composition, checkpoint-selection criteria, and seeds for the fine-tuning runs.
- Footnote 1: The note that the teacher token probability is assumed to be 1 (yielding a divergence-like but not true-KL quantity) is important and would be better placed in the main text where 'KL divergence' is defined.
- Figures 2–3 show only a subset of strategies. An appendix figure with all 14 curves would make it possible to assess whether Pareto frontiers cross or interleave (which would matter for the ordering).

### Questions for Authors
- Have you tested the intrinsic-dim ordering on a non-Gemma base model family (e.g., Llama-3, Qwen-2.5)? Even partial replication on 5–6 strategies would substantially strengthen generality, particularly given the conflict-of-interest disclosure.
- How sensitive is the strategy ordering to the LoRA module-group choice? If you restrict the sweep to attention-only or MLP-only adaptations throughout, are the headline correlations preserved?
- Does the base model's zero-shot accuracy on each strategy's CoT format predict overall accuracy comparably well? If so, does intrinsic dimensionality retain explanatory power after controlling for it?
- Can you isolate teacher-quality from strategy effects in the Gemini-CoT comparison, e.g., by generating long/unconstrained CoTs with Gemma-3 27B and short/equation-style CoTs with Gemini 2.5?
- Does Executed PoT retain its low intrinsic-dimension advantage on subsets where the arithmetic is light or trivial?
- Is the 0.93 vs 0.82 correlation gap between intrinsic dim and token perplexity statistically significant under a Steiger/Williams test (or bootstrap)?
- What are the seed-to-seed variances of (a) the estimated d_int for a fixed strategy and (b) the downstream overall accuracy?
- For strategies that never reach τ within the swept parameter range, how is d_int reported, and how does this choice affect the correlation?
- For the cross-scale claim, can you re-run the analysis with a model-normalized threshold to enable a clean comparison?
- Have you explored cheap surrogate predictors—e.g., training loss after a few hundred steps at a small fixed LoRA rank—and how do these correlate with overall accuracy?

### Suggestions for Improvement
- Add at least one non-Gemma model family (e.g., Llama-3-8B or Qwen-2.5-7B) to verify that the intrinsic-dim ordering is not specific to Gemma.
- Report bootstrap CIs on Spearman correlations and a Steiger/Williams test between intrinsic dim and the next-best baseline (token PPL).
- Run multiple seeds for the LoRA sweep and report variance bands on d_int and accuracies; at minimum, 3 seeds for a representative subset of strategies.
- Add a base-model zero-shot accuracy baseline (per strategy's CoT format) and an ablation showing whether intrinsic dimensionality contributes additional predictive power beyond it. This directly addresses the circularity concern.
- Benchmark at least one cheap surrogate predictor (e.g., early-step training loss at fixed small LoRA rank) and report its correlation with overall accuracy.
- Rename 'sequence KL divergence' to 'sequence NLL' or 'cross-entropy', and promote Footnote 1 into the main text.
- Decouple teacher quality from strategy by generating matched short/long CoTs from a common teacher.
- Provide an ablation isolating Executed PoT's external-execution effect from compressibility (e.g., compare against Simulated PoT on arithmetic-heavy vs arithmetic-light subsets).
- Extend the Reasoning Gym evaluation to ≥8 strategies per category, or explicitly qualify the cross-domain claim as exploratory.
- Recompute the 1B vs 4B 'larger models compress better' claim using a per-model-normalized threshold, and explicitly state when the comparison is qualitative.
- Position intrinsic dimensionality primarily as an analytical/interpretive tool given its computational cost, and either propose a cheap surrogate or clearly delineate use cases where the LoRA sweep is justified.
- Add an appendix figure showing the Pareto frontiers for all 14 strategies.

### Improvement Checklist
- Replicate the intrinsic-dimension correlation on at least one non-Gemma model family (e.g., Llama-3, Qwen-2.5), even on a subset of strategies.
- Add a base-model zero-shot accuracy baseline per CoT format and show whether intrinsic dimensionality adds predictive power beyond it (addresses a potential circularity concern).
- Benchmark at least one cheap surrogate (e.g., early training loss at small fixed LoRA rank) against intrinsic dimensionality.
- Report bootstrap CIs on Spearman correlations and a Steiger/Williams test between intrinsic dim and token perplexity.
- Add multi-seed variance estimates for d_int and downstream accuracies on a representative subset of strategies.
- Specify how d_int is handled when a strategy never reaches τ in the sweep, and analyze sensitivity to this choice.
- Recompute the 4B-vs-1B cross-scale compression claim using a per-model-normalized threshold.
- Provide an ablation on LoRA module-group choices (attention-only / MLP-only / all) and report whether the strategy ordering is preserved.
- Disentangle teacher-quality from strategy effects (e.g., produce matched CoTs from a single teacher).
- Provide evidence isolating Executed PoT's external-execution advantage from compressibility (e.g., arithmetic-heavy vs light subsets).
- Rename 'sequence KL divergence' to 'sequence NLL' and promote Footnote 1 into the main text.
- Expand Reasoning Gym to ≥8 strategies per category or explicitly qualify the cross-domain claim.
- Add an appendix figure with Pareto frontiers for all 14 strategies and a full d_int table.
- Document decoding settings, validation composition, checkpoint selection, and random seeds for reproducibility.

