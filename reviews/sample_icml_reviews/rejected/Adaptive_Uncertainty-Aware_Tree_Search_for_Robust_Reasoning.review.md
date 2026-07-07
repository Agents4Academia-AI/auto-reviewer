# Reviewer Agent Report
**Paper file:** `Adaptive_Uncertainty-Aware_Tree_Search_for_Robust_Reasoning.pdf`  **Generated:** 2026-06-21T16:05:18.278818Z
---
## Summary of the Paper
The paper identifies that Process Reward Models (PRMs) used to guide external tree search for LLM reasoning become unreliable when scoring reasoning traces produced by policy models whose distribution differs from the PRM's training distribution. The authors empirically demonstrate, on a 50-question MATH500 subset across two PRMs and two policies, that cross-distribution pairs exhibit higher MC-Dropout score variance and lower search accuracy. They then provide a bandit-style regret analysis showing that greedy uncertainty-agnostic selection accumulates linear regret in the OOD probability ε, while UCB-style uncertainty-aware selection achieves sublinear O(ε√(T ln T)) regret when sample budget scales as Kt=Ω(t). Motivated by this analysis, the authors propose UATS: (i) MC-Dropout-based epistemic uncertainty estimation yielding empirical mean, variance, and a UCB score; (ii) a heuristic search (H-UATS) that filters candidates into ID/OOD via a variance threshold, retains optimistic OOD candidates, and distributes re-evaluation and expansion budgets via temperature-controlled softmaxes; and (iii) an adaptive controller (A-UATS) trained with REINFORCE that dynamically modulates six search hyperparameters. Across MATH-500 and AIME24 with 5 policy models, 3 PRMs, and budgets N∈{4,...,256} matched by wall-clock latency, H-UATS and A-UATS consistently outperform Best-of-N, Beam Search, REBASE, DoRA, and DVTS, with ablations confirming that the uncertainty signal contributes substantially to the gains.
## Recommendation
**Borderline / weak reject — The paper addresses a timely problem and presents a coherent framework with broad empirical evidence and a useful uncertainty-vs-budget ablation, but the theoretical contribution rests on assumptions that are partly in tension with the paper's own motivation, the MC-Dropout estimator is not validated as a faithful epistemic uncertainty signal, statistical significance is absent on a small AIME benchmark, and several important baselines and reproducibility details are missing. With a corrected/strengthened theory under bounded-bias assumptions, calibration validation of MC-Dropout, held-out policy-PRM generalization tests for A-UATS, significance testing, and clearer baseline specification, the paper could become a solid accept.**  (confidence 4/5)
### Score Card
- Soundness: 2/4
- Presentation: 3/4
- Contribution: 2/4
- Overall: 5/10
### Main Strengths
- The paper identifies and clearly frames a real and increasingly relevant problem: policy-PRM distribution mismatch causes overconfident PRM misrankings during search. The motivation is grounded in both quantitative evidence (Figure 2) and a clear qualitative example (Figure 1).
- The framework unifies three components — MC-Dropout uncertainty estimation, uncertainty-aware budget allocation (H-UATS), and a learned adaptive controller (A-UATS) — into a coherent inference-time pipeline that bridges bandit-style theory and practical search algorithms.
- Empirical evaluation is broad: 5 policy models (0.5B–8B) × 3 PRMs × 7 budgets on MATH-500 plus AIME24, with consistent gains over Beam Search, Best-of-N, REBASE, DVTS, and DoRA (Table 2; Figures 4, 6, 7).
- The ablation in Table 3 cleanly demonstrates that the uncertainty signal — not just the budget reallocation mechanism — contributes substantially, with drops of 2–7 points across three policy-PRM pairs when uncertainty is removed.
- Compute is matched via wall-clock latency calibration (~18 PRM passes per generation step), which is a more meaningful protocol than naive N-matched evaluation.
- Appendix F provides systematic hyperparameter sensitivity studies (dropout rate p, initial sample count K0, threshold τ, optimism margin δ, network architecture), supporting the robustness of the chosen configuration.
- The qualitative case studies (Figures 9–12) clearly illustrate the four-quadrant taxonomy of PRM score vs uncertainty and provide a useful diagnostic framing of where uncertainty-aware filtering helps and where it does not.

### Main Weaknesses
- The theoretical analysis rests on assumptions that are partly in tension with the paper's own empirical motivation. Proposition 4.2 assumes Eϕ[R̄t(h)] = R*(h) (unbiased estimators), while the paper's central claim is that PRMs are systematically biased on OOD inputs — MC-Dropout samples over parameter perturbations but is unlikely to remove a systematic OOD bias inherited from PRM training. Proposition 4.1 also assumes P(error | ID) = 0, which makes the linear-vs-sublinear contrast partly an artifact of the assumption rather than a purely algorithmic distinction.
- Proposition 4.2's Case 1 (ID contributes negligible regret) is asserted rather than proved, leaving a meaningful gap in the derivation.
- The theory-to-algorithm link is qualitative. The theory requires Kt = Ω(t) and i.i.d. OOD events; the algorithm uses fixed K0 plus heuristic reallocation on highly correlated tree-structured states. No experiment verifies the predicted O(√T ln T) regret scaling.
- MC-Dropout is presented as approximating p(ϕ | D_PRM), but the paper does not validate whether off-the-shelf PRMs (not necessarily trained with the specific dropout configuration used at inference) yield meaningful posterior samples. There is no calibration analysis (e.g., ECE, reliability diagram, AUROC for OOD step detection) showing that σR is a faithful epistemic uncertainty estimator.
- The empirical OOD analysis motivating the whole paper (Section 4.1, Figure 2) rests on only 50 problems and a 2×2 PRM-policy grid, without per-step OOD labeling. The paper never directly measures accuracy gains specifically on OOD-flagged steps, so the central claim of 'mitigating OOD errors' is inferred rather than measured.
- AIME24 has only ~30 problems, yet small numerical differences (often ≤2 points) are interpreted as substantive improvements. No confidence intervals, paired significance tests, or multi-seed standard deviations are reported anywhere.
- Baselines are under-specified. Beam widths and REBASE/DVTS/DoRA temperatures and configurations are not given. The 'H-UATS w/o Uncertainty' variant — described as methodologically similar to REBASE — reports numbers that differ from the REBASE row in Table 2, raising reproducibility concerns about baseline tuning.
- Important comparison baselines are missing: PRM ensembles (a natural alternative epistemic uncertainty estimator), self-consistency / majority voting, UCB-MCTS, and a 'UCB-without-MC-Dropout' control that would isolate which component is doing the work.
- A-UATS generalization is only partly substantiated. Training uses a mix of policy-PRM pairs, but there is no held-out policy-PRM transfer experiment, only 500 REINFORCE updates with sparse training-detail reporting, and the gain over H-UATS (~1.5–3 points) is not decomposed into 'behavioral-cloning init' vs 'RL fine-tuning' contributions.
- Even with UATS, results remain well below the Oracle Pass@K curves shown in Figures 4 and 6, indicating substantial headroom that the paper does not discuss or analyze.
- No FLOPs metric is reported, and the 18:1 latency calibration is measured for a single batch size, sequence length, and hardware setting (and on the 7B PRM), then applied uniformly across policy sizes 0.5B–8B. Smaller policies have very different generation:PRM cost ratios, so the compute-matching is likely uneven across configurations and may favor UATS's parallel PRM evaluation.
- Methodological novelty is moderate: MC-Dropout, UCB, REBASE-style expansion, and REINFORCE controllers are all standard. The contribution is primarily their combination and the uncertainty framing.

### Detailed Comments
- Section 4.2: The combination of Proposition 4.1's idealized P(error | ID) = 0 and Proposition 4.2's unbiasedness assumption makes the linear-vs-sublinear contrast partly an assumption-driven artifact. A unified bounded-bias setting — in which both ID and OOD incur error with different rates, and OOD scores carry a residual systematic bias b — would more honestly reflect the empirical claim and yield a more informative bound.
- Section 4.2: Proposition 4.2's Case 1 ('No OOD contributes negligible regret') is stated without proof. Please make this assumption explicit or derive it from a stated ID-noise condition.
- Section 5.1: It is unclear whether the PRMs evaluated were trained with the same dropout configuration used at inference. If not, the resulting variance may partly reflect architectural noise rather than posterior dispersion. A small calibration study (e.g., ECE on a held-out PRM training set, AUROC for OOD step detection using cross-policy traces as a proxy) would strengthen this central component.
- Sections 5.2–5.3: Eq. 10 expands children over the full candidate set H, while the filtering step removes uncompetitive OOD candidates from the re-evaluation pool S — the interaction between these two pools should be clarified. The controller's action parameterization (output activations, bounded ranges, exploration noise), batch size M, and training/evaluation statistics are also not specified.
- Section 6.1: The wall-clock calibration (571 ms / 32 ms ≈ 18) is reported for one batch size and step length on one GPU. Since policy generation latency varies significantly across the policy models used (0.5B–8B) and across batch sizes, the 18:1 conversion is unlikely to hold uniformly; reporting per-model latency and FLOPs would clarify the compute-matching claim.
- Table 3 vs. Table 2: 'H-UATS w/o Uncertainty' is described as methodologically similar to REBASE, yet the numbers differ. Please clarify the precise differences and whether REBASE was re-tuned per policy-PRM pair.
- Statistical reporting: For AIME24 (~30 problems), 1–2 point differences correspond to 0–1 problem changes. Bootstrap CIs, paired McNemar tests, or multi-seed evaluations are needed to support the claimed improvements.
- Oracle gap: Figures 4 and 6 show a persistent gap between UATS and the Pass@K Oracle, suggesting that uncertainty-aware selection is not the only bottleneck. A discussion of remaining failure modes (e.g., correct paths never sampled by the policy) would help calibrate the contribution.
- Wording: Claims such as 'provably minimizes regret' (Sections 4.3 and 1) overstate the upper-bound result, which provides only an upper bound under idealized assumptions without matching lower bounds for the algorithm.
- Minor: Figure 1 cites σ²=0.032 vs 0.001 without connecting these numbers to the MC-Dropout configuration (K, dropout rate). The reference list contains both Snell et al. 2024a and 2024b, which appear to be the same work.

### Questions for Authors
- How do you justify the unbiasedness assumption Eϕ[R̄t(h)] = R*(h) in Proposition 4.2 given the empirical claim that PRMs are systematically biased on OOD inputs? Can the regret bound be re-derived under a bounded-bias assumption with a residual O(εTb) term?
- Can you make Proposition 4.2's Case 1 explicit — either as a stated assumption on ID noise or as a derivation — rather than asserting that ID contributes negligible regret?
- Can you provide an experiment that verifies the predicted O(√T ln T) scaling — e.g., a regret-vs-T (or vs-budget) curve and a comparison to a method using Kt = Ω(t) as the theory prescribes?
- Have you validated that MC-Dropout variance on these off-the-shelf PRMs is a meaningful epistemic uncertainty estimator? Specifically, can you report reliability diagrams, ECE, or AUROC for OOD step detection? How was dropout inserted into PRMs whose original training did not necessarily use the same dropout configuration?
- Why do the 'H-UATS w/o Uncertainty' numbers in Table 3 differ from the REBASE numbers in Table 2 despite the text describing them as methodologically similar? What are the exact algorithmic differences?
- Can you provide a held-out policy-PRM generalization experiment for A-UATS where the controller is trained on one policy-PRM family and tested on an entirely unseen one?
- Can you isolate the contribution of REINFORCE fine-tuning versus the behavioral-cloning initialization for A-UATS?
- Could you report FLOPs and end-to-end wall-clock latency per problem under matched conditions, and verify that the 18:1 calibration holds across the different policy sizes (0.5B–8B) used?
- Have you compared against a PRM-ensemble baseline as an alternative epistemic uncertainty estimator? How does H-UATS with an ensemble compare to MC-Dropout?
- On AIME24 (~30 problems), can you report paired bootstrap or McNemar's test results to substantiate the small percentage-point differences?
- How were baseline hyperparameters (beam widths, REBASE/DVTS/DoRA temperatures, sampling temperatures) chosen, and were they tuned per policy-PRM pair?

### Suggestions for Improvement
- Strengthen the theory by replacing the unbiased-estimator assumption with a bounded-bias condition (e.g., |E[R̄t(h)] − R*(h)| ≤ b on OOD inputs) and explicitly stating (or deriving) the ID-regret condition used in Proposition 4.2's Case 1.
- Add a calibration study of MC-Dropout on the PRMs used: reliability diagrams, ECE, and AUROC for distinguishing ID vs OOD reasoning steps (e.g., using cross-policy traces as a proxy). This would justify σR as an epistemic uncertainty estimator.
- Include a PRM-ensemble baseline (e.g., 3–5 independently fine-tuned or seed-varied PRMs) as an alternative uncertainty estimator and a 'UCB-only' control without MC-Dropout, to isolate which component drives gains.
- Add statistical significance testing: bootstrap confidence intervals for MATH-500 accuracy and paired McNemar tests for AIME24, plus multi-seed standard deviations for the controller training.
- Provide a held-out policy-PRM transfer experiment for A-UATS: train the controller on a subset of policy-PRM pairs and evaluate on entirely unseen combinations to substantiate generalization claims.
- Specify baseline hyperparameters and per-model latency measurements clearly, and reconcile the 'H-UATS w/o Uncertainty' variant with REBASE numbers.
- Report end-to-end wall-clock latency and FLOPs per problem for all methods at matched accuracy levels, including per-policy-size measurements, since efficiency is a central claim.
- Decompose the A-UATS gain into the behavioral-cloning initialization and RL fine-tuning contributions.
- Discuss the remaining gap to the Oracle Pass@K curves and characterize when uncertainty-aware selection cannot close it (e.g., correct path never proposed by the policy).
- Soften theoretical claims (e.g., 'provably minimizes regret' → 'achieves a sublinear regret upper bound under stated assumptions') and explicitly list the caveats.

### Improvement Checklist
- Re-derive Proposition 4.2 under a bounded-bias condition on E[R̄t(h)] − R*(h), and make the ID-regret assumption in Case 1 explicit or derived.
- Add a calibration study for MC-Dropout-based PRM uncertainty (ECE, reliability diagrams, AUROC for ID/OOD step detection), and clarify how dropout was inserted in off-the-shelf PRMs.
- Add a PRM-ensemble baseline and a 'UCB without MC-Dropout' control to isolate where the gains come from.
- Report bootstrap confidence intervals and paired McNemar tests (especially for AIME24), plus multi-seed standard deviations for controller training.
- Add a held-out policy-PRM transfer experiment for A-UATS.
- Specify all baseline hyperparameters and per-policy-size latency / FLOPs; reconcile 'H-UATS w/o Uncertainty' with REBASE.
- Decompose the A-UATS gain into BC-initialization and RL fine-tuning contributions.
- Add an experiment verifying the predicted O(√T ln T) regret scaling.
- Discuss the remaining gap to Oracle Pass@K and characterize when uncertainty cannot close it.
- Soften 'provably minimizes regret' phrasing and explicitly state assumptions.
- Deduplicate Snell et al. 2024a/b in the reference list.

