# Reviewer Agent Report
**Paper file:** `Revisiting_the_Platonic_Representation_Hypothesis_An_Aristotelian_View.pdf`  **Generated:** 2026-06-21T16:05:25.483186Z
---
## Summary of the Paper
The paper identifies two systematic confounders that distort representational similarity comparisons across neural networks: (i) a width-driven non-zero null baseline for spectral metrics like CKA that scales as O(d/n), and (ii) a depth-driven multiple-comparisons inflation when summarizing layer-pair similarities via max/top-k operators. The authors derive these effects theoretically (Propositions 4.1, 4.2, and a sub-Gaussian maximal inequality for the depth confounder) and propose a unified, metric-agnostic permutation-based null-calibration framework. The framework transforms any raw similarity into a bounded calibrated effect size with finite-sample super-uniform p-values, and an aggregation-aware variant calibrates the entire reported summary statistic by applying consistent permutations across layers.

The authors then revisit the Platonic Representation Hypothesis (PRH) using their calibration. Across 204 vision–language model pairs (plus a video–language extension), the global spectral convergence trend in raw CKA largely vanishes after calibration, whereas local neighborhood metrics (mKNN, cycle-kNN, CKNNA) retain a scaling trend (with family-dependent strength). A locality analysis (varying mKNN's k and CKA-RBF's bandwidth) suggests that the persistent alignment is topological (neighbor identity) rather than metric (exact local distances), motivating a refined claim: the Aristotelian Representation Hypothesis, that networks converge to shared local neighborhood relationships.
## Recommendation
**Accept (with revisions). The paper makes a principled, technically sound, and broadly useful methodological contribution and applies it to a high-profile open question with substantive findings. Several interpretive claims—particularly the topological-vs-metric distinction and the strong 'convergence' language—would benefit from additional baselines, direct probes, and quantitative analyses on real data, but no concern rises to the level of a fatal flaw.**  (confidence 4/5)
### Score Card
- Soundness: 3/4
- Presentation: 3/4
- Contribution: 3/4
- Overall: 7/10
### Main Strengths
- Identifies and clearly characterizes two real and important confounders (width-driven O(d/n) null baselines and depth-driven look-elsewhere inflation) that undermine cross-scale representational similarity comparisons.
- Provides a unified, metric-agnostic permutation calibration framework with finite-sample super-uniformity guarantees (Lemma D.2, Corollary 5.1), and a non-trivial aggregation-aware extension that calibrates the entire reported max/top-k statistic via consistent layer-wise permutations rather than per-entry calibration.
- Theoretical results (Propositions 4.1, 4.2, D.6, D.9) are correct, clearly stated, and tightly connected to the empirical methodology.
- Thoughtful design distinction between rank-based, monotone-invariant permutation p-values and an explicitly non-monotone-invariant calibrated effect size, with a clear rationale for why a rank-invariant calibration cannot correct scale-dependent baselines.
- Table 1 (Appendix B) provides a clean positioning against prior debiasing approaches (Murphy et al., Chun et al., Cui et al., Diedrichsen et al., Cai et al., Smilde et al.), making explicit that prior corrections are metric-specific while this framework is metric-agnostic and additionally handles selection inflation.
- Empirical validation is thorough: controlled synthetic Type-I/power experiments across multiple metric families and noise distributions, agreement with Murphy et al.'s analytical debiased CKA on synthetic data, a large-scale PRH re-evaluation across 204 vision–language pairs, and a video–language extension.
- Robustness ablations across α, permutation budget K, neighborhood size k, and RBF bandwidth strengthen the central qualitative finding that global spectral scaling vanishes after calibration while local neighborhood scaling persists.
- Clean pseudocode (Algorithms 1, 2) and released code lower adoption barriers; the framework is practically usable and likely to influence reporting practices.
- The reframing into the Aristotelian Representation Hypothesis (topological rather than metric agreement) is a substantively meaningful refinement of an influential prior claim.

### Main Weaknesses
- On the actual PRH data, calibrated CKA is not directly compared against existing analytical bias corrections (Murphy et al., Chun et al., Song et al.'s unbiased CKA). The agreement is shown only on synthetic data, leaving open whether the disappearance of global convergence is specific to the permutation null or also holds under analytical debiasing.
- Proposition 4.1 derives the expected null Frobenius energy E[||C̃||_F^2] of the cross-covariance, but the O(d/n) baseline statement for CKA itself is informal: CKA is a ratio of random quantities and E[ratio] ≠ ratio of expectations, so the headline scaling claim for CKA is justified heuristically rather than proved.
- Assumption D.5's sub-Gaussian parameter σ ≤ (s_max−s_min)/2 from Hoeffding is loose and likely does not reflect realistic right-tail behavior of CKA across correlated layer pairs, so the √log M depth inflation bound is qualitatively informative but not tight.
- The strong-form 'convergence' language in the Aristotelian Representation Hypothesis is not operationally defined. Calibrated mKNN values remain modest (~0.10–0.20) with gradual upward trends consistent with persistent alignment but not strong-sense convergence to a shared limit.
- The 'topological vs metric' interpretation rests largely on small-bandwidth (σ=0.1) CKA-RBF showing no calibrated alignment, but at σ=0.1 raw scores saturate near 1.0, which complicates the interpretation. No direct test (e.g., local distance rank correlation or local Procrustes within k-neighborhoods) is provided.
- Missing baselines on PRH: no untrained/randomly-initialized model controls, no within-modality (vision–vision, language–language) controls, and no direct comparison with Ding et al. (2021)'s permutation-based similarity testing.
- Confidence intervals/bootstrap variability on calibrated scores and quantitative slopes for the 'scaling trend persists' versus 'flattens' claims are not reported, leaving these claims qualitative.
- Sample size n=1024 places PRH experiments in a high-d/n regime where calibration corrections are largest. Robustness to larger n on actual model data is not demonstrated.
- The video–language extension relies on a single encoder family (VideoMAE, three sizes); the 'bottleneck' interpretation of smaller encoders is speculative without further encoder families.

### Detailed Comments
- Section 4.1: The informal claim that linear CKA's null baseline scales as O(d/n) glosses over (i) the behavior of the denominator (||Σ_XX||_F · ||Σ_YY||_F) and (ii) the fact that CKA is a ratio of random quantities, so the energy calculation does not directly yield E[CKA] under H_0. A short additional argument (e.g., concentration of the denominator) would tighten the claim.
- Section 5.1: The asymmetry between calibrated scores (α-dependent, not monotone-invariant) and p-values (rank-based, monotone-invariant) is acknowledged briefly but deserves more emphasis to prevent readers from misinterpreting effect-size plots across metrics.
- Section 6.3 and Figures 6, 7: The qualitative judgments 'no systematic increase with scale' (global) versus 'retains alignment trend' (local) would be more convincing with regression slopes, confidence intervals, or a formal scaling-trend test. Note that the local trend is clearer for some vision families (DINOv2, CLIP) than for others (MAE, INet21K).
- Section F.9 (locality analysis): The RBF bandwidths σ ∈ {0.1, 0.5, 2.0, 5.0} are not justified relative to the feature scales of the underlying representations. Reporting median-heuristic bandwidths or feature norm statistics would clarify whether σ=0.1 reflects an extremely under-smoothed kernel rather than a 'truly local' geometric probe.
- Aggregation-aware calibration: The illustration that naive entry-wise calibration still inflates the max (Figure 5) is a particularly clarifying result and could be highlighted more prominently as it directly contradicts a natural practitioner instinct.
- Section 6.3: The framing should make clear that Huh et al.'s local mKNN scaling result is qualitatively preserved after calibration (with family-dependent strength), while their global CKA-based convergence claim is the one overturned. This nuance is important for an accurate accounting of what the work refines versus refutes.
- Section A (Limitations): The mention of restricted permutations under non-exchangeable structure (e.g., topic clusters in WIT) is appropriate but not empirically tested; a block-restricted permutation ablation would strengthen Section 6.3.
- Choice of distance for mKNN (Euclidean vs cosine) and feature normalization can materially affect both spectral and neighborhood metrics; an ablation would address an obvious practitioner concern.
- Figure 2(a) is somewhat dense; axis labels and the relationship between subpanels could be clarified to make the visual claim about width inflation more legible.

### Questions for Authors
- On the actual PRH data, how does calibrated CKA compare to Murphy et al.'s debiased CKA, Chun et al.'s dep-cols CKA, and Song et al.'s unbiased CKA? Does the disappearance of global scaling reproduce under these analytical corrections, or is it specific to the permutation null?
- Can you provide quantitative slopes (with confidence intervals) of calibrated mKNN versus language model capability for each vision family, to substantiate the 'scaling trend persists' claim quantitatively, especially given the apparent family dependence?
- Beyond the energy calculation in Proposition 4.1, can you provide a direct argument (or empirical check on real model representations) that the null expectation of CKA itself scales as O(d/n)?
- What do calibrated CKA and mKNN look like for untrained or randomly initialized vision/language models as baseline controls, and for within-modality comparisons (vision–vision, language–language)?
- How sensitive are the locality conclusions (Section F.9) to feature normalization and to median-heuristic RBF bandwidth selection? Could the σ=0.1 result reflect kernel saturation rather than absence of metric agreement?
- Does the local-vs-global pattern persist at substantially larger n (e.g., 4096, 8192), where d/n is smaller and width confounding is intrinsically milder?
- Have you tested restricted/block permutations to address possible topic clustering in WIT? Do results change materially?
- Could you complement the topological-vs-metric claim with a direct test such as local distance rank correlation or local Procrustes alignment within k-neighborhoods?
- How would you formally define 'convergence' in the Aristotelian Representation Hypothesis (e.g., a limit object, a slope threshold for scaling, or a fixed-point characterization)?
- For the video–language extension, would additional video encoder families (e.g., VideoSwin, V-JEPA) corroborate the 'smaller encoders act as a bottleneck' interpretation?

### Suggestions for Improvement
- Add a direct comparison on the actual PRH data between calibrated CKA and existing analytical debiasing methods (Murphy et al., Chun et al., unbiased CKA). This would substantially strengthen the claim that global convergence is a confounding artifact rather than a permutation-specific phenomenon.
- Tighten Section 4.1 by either (a) deriving the null expectation of CKA directly or (b) clearly labeling the O(d/n) statement as a heuristic for the numerator energy, with empirical verification on synthetic data of E[CKA] under H_0.
- Include untrained-model and within-modality baselines on the WIT/PRH setup to anchor the magnitude of calibrated scores.
- Report regression slopes with bootstrap confidence intervals for calibrated alignment versus model capability, and add a formal scaling-trend test (e.g., null of zero slope) to make the local-vs-global contrast quantitative; explicitly acknowledge vision-family-dependent strength of the local trend.
- Strengthen the topological-vs-metric distinction by adding a direct probe such as local distance rank correlation (Spearman of distances within k-neighborhoods) or local Procrustes, instead of relying solely on small-σ CKA-RBF behavior.
- Justify RBF bandwidth choices via median heuristic or feature-norm statistics, and ablate over feature normalization and distance metric (Euclidean vs cosine) for mKNN.
- Operationalize 'convergence' in the Aristotelian Representation Hypothesis (e.g., a specified scaling-law form, a limiting object, or an explicit non-trivial slope criterion) so the hypothesis becomes empirically falsifiable.
- Test restricted/block permutations on WIT to address possible non-exchangeability from topic clustering.
- Repeat the PRH experiment at larger n where computationally feasible to demonstrate robustness outside the high-d/n regime.
- Emphasize more clearly in the main text that Huh et al.'s mKNN-based local convergence finding is qualitatively preserved after calibration, so that readers do not misread the contribution as overturning PRH wholesale.
- Add a brief subsection in the main text discussing the α-dependence and non-monotone-invariance of s_cal alongside the monotone-invariance of p-values.

### Improvement Checklist
- Compare calibrated CKA against Murphy et al., Chun et al., and unbiased CKA on actual PRH (image–text and video–text) data, not only synthetic.
- Tighten the theoretical link between the null Frobenius energy (Proposition 4.1) and the null expectation of CKA itself (a ratio of random quantities); either prove a direct statement or label the O(d/n) baseline as heuristic and verify empirically.
- Add untrained/randomly-initialized model controls and within-modality (vision–vision, language–language) controls to the PRH experiments.
- Report regression slopes with bootstrap confidence intervals for calibrated alignment vs model capability, with a formal test of zero slope, and explicitly discuss the vision-family-dependent strength of the local trend.
- Provide a direct test of the topological-vs-metric distinction (e.g., local distance rank correlation, local Procrustes within k-neighborhoods) rather than relying on small-σ CKA-RBF.
- Justify RBF bandwidth and distance/normalization choices via median heuristic and feature-norm statistics; ablate Euclidean vs cosine for mKNN.
- Operationalize 'convergence' in the Aristotelian Representation Hypothesis with a concrete falsifiable criterion.
- Run block-restricted permutations on WIT to address potential non-exchangeability from topic clustering.
- Where feasible, demonstrate robustness at larger n to show the local-vs-global pattern is not a small-sample artifact.
- Add a main-text emphasis that Huh et al.'s local mKNN scaling claim is qualitatively preserved after calibration (with family-dependent strength), while their global CKA claim is overturned.
- Add a clear main-text discussion of α-dependence and non-monotone-invariance of s_cal versus rank-invariance of p-values.
- Improve clarity of Figure 2(a) labeling and consider highlighting Figure 5's entry-wise-calibration counterexample more prominently in the main text.

