# Reviewer Agent Report
**Paper file:** `stochastity.pdf`  **Generated:** 2026-06-19T05:19:18.649170Z
---
## Summary of the Paper
The paper proposes Deformable Convolution with Stochasticity (DCS), a structural random defense that replaces a standard convolution with a deformable convolution whose offsets are drawn as random binary masks selecting n out of k×k positions. Because the randomness is parameterized by data-independent hyperparameters (n, k, stride S), the authors argue it avoids the per-dataset tuning required by additive-noise random defenses. They decompose pixel-level gradient cosine similarity between two sampled inference paths into shared (X^s), neighborhood (X^g), and unsampled (X^u) point contributions, and derive an upper bound n ≤ S²ε_c (Lemma 1) for low gradient similarity and a lower bound on n (Lemma 2) from an L1 output-distance argument, yielding a feasible range for n. They additionally propose Gradient-Selective Adversarial Training (GSAT), which masks X^s points during AT. Experiments on CIFAR-10/100 (ResNet-18, WRN-34) and ImageNet (ResNet-50) report large gains over Conv/DCN baselines under PGD, AutoAttack, CW, MIFGSM, DeepFool, EOTPGD, and several black-box/adaptive attacks; a brief ViT-tiny extension is also reported.
## Recommendation
**Reject**  (confidence 4/5)
### Score Card
- Soundness: 2/4
- Presentation: 2/4
- Contribution: 2/4
- Overall: 4/10
### Main Strengths
- Conceptually clean idea: leveraging deformable convolutions with random masks to obtain structural randomness whose hyperparameters are decoupled from data statistics.
- Novel analytical decomposition of pixel-level gradient cosine similarity into X^s/X^g/X^u contributions, providing a useful lens on transferability between sampled inference paths.
- Attempts to formalize the robustness-vs-clean-accuracy trade-off via two-sided bounds on the receptive field n, giving principled hyperparameter guidance.
- Broad empirical scope: multiple datasets, backbones, white-box and black-box attacks, adaptive evaluations (BPDA, BPDA+EOT), and an exploratory ViT extension.
- GSAT is a sensible algorithmic instantiation of the theoretical decomposition, and inference overhead is modest (~1.1×).

### Main Weaknesses
- Evaluation shows patterns consistent with obfuscated/masked gradients under a stochastic defense. Most notably, in Table 1, AutoAttack accuracy exceeds PGD20 in several rows (e.g., CIFAR-10/RN18 73.41 AA vs 72.10 PGD; CIFAR-100/WRN34 52.36 AA vs 48.05 PGD), which contradicts AA's design property of being at least as strong as PGD and is a known signature of insufficient EOT under randomized defenses. The very large DeepFool gains (~5%→~88%) are also suggestive (though not by themselves diagnostic) of gradient masking.
- Critical evaluation details for a randomized defense are unspecified: the AutoAttack variant (standard vs rand), the number of EOT samples used for APGD/FAB, and the BPDA surrogate and EOT count.
- 'Data independence' is overstated. Lemma 2's lower bound depends on feature-map size N and on worst-case substitutions (∆g=1, C^g=1) of data-dependent quantities; in practice, n and k are still chosen via grid search (App. B.3).
- The Lemma 1 proof drops the cross-term contribution by assuming Cos(∂X^u/∂y, ∂'X^u/∂'y)=0; in deep residual networks gradients to unsampled positions are typically nonzero through skip connections and subsequent layers, so the bound may not faithfully bound full-network gradient similarity.
- SOTA comparisons in Table 2 mix heterogeneous backbones and training-data regimes (e.g., DiffAT/AdvWRN use diffusion-generated data) without normalization, making the SOTA claim hard to verify, and matched-protocol baselines (TRADES, MART, Random Normalization Aggregation) on the same backbone/AT schedule are missing.
- Reproducibility issues: the text inconsistently states DCS replaces the 'second' (Sec. 5.1) vs 'third' (CIFAR setup) convolution; mask sampling distribution (per sample / per location / channel-shared?) is underspecified.
- The ViT extension is supported by a single PGD number with no AA or adaptive evaluation.

### Detailed Comments
- The Lemma 1 derivation drops gradient contributions through unsampled positions. In a deep residual network, gradients to X^u positions are typically nonzero through skip connections and downstream layers, so the bound is not a faithful upper bound on gradient cosine similarity in the full network.
- 'A normal m×m convolution is a special case where k=n=m²' confuses kernel area with linear kernel size; please clarify notation throughout.
- Eq. 12 combines an upper bound that decreases with smaller n and a lower bound that depends on N. For typical CIFAR feature maps the feasible range is likely wide, weakening the claim that the bounds tightly determine n.
- Table 1 reports large standard deviations (±2-4%) on robust metrics; significance tests or CIs would strengthen the comparisons.
- The claim that random defenses 'seldom study' the natural-vs-robust trade-off underplays substantial prior work on TRADES/MART and certified-smoothing trade-offs.
- Figure 4b is hard to interpret due to axis scaling.
- App. B.1's explanation of GSAT instability is qualitative and somewhat circular.
- Table 6 reports defenses against BPDA/BPDA+EOT that match or exceed several white-box numbers, which warrants a more carefully tuned adaptive attack.

### Questions for Authors
- Was AutoAttack run in the 'rand' variant for the stochastic model? How many EOT samples were used for APGD and FAB? Could you report PGD with EOT≥20 over mask resampling?
- How do you reconcile AutoAttack accuracy exceeding PGD20 accuracy in multiple Table 1 rows with AA being at least as strong as PGD by construction?
- For BPDA, what surrogate is used to backpropagate through the random mask, and how many EOT samples are used in BPDA+EOT?
- Given S, k, and ε_c used in CIFAR experiments, what is the numerical feasible range from Eq. 12, and does n=2 lie strictly inside it? In particular, for stride-1 replaced layers, what value of ε_c does n=2 correspond to?
- Could you report DCS without AT vs Conv without AT to isolate the contribution of structural randomness from AT?
- How exactly is the mask sampled — once per forward pass, per spatial location, shared across channels and within a batch?
- Can you provide a matched-backbone, matched-data comparison with TRADES, MART, and Random Normalization Aggregation, evaluated under EOT-AutoAttack?
- In what sense is Lemma 2's feasible range 'data independent' given its dependence on N, ∆g, and worst-case substitutions?

### Suggestions for Improvement
- Run AutoAttack-rand and PGD with substantial EOT (e.g., 20–100 samples) and report per-attack numbers; this is essential for randomized defenses following Athalye et al. and Tramèr et al.
- Add a strong adaptive BPDA+EOT evaluation with clearly specified surrogate gradients and EOT count.
- Normalize SOTA comparisons by backbone and training-data regime; separate methods that use extra synthetic data.
- Add matched-protocol comparisons with TRADES/MART/RNA on the same backbone and AT schedule.
- Tighten the framing of 'data independence' to acknowledge dependence on feature-map size and worst-case substitutions.
- Clarify reproducibility details: which layer is replaced, mask sampling distribution and pseudo-code, hyperparameter grid for ViT.
- Report significance tests or confidence intervals for headline comparisons given the large reported variance.
- For the ViT extension, report AA and adaptive results, not only PGD.

### Improvement Checklist
- Report AutoAttack-rand with explicit EOT counts; explain AA<PGD inversions in Table 1.
- Specify BPDA surrogate and EOT samples; rerun adaptive attacks with stronger settings.
- Provide pseudo-code for mask sampling (granularity, sharing across channels/batch).
- Resolve inconsistency about which conv layer is replaced (second vs third).
- Add matched-protocol comparisons to TRADES/MART/RNA on identical backbones/data.
- Separate SOTA table by extra-data regime; avoid mixing diffusion-augmented methods with vanilla AT.
- Numerically instantiate Eq. 12 for the experimental settings to show n=2 satisfies both bounds.
- Clarify treatment of skip-connection gradients in Lemma 1.
- Report AA and adaptive results for the ViT extension.
- Add CIs/significance tests given ±2–4% variance on robust accuracy.

