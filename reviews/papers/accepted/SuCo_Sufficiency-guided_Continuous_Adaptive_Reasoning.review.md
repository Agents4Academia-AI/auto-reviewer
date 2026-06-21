# Reviewer Agent Report
**Paper file:** `SuCo_Sufficiency-guided_Continuous_Adaptive_Reasoning.pdf`  **Generated:** 2026-06-21T16:04:49.833960Z
---
## Summary of the Paper
The paper tackles reasoning redundancy in Large Reasoning Models (LRMs) by introducing Minimal Sufficient CoT (MSC), defined as the shortest sentence-level CoT prefix whose geometric-mean per-token probability of the ground-truth answer exceeds a problem-adaptive threshold δ(x) = δ0 + α·C(x), where C(x) is a percentile-rank complexity proxy based on reasoning length. Building on MSC, the authors propose SuCo, a two-stage training framework: (i) MSC-Aligned Fine-Tuning (MFT) constructs an MSC dataset from full CoT trajectories (with LLM-based refinement via Qwen3-Next-80B) and performs SFT; (ii) Sufficiency-Aware Policy Optimization (SAPO) extends GRPO with an EMA-updated dynamic complexity pool and a reward shaping scheme that asymmetrically penalizes over- and under-thinking. Experiments on Qwen2.5-Math-Base 1.5B/7B across 8 math/code/science benchmarks show that SuCo improves accuracy while substantially reducing reasoning tokens relative to DeepSeek-R1-Distill and adaptive baselines (AdaCoT, AdaptThink, S-GRPO, LHRMs). Ablations isolate the sufficiency metric, threshold adaptivity, complexity estimator, dynamic complexity pool (DCP), and the sufficiency reward; auxiliary analyses cover OOD generalization (StrategyQA, CSQA, AlpacaEval), cross-calibrator robustness, difficulty-conditioned length allocation, and empty-CoT behavior.
## Recommendation
**Weak Accept**  (confidence 4/5)
### Score Card
- Soundness: 3/4
- Presentation: 3/4
- Contribution: 3/4
- Overall: 6/10
### Main Strengths
- Clean, well-motivated conceptual framing: MSC operationalizes 'when is reasoning enough' via a length-invariant geometric-mean per-token sufficiency score, and Appendix Table 8 empirically justifies this choice over joint-probability and arithmetic-mean alternatives.
- Methodologically coherent two-stage pipeline combining several reusable ideas: percentile-based complexity proxy (robust to outliers), problem-adaptive threshold, EMA-tracked dynamic complexity pool that keeps sufficiency targets aligned with the evolving policy during RL, and asymmetric over/under-thinking rewards.
- Empirical evaluation is broad: 8 benchmarks across math/code/science, two model scales, four ALRM baselines, OOD evaluation, cross-calibrator robustness, and difficulty-conditioned analysis. Reported gains are sizable and frequently Pareto-dominant (e.g., AIME25 7B: +12 points accuracy with ~75% fewer tokens vs R1-Distill).
- Ablations meaningfully isolate design choices, and Figure 5 demonstrates that SAPO genuinely reallocates rather than uniformly compresses reasoning, supporting the adaptive-allocation narrative.
- Reproducibility is aided by Algorithm 1, hyperparameter values, refinement prompts in Appendix C, and dataset statistics in Appendix B. The Limitations section is transparent about the reliance on ground-truth answers and on distillation from strong LRMs.

### Main Weaknesses
- Attribution of gains is confounded by the Qwen3-Next-80B refinement teacher. The paper does not include a 'Full CoT refined by Qwen3-Next-80B (without MSC truncation)' baseline, so it is unclear how much of MFT's improvement over Full CoT SFT comes from sufficiency-based truncation versus distillation from a strong 80B teacher. The same 80B model also serves as the quality assessor (Appendix B.4), raising a potential circularity concern.
- Baseline-comparison fairness is uneven. AdaCoT and LHRMs are re-trained on SuCo's data from Qwen2.5-Math-Base, while AdaptThink and S-GRPO follow their original implementations from DeepSeek-R1-Distill-Qwen. This confounds method-vs-base attribution; additionally Qwen2.5-Math-Base is math-specialized, which may inflate math gains.
- Statistical rigor is limited. Apart from 10-run averaging on AMC23/AIME25, no standard deviations, seeds, or significance tests are reported. Several ablation deltas (Table 3: DCP and R_suff contribute ~0.2–0.4 accuracy points) and at least one head-to-head comparison (Table 1 AMC23 7B: SuCo 90.3 vs S-GRPO 90.5) lie within plausible noise.
- The 'continuous adaptive reasoning' framing is somewhat overstated. At inference time the model produces a single trajectory with no user-facing continuous control knob; continuity exists only in the training-time threshold. The continuous-vs-discrete distinction at inference time is less clear-cut than the framing suggests.
- Figure 1's MSC selection requires access to ground-truth answer probabilities (per Eq. 1). The paper does not hide this, but the figure is presented as a motivation that 'models can perform better with less reasoning' without flagging that the short prefixes are oracle-selected. Readers may misread this as a deployable inference behavior.
- The minimality definition (Eq. 2) is technically violated by the fallback rule (Eq. 6): when no prefix reaches δ(x), the argmax prefix is still labeled MSC despite being non-sufficient. The edge case t* = ∞ in the SAPO reward (Eq. 11) is also not analyzed.
- Using reasoning length as a complexity proxy is correlational and may conflate model verbosity with intrinsic problem hardness, particularly across domains (code traces are systematically longer than math). The intra-domain ablation (Appendix A.5) addresses this only partially and does not validate against an external difficulty signal.
- Several procedural details are underspecified: which model's probabilities are used to compute the sufficiency score (the source LRM, the base policy being fine-tuned, or πθ during SAPO), how sentence boundaries are determined, evaluation decoding configuration (temperature, top-p, max tokens), and whether the Qwen3-Next-80B refinement model is identical to the quality judge.
- No training-compute or wall-clock cost is reported. Computing sufficiency scores requires teacher-forward passes over the full CoT trajectories, and the dynamic complexity pool requires periodic updates during RL; quantifying this overhead is important since efficiency is a central theme.
- OOD claims rest on three tasks, and the AlpacaEval LC-WR values in Table 4 (0.3, 1.05, 2.4) appear on an unusual scale that is not explained — even SuCo's best score is very low in absolute terms if these are percentages.

### Detailed Comments
- Section 3.2 (MSC definition): Please reconcile the minimality formalism in Eq. 2 with the fallback in Eq. 6. As written, when no δ-sufficient prefix exists, the algorithm returns a non-sufficient prefix that still violates the sufficiency condition. Consider redefining MSC piecewise (sufficient case vs. saturated case) or excluding such samples from training.
- Section 3.2 (complexity proxy): The argument that reasoning length is a proxy for difficulty is supported by Figure 1, but length is a model-specific verbosity measure. It would be informative to correlate C(x) with an external difficulty signal (e.g., MATH difficulty level, pass rate of a fixed reference model) to validate that the proxy captures intrinsic complexity rather than the teacher's style.
- Section 3.4 (dynamic complexity pool): The EMA update in Eq. 9 uses average length per question, while the threshold is derived from percentile ranks over the pool. Please clarify the temporal semantics: is the percentile recomputed at every step, every batch, or every epoch? How are ties handled when many samples share the same length?
- Section 3.4 (reward shaping): The under-thinking penalty only applies to incorrect generations (Eq. 11), which couples it to R_cor. Please discuss whether the reward could be reduced to R_cor + over-thinking penalty without loss, and whether under-thinking on correct outputs should be neutral or rewarded.
- Section 4.1 (baselines): The mismatched base models for AdaptThink/S-GRPO vs SuCo, AdaCoT, and LHRMs make Table 1 hard to interpret as a controlled comparison. Re-running at least one of AdaptThink/S-GRPO from Qwen2.5-Math-Base, or running SuCo from R1-Distill-Qwen, would clarify what is attributable to the method versus the base model.
- Section 4.2 (token-reduction framing): The 74–76% reduction figures are anchored to R1-Distill. Relative to the strongest efficient baseline (LHRMs), the reduction is much smaller (e.g., 1.5B: 1,483 vs 2,055 ≈ 28%). Both numbers should be reported in the main text.
- Table 1: Qwen2.5-Math-Base MATH500 accuracy of 22.6% looks anomalously low relative to the official Qwen2.5-Math technical report. Please verify or explain (e.g., prompt template, no few-shot setting).
- Table 3 (SAPO ablation): With DCP and R_suff contributing only 0.2–0.4 accuracy points, the case for SAPO as a necessary stage is empirically weak on average. The per-benchmark story in Figure 5 is more compelling — consider promoting per-benchmark deltas to the main ablation table and reporting variance.
- Appendix A.4: The sufficiency metric ablation is one of the most important justifications of the design and should be summarized in the main paper.
- Figure 1: Please state explicitly in the caption that MSC there is selected using ground-truth answer probabilities, so readers do not infer that a deployed model produces these shorter trajectories at no cost.
- OOD results (Table 4): The Full-CoT SFT baseline collapses on StrategyQA (22.6%) and CSQA (19.4%), well below the base R1-Distill (53.3/45.0). This suggests SFT on the math/code/science distillation data degrades general capability, which complicates interpretation of the SuCo OOD gains. A baseline that mixes general instruction data would be more convincing.
- Appendix B.4 / C: Using the same Qwen3-Next-80B model for both MSC refinement and quality assessment is potentially circular (the judge may prefer samples in its own style). Please justify or use an independent judge.

### Questions for Authors
- Which model's policy is used to compute the sufficiency score S_θ during MSC dataset construction — the source LRM that produced the trajectory, the base policy being fine-tuned, or the refinement model? How sensitive are MSC boundaries to this choice, and is the sufficiency score recomputed under πθ during SAPO?
- Can you provide a controlled ablation where Full CoT data is refined by Qwen3-Next-80B without sufficiency-based truncation, to isolate the contribution of the refinement teacher from the MSC criterion?
- Why are AdaptThink and S-GRPO evaluated from a different base model (R1-Distill-Qwen) than SuCo, AdaCoT, and LHRMs? Can you provide a head-to-head comparison where all methods share the same base model and the same training data?
- Could you report standard deviations / seed variability for close comparisons (e.g., Table 1 AMC23 7B SuCo 90.3 vs S-GRPO 90.5; Table 3 DCP and R_suff ablations) and indicate which differences are statistically significant?
- How is the fallback case (no prefix satisfies δ(x), t* = ∞ in Eq. 11) handled during SAPO? Are these samples excluded, or does the over-thinking penalty become trivially zero / the under-thinking penalty fire for any incorrect output?
- How are sentence boundaries determined (punctuation rules, special tokens, or a separate segmenter)? How robust are MFT and SAPO to alternative segmentation choices?
- What decoding parameters (temperature, top-p, max tokens) are used at evaluation, and are they matched across all baselines?
- Could you clarify the AlpacaEval LC-WR scale (Table 4)? Values in the range 0.3–2.4 are not standard if these are percentages.
- Does the same Qwen3-Next-80B model serve as both the MSC refinement model and the quality assessor in Appendix B.4? If so, how do you guard against circularity (the judge favoring its own style)?
- Table 5 demonstrates calibrator robustness across Qwen3-4B/14B and DS-R1-Distill-7B, all Qwen-lineage. Have you tested non-Qwen calibrators (e.g., a Llama-family calibrator) to verify cross-family generality on the calibrator side?
- Could you report training compute (GPU-hours) or wall-clock for MFT and SAPO, including the teacher-forward overhead for sufficiency-score computation and pool updates, relative to vanilla SFT/GRPO?

### Suggestions for Improvement
- Add a 'Full CoT + 80B refinement (no truncation)' baseline to disentangle MSC from teacher distillation.
- Unify the experimental protocol so that all adaptive baselines share both the same base model and training data, or provide both base-model variants for SuCo.
- Report seed variance and statistical significance for headline numbers and close ablations.
- Refine the MSC definition (Eq. 2) to handle the no-sufficient-prefix case cleanly, and analyze t* = ∞ behavior in Eq. 11.
- Move the sufficiency-metric ablation (Appendix A.4) into the main paper, given its centrality to the contribution.
- Clarify Figure 1's caption to indicate that MSC there uses ground-truth answer probabilities and does not reflect deployable inference.
- Tone down the 'continuous' framing or expose an inference-time continuous control knob (e.g., adjustable δ at test time) and evaluate the resulting accuracy–length trade-off curve.
- Compare empirically against ThinkPrune and AlphaOne, which are cited but not benchmarked.
- Report token-reduction percentages relative to the strongest efficient baseline (LHRMs) in addition to R1-Distill.
- Validate the length-based complexity proxy against an external difficulty signal (e.g., MATH levels, reference-model pass rate) and report cross-domain calibration.
- Use an independent judge for MSC quality filtering, or report results with and without filtering to quantify its effect.
- Clarify reporting scale for AlpacaEval and consider strengthening the OOD section with a general-capability benchmark (e.g., MT-Bench) and a baseline that mixes general instruction data.
- Report training compute and overhead introduced by sufficiency-score computation and the dynamic complexity pool.

### Improvement Checklist
- Add a 'Full CoT refined by Qwen3-Next-80B (no MSC truncation)' baseline to isolate teacher-distillation effects from MSC truncation.
- Either unify base models across all ALRM baselines or report SuCo trained from R1-Distill-Qwen so the comparison in Table 1 is controlled.
- Report standard deviations / multiple seeds for headline numbers and SAPO ablations; mark within-noise comparisons (e.g., AMC23 7B vs S-GRPO).
- Reformulate MSC (Eq. 2) and Eq. 11 to handle the no-sufficient-prefix / t* = ∞ case explicitly.
- Clarify in Figure 1's caption that MSC selection uses ground-truth answer probabilities.
- Specify which model's probabilities define Sθ at each stage (MSC construction and SAPO), the sentence-boundary procedure, and evaluation decoding parameters.
- Report training compute and the overhead of sufficiency-score computation and dynamic complexity pool updates.
- Use an independent judge for MSC quality assessment (currently the same 80B model as the refiner) or quantify the effect of filtering.
- Validate the length-based complexity proxy C(x) against an external difficulty signal (e.g., MATH levels, reference-model pass rate).
- Move the sufficiency-metric ablation (Appendix A.4) into the main text.
- Clarify AlpacaEval LC-WR scale and consider adding a general-capability OOD benchmark with a mixed-data SFT baseline.
- Soften the 'continuous adaptive reasoning' framing or expose an inference-time control knob and evaluate the trade-off curve.
- Add empirical comparisons to ThinkPrune and AlphaOne.
- Test a non-Qwen-lineage calibrator (e.g., Llama-family) to strengthen the cross-family robustness claim.

