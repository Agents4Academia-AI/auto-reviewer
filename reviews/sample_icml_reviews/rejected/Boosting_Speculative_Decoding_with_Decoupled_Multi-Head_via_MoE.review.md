# Reviewer Agent Report
**Paper file:** `Boosting_Speculative_Decoding_with_Decoupled_Multi-Head_via_MoE.pdf`  **Generated:** 2026-06-21T16:04:40.204340Z
---
## Summary of the Paper
The paper proposes Jakiro, a speculative decoding method that targets a specific limitation of tree-based draft methods: candidates at the same draft-tree layer are derived from a single shared feature representation and are therefore correlated. Jakiro replaces the Eagle-style draft MLP with a Mixture-of-Experts layer using top-2 routing, producing two intra-layer logits distributions that are used to construct the draft tree. To reduce drafting cost, the authors introduce a hybrid strategy that drafts γ−1 steps autoregressively and uses parallel decoding at the penultimate step, augmented by a learned feature-level contrastive operation (β f^top1 − α f^top2) between the two activated experts before the shared LM head. Training uses Smooth-L1 feature regression and cross-entropy classification losses for both MoE and contrastive heads. The method is evaluated on Vicuna (7B/13B/33B), LLaMA2-chat (7B/13B/70B), and LLaMA3-Instruct (8B/70B), across six benchmarks (MT-bench, HumanEval, GSM8K, Alpaca, CNN/DM, Natural Questions), under both greedy and non-greedy decoding, and on MI250/A40/A100 GPUs at batch size 1. Reported walltime speedups consistently exceed Eagle2, with the largest gains in non-greedy mode (up to 3.86x on A100 MT-bench for Vicuna 7B). Ablations study the number of candidate experts and the individual contributions of parallel decoding and the contrastive mechanism.
## Recommendation
**Weak reject. The paper identifies a real limitation in tree-based speculative decoding and proposes a reasonable architectural fix with broad empirical evaluation, but the central mechanism is never directly measured, key ablations weaken the MoE framing, gains from the heavily emphasized contrastive component appear marginal and within plausible noise, the SOTA claim is not supported by an adequate baseline set, and the inconsistent and under-specified use of Jakiro vs Jakiro* obscures credit attribution. With direct diversity measurements, statistical significance reporting, comparisons to more recent SD baselines, a unified and fully specified Jakiro configuration, and a careful losslessness argument, the paper could be substantially strengthened.**  (confidence 3/5)
### Score Card
- Soundness: 2/4
- Presentation: 2/4
- Contribution: 2/4
- Overall: 4/10
### Main Strengths
- Identifies a concrete and previously underexamined limitation in tree-based speculative decoding: intra-layer candidate coupling due to shared feature representation, which complements Eagle's inter-step decoupling story.
- Proposes a clean architectural fix (MoE draft head with top-2 routing) that integrates naturally with existing Eagle-style drafters and both static (Eagle1) and dynamic (Eagle2) tree constructions.
- Empirical evaluation is broad: 7 target models spanning 7B–70B and three families, 6 benchmarks, three GPU platforms (MI250/A40/A100 reported in main text and appendix), and both greedy and non-greedy modes; speedups over Eagle2 are consistently positive in the headline tables.
- Cross-device appendix results (MI250, A40, A100) indicate the gains are not specific to a single hardware platform.
- Losslessness of the verification step is preserved by inheriting standard speculative-sampling acceptance, and code is released, which aids reproducibility and adoption.
- Training cost is modest (the 70B drafter trains in 2–3 days on 4×A100), and additional trainable parameters are small relative to the target model.
- Ablation on N–K (Table 3) provides useful insight into the cost–benefit tradeoff of larger MoE configurations, even if the result complicates the framing.

### Main Weaknesses
- The central 'decoupling' claim is argued only architecturally and never measured. No quantitative diversity metric (e.g., KL between sibling experts' distributions, top-k token-set overlap, expert utilization, conditional acceptance probabilities at each tree layer) is reported to substantiate the motivating story or compare against Eagle2's intra-layer correlation.
- Table 3 shows the best walltime is achieved at N=2, K=2, which arguably reduces to a two-head design with shared backbone rather than a true sparse mixture. This is an interpretive concern rather than a definitive conclusion (larger N may benefit from further hardware/algorithmic optimization, as the authors note), but it nonetheless weakens the framing of MoE as the primary mechanism behind the gains.
- The contrastive mechanism is positioned as a major contribution but contributes only marginally in ablations (Table 4 on Vicuna 7B, T=0: 2.92x → 2.99x on MT-bench, 3.36x → 3.43x on HumanEval). Without variance estimates these differences are hard to distinguish from run-to-run noise.
- No standard deviations, confidence intervals, or significance tests are reported despite averaging over four runs. Several headline comparisons (e.g., Jakiro vs Eagle2 on some configurations) differ by amounts that could plausibly be within noise.
- The 'SOTA' claim is overstated relative to the baseline set. Comparisons are limited to Eagle1/Eagle2 (with Medusa/Hydra/SpS only on Vicuna 7B greedy). Recent SD methods such as Kangaroo, Sequoia, Glide, REST, Medusa-2/Hydra-2, PaSS, SPACE, and multi-token-prediction drafters are not benchmarked.
- Two variants 'Jakiro' and 'Jakiro*' are used inconsistently across tables. Per the Table 1 footnote, the distinction is in tree construction (weighted decoupling vs weighted non-decoupling combined with the contrastive mechanism), but whether the contrastive component is also active in Jakiro* is not explicitly clarified. The headline 3.86x speedup on Vicuna 7B (Figure 2) is achieved by Jakiro*, while most ablations and the architectural narrative center on the non-* variant, complicating attribution of credit to individual components.
- Counterexamples and configurations where Jakiro is comparable to or slightly worse than Eagle2 are not discussed: e.g., A100 T=0 LLaMA2 7B Jakiro 3.05x vs Eagle2 3.10x (Table 6); A100 T=1 Vicuna 13B CNN/DM Jakiro* 1.96x vs Eagle2 2.28x; A100 T=1 HumanEval Vicuna 7B Jakiro 2.96x vs Eagle2 3.11x.
- Losslessness under the modified hybrid drafting (parallel decoding at the penultimate step with a contrastive feature) is asserted by inheritance but never explicitly argued. It is not clear which draft distribution q(.|.) is used in the acceptance criterion for tokens proposed at the parallel step, nor how rejection-resampling behaves in this regime.
- Several claims are not directly supported by experiments: 'improves factuality' (no factuality benchmark), 'minimal computational cost' (Table 3 suggests cost grows with N), and 'almost no additional latency' from the contrastive operation (not measured).
- The contrastive regression target (Eq. 10) supervises f_i^const to predict the feature at position i+2 using a contrast between sibling experts at step i. The theoretical/empirical motivation for why a subtraction of two same-step expert features should predict the next-next token is not provided.
- The Top-K mechanism for MoE expert selection (K=2) and the top-k tree branching at each layer are both set to 2 and described together; whether these two uses of 'K' are linked by design or coincidence is not clarified.
- Notation in Section 3 is inconsistent: Eq. 3 produces a single fused feature f_i, while Eqs. 6–7 introduce f^top1 and f^top2 and use them in Eqs. 4 and 8. The mapping between these quantities is not made explicit.
- The reproduced Eagle1 number for LLaMA3-Instruct 8B on A100 (1.67x) appears anomalously low compared to the original Eagle paper, but no explanation is provided. This affects the credibility of the speedup comparisons that use this baseline.

### Detailed Comments
- Section 3.1 motivates MoE primarily for diversity, but the formal mechanism (Eqs. 1–5) is standard sparse-gated MoE; nothing in the construction explicitly encourages experts to produce diverse predictions (no diversity regularizer, no load-balancing loss mentioned). It would help to either (a) show empirically that the top-2 experts produce more diverse distributions than Eagle's top-2 logits, or (b) add an explicit diversity-inducing objective during training.
- The contrastive mechanism in Eq. 7 contrasts two similarly-capable experts in hidden-feature space, whereas the cited contrastive decoding works (Li et al., 2022; O'Brien & Lewis, 2023) contrast strong vs. weak models in logit space. The justification for feature-space contrast between similarly trained experts is not made.
- Table 4 ablations are run only on Vicuna 7B at T=0 — the regime where the paper itself concedes the contrastive mechanism is least impactful. An ablation under non-greedy mode and on at least one larger model would strengthen the case for the proposed components.
- The relationship between Jakiro and Jakiro* should be made explicit early in the method section. Currently, the Table 1 footnote is the first place readers learn that the headline non-greedy numbers come from a different tree-construction variant, and the exact component composition of Jakiro* (in particular, whether the contrastive mechanism is active) is not fully clarified.
- Figure 7's labeling is dense; grouping by device and including τ would improve readability.
- The paper claims 'one less drafting step than Eagle2' as a key efficiency lever, but doesn't isolate this from MoE compute overhead. An ablation matching Eagle2 with one fewer step (parallel-decoded at the last step) but without MoE would help isolate the MoE contribution.
- Training details (e.g., expert dropout, load-balancing auxiliary loss, expert collapse mitigation) are not discussed. For an MoE module with small N, expert collapse is a real concern.
- The paper does not discuss inference-time memory overhead of the MoE drafter, nor how it scales with batch size > 1.
- Minor: citation 'Langley, 2000' appears in references but is never cited in the body. Some tables omit Eagle1 numbers inconsistently. There are typos (e.g., 'accpet length').

### Questions for Authors
- Can you provide a direct quantitative measure of intra-layer 'decoupling' — for example, KL divergence or top-k token-set overlap between the two activated experts' distributions, compared against the analogous quantity for Eagle2's top-2 sibling tokens — to substantiate the central mechanism story?
- Given Table 3 shows the best speedup at N=K=2, is your method effectively a two-head design? Have you tried N>2 with parameter-matched controls (e.g., expanded MLP) and tuned tree budgets so that compute is comparable?
- Can you provide an explicit argument (formal or informal) that the hybrid drafting with a parallel-decoded penultimate step preserves the lossless guarantee of standard speculative sampling? Specifically, what draft distribution q(.|.) is used in the acceptance criterion for tokens proposed at that step?
- Why does the reproduced Eagle1 speedup for LLaMA3-Instruct 8B on A100 (1.67x) differ substantially from the originally published numbers? Were tree configurations, draft model sizes, and inference codepaths matched?
- Can you report mean ± std (or confidence intervals) over the four runs for all main tables and ablations? Several differences appear within plausible run-to-run variance.
- How were the learned contrastive weights α and β initialized, and what are their typical learned values? Did you compare with fixed contrastive weights, logit-space contrast, or a control that performs parallel decoding without the contrast?
- What is the rationale for supervising f_i^const (a contrast of two sibling-expert features at step i) to predict the feature at step i+2 (Eq. 10)? Have you tried alternative targets (e.g., predicting step i+1 with a contrastive correction)?
- Why are recent speculative decoding methods (Kangaroo, Sequoia, Glide, REST, Medusa-2/Hydra-2, PaSS, SPACE, multi-token prediction) not included as baselines? Without them, the SOTA claim is hard to assess.
- Could you clarify the relationship between Jakiro and Jakiro* — including precisely which components (MoE tree construction, parallel decoding, contrastive mechanism) are active in each — and report a unified configuration whose results are used consistently across tables?
- Are draft model parameter counts and runtime tree budgets matched against Eagle1/Eagle2 in the speedup comparisons? An Eagle-style baseline trained with the same hybrid PD/contrastive objective but without MoE would help isolate MoE's contribution.
- The conclusion mentions improved 'factuality' — can you provide any direct factuality/hallucination evaluation (e.g., TruthfulQA, FactScore) supporting this claim, or otherwise soften the wording?
- Equations 3 vs 6–7 appear inconsistent: Eq. 3 defines a single fused feature f_i, while Eq. 6 introduces a weighted sum of f^top1 and f^top2 and Eq. 7 a contrast over the same. Could you reconcile the notation and clarify which features feed into the LM head at each step?
- Is the use of K=2 for both MoE expert activation and tree branching intentional and linked, or coincidental? How does decoupling these two K values affect performance?
- How does Jakiro behave at batch sizes > 1, where MoE compute overhead and tree-attention masking interact differently with memory-bandwidth bottlenecks?
- Was any auxiliary load-balancing loss used for the MoE router? With small N, how do you prevent or detect expert collapse, and what are the expert utilization statistics?

### Suggestions for Improvement
- Add direct, quantitative measurements of intra-layer diversity (e.g., distributional divergence and token overlap between the two heads/experts) and compare against Eagle2 to support the decoupling motivation.
- Report mean ± standard deviation (or bootstrap CIs) over runs for all main results and ablations; mark differences that are not statistically significant.
- Unify the Jakiro and Jakiro* configurations or, at minimum, present a single canonical configuration whose components are isolated in a clean ablation grid (MoE / hybrid PD / contrastive) on multiple models, in both greedy and non-greedy modes. State explicitly which components are active in each variant.
- Provide an explicit (even if informal) argument for losslessness under the parallel-decoded penultimate step, specifying the draft distribution q used at that position and how acceptance/rejection is computed.
- Soften the 'SOTA' claim or add more recent SD baselines (Kangaroo, Sequoia, Glide, REST, Medusa-2/Hydra-2, PaSS, SPACE).
- Match draft-model parameter counts and tree budgets when comparing to Eagle1/Eagle2, and report a baseline that uses Eagle's architecture trained with the same hybrid drafting + contrastive objective to isolate the MoE contribution.
- Explain the anomalous reproduced Eagle1 number for LLaMA3-Instruct 8B on A100 and verify the reproduction settings.
- Discuss counterexamples in the tables (configurations where Jakiro is comparable to or worse than Eagle2) and analyze when and why this occurs.
- Remove or substantiate the 'factuality' and 'minimal computational cost' / 'almost no additional latency' claims with direct measurements.
- Fix notation inconsistencies in Section 3 (especially between Eqs. 3 and 6–7), and clarify which features feed into the LM head at each step of inference.
- Justify the choice of contrastive regression target in Eq. 10 (predicting f^p_{i+2} from a same-step sibling-expert contrast) and consider ablating alternative target offsets.
- Discuss MoE-specific training considerations (load balancing, expert collapse) and report expert utilization statistics.

### Improvement Checklist
- Add a quantitative diversity analysis (KL or top-k overlap) between sibling experts vs Eagle2's top-2 sibling tokens.
- Report mean ± std (or CIs) over runs for all tables and mark non-significant differences.
- Provide a clean component ablation grid (MoE / hybrid PD / contrastive) on multiple models and at both T=0 and T=1, explicitly stating which components are active in Jakiro and Jakiro*.
- State an explicit losslessness argument for the hybrid drafting with parallel-decoded penultimate step, including the form of q used in acceptance.
- Add comparisons to more recent SD baselines (e.g., Kangaroo, Sequoia, Glide, REST, Medusa-2/Hydra-2, PaSS, SPACE) or soften the SOTA claim.
- Match draft parameter counts and tree budgets across baselines; include an Eagle-style baseline with the same hybrid + contrastive objective to isolate MoE's contribution.
- Investigate/explain the anomalous reproduced Eagle1 LLaMA3-Instruct 8B speedup on A100.
- Discuss configurations where Jakiro is comparable to or worse than Eagle2 and analyze causes.
- Either run a factuality benchmark or remove the 'factuality' claim; similarly substantiate or remove 'minimal computational cost' and 'almost no additional latency'.
- Reconcile notation between Eqs. 3 and 6–7 and clarify which features feed the LM head at each step.
- Justify the contrastive regression target in Eq. 10 (predicting feature at i+2 from a same-step sibling-expert contrast).
- Clarify whether the K=2 used for MoE routing and the K=2 used for tree branching are intentionally coupled.
- Discuss MoE training stability (load balancing, expert collapse) and report expert utilization, especially for small N.
- Report inference-time memory overhead and behavior at batch sizes > 1.
- Fix minor issues: 'accpet length' typo, unused Langley 2000 citation, inconsistent inclusion of Eagle1 baseline across tables.

