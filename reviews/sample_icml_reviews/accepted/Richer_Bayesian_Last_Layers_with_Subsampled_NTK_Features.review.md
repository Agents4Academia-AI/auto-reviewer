# Reviewer Agent Report
**Paper file:** `Richer_Bayesian_Last_Layers_with_Subsampled_NTK_Features.pdf`  **Generated:** 2026-06-21T16:03:41.075585Z
---
## Summary of the Paper
The paper introduces Rich-BLL, a post-hoc uncertainty estimation method that enriches Bayesian Last Layers (BLLs) by incorporating contributions from earlier layers through a low-dimensional projection of empirical NTK (eNTK) features onto the span of last-layer features. The earlier-layer Jacobian features are regressed onto last-layer features via closed-form least squares, producing a kernel correction B^T B = L L^T that allows inference to be carried out in the r-dimensional last-layer space at standard BLL cost. A uniform subsampling scheme further reduces cost to depend on the subsample size k rather than the training set size N.

The authors provide several theoretical results: a closed-form r x r predictive covariance via Woodbury and a push-through identity (Thm 3.1-3.2); a proof that Rich-BLL predictive variance is always at least as large as standard BLL when A is the exact solution (Thm 3.3); and matrix-Bernstein-based concentration bounds for both the projection estimator (Thm 3.4) and the subsampled posterior (Thm 3.5), with the latter notably independent of N. Empirical results on UCI regression, the Wheel contextual bandit, CIFAR-10 classification, and OOD detection tasks show consistent improvements over BLL/NNGP and competitive performance versus VBLL, last-layer Laplace, SNGP, and ensembles.
## Recommendation
**weak_accept**  (confidence 4/5)
### Score Card
- Soundness: 3/4
- Presentation: 3/4
- Contribution: 2/4
- Overall: 6/10
### Main Strengths
- Clean and elegant methodological idea: expressing the contribution of earlier-layer eNTK features as a linear projection onto the last-layer feature span, reducing posterior inference to an r x r problem at standard BLL cost.
- Solid theoretical analysis: Theorems 3.1-3.2 give closed-form reductions via Woodbury and a push-through identity; Theorem 3.3 establishes variance dominance over BLL; Theorems 3.4 and 3.5 provide matrix-Bernstein concentration bounds, with the subsampling bound being independent of N.
- Broad empirical evaluation across qualitatively different tasks (UCI regression, Wheel Bandit, CIFAR-10 with SVHN/CIFAR-100 OOD, Wine OOD), with consistent improvements over BLL/NNGP.
- Strong gains in the Wheel Bandit setting (e.g., 21.8 vs 55.8 cumulative regret at delta=0.99), where epistemic uncertainty quality directly drives exploration performance.
- Practical post-hoc method with no retraining required, plus a subsampling extension grounded in theory.
- Appendix B provides an interpretable framework (relative quasi-low-rank residual epsilon_x) connecting the method to a geometric property of the eNTK, and Appendix C describes a scalable computation pipeline using random projections.

### Main Weaknesses
- No quantitative comparison to the full NTK-GP / Linearized Laplace baseline on any real dataset. The central motivation (approximating NTK-GP) is only illustrated via a 1D toy figure (Fig. 1), and even there the match is shown only qualitatively.
- The eNTK low-rank assumption underlying the approach is supported only by spectral plots (Figures 3-4), which actually show that >100-250 eigenvalues are needed to explain 95% of trace. The relevant residual epsilon_x defined in Appendix B is never measured for the actual trained networks.
- The variance-dominance result (Theorem 3.3) holds exactly only when A is the population/exact least-squares solution. Under empirical and subsampled estimation, dominance is only approximate, but the abstract and intro phrase the result unconditionally ('provably greater or equal').
- Theorem 3.5 conditions on a fixed L while in practice L itself is estimated (and possibly subsampled). The joint error from simultaneously estimating L and Sigma is not analyzed.
- Scalability claims are supported only by an asymptotic complexity table; no wall-clock or memory measurements are reported, and the largest experiment is CIFAR-10 (50k examples) on a small CNN.
- The classification extension is presented informally: the choice of global vs class-specific transformation, the use of predicted-class logit variance as OOD score, ridge lambda=1.0, projection dimension q, and per-class subset size 1024 are not ablated or justified, and the regression-style theory does not formally cover this setting.
- Several Wheel Bandit baselines (VBLL, NeuralLinear, LinDiagPost) are imported from Harrison et al. (2024) rather than re-run under matched protocol, introducing a possible confounder.
- Important baselines are missing or only partially included: full LLA/NTK-GP where feasible, KFAC/subnetwork Laplace, and LL-LLA (only listed for image classification, not regression or bandits).

### Detailed Comments
- Sec. 3.2: The derivation is clean, and the push-through identity (Eq. 30) used to avoid inverting the p x p system is a nice technical step. The Cholesky reparameterization in Theorem 3.2 makes the method elegantly implementable, since only L in R^{r x r} needs to be stored. However, the operational sequence -- estimate A from data, form B^T B, then Cholesky -- should be made explicit via pseudocode for reproducibility.
- Sec. 3.2, Theorem 3.3: The dominance result is mathematically correct for exact A, but the abstract phrasing ('provably greater or equal') overstates what holds in practice, where A is estimated. Theorem 3.4 only gives O(1/sqrt(N)) convergence of hat(A) to A; this mismatch should be clearly acknowledged.
- Eq. 9 requires N >= r for Phi_x^{r T} Phi_x^r to be invertible. With subsampling at 30-40% on small UCI datasets like Boston (~500 examples) and r=50, this can leave the regime quite tight; a brief discussion of how the method behaves (and what regularization is used) when k approaches r would be valuable.
- Sec. 3.3, Theorem 3.5: The N-independent bound is a nice observation, but the constant scales as 1/lambda_min(Sigma) and the threshold on k scales as 1/lambda_min(Sigma)^2. For wide last layers (large r), lambda_min(Sigma) can be small, and the practical implication of this dependence is not discussed.
- Appendix B: The framework of the relative quasi-low-rank residual epsilon_x is the right conceptual bridge between spectral decay and Rich-BLL accuracy. It would significantly strengthen the paper to measure epsilon_x empirically for the experimental networks; doing so would directly substantiate the central methodological claim.
- Figures 3-4: The spectra do show concentration, but only ~95% of trace is captured by roughly 100-250 directions in both networks. Whether the last-layer feature span (of dimension r = 50/512) contains these dominant directions is precisely what determines Rich-BLL accuracy, and this is not verified.
- Figure 1: The NTK-GP and Rich-BLL panels look similar qualitatively, but no quantitative comparison (e.g., predictive variance MSE) is reported even on this 1D toy. Adding such a measurement would help substantiate the central claim.
- Table 1: The complexity table omits the one-time cost of computing L, which involves Jacobian extraction with random projection. This should be added or commented on.
- Table 5 (CIFAR-10): Test accuracy is not reported despite being mentioned in the experimental setup; bolding choices are inconsistent. The comparison with Dropout (NLL 0.31) is not strictly apples-to-apples since Dropout requires a different training procedure (stochastic forward passes), whereas Rich-BLL is post-hoc on a deterministic backbone; however, even among post-hoc/single-pass methods, this gap is informative for context. The Ensemble's SVHN AUROC of 0.80 +/- 0.20 has remarkably high variance and should be discussed.
- Table 3 (Wheel Bandit): Rich-BLL (S) outperforms Rich-BLL at delta=0.7 -- is this within noise, or evidence of an implicit regularization effect from subsampling? A brief comment would be helpful.
- Sec. 4.4: The classification setup involves several non-trivial design choices (global vs per-class transformation, ridge lambda, projection dimension q, subset size 1024) that are stated as outcomes of internal comparisons but not quantitatively shown. An ablation table would strengthen the contribution.
- Bandit experiments: The empirical-Bayes noise heuristic ('periodically sets the aleatoric noise variance to the mean of recent squared prediction errors') is potentially impactful and should be ablated against a fixed sigma^2 to ensure the gains are not driven primarily by this device.
- Minor: arXiv IDs starting '2602.*' appear future-dated (likely a typo for 2502 or 2602 should be checked); the muTransfer reference is formatted as a non-standard 'Microsoft Research, 8, 2022'.

### Questions for Authors
- Can you quantitatively compare Rich-BLL's predictive covariance to the full NTK-GP / LLA on at least small/medium datasets (UCI), to validate the central approximation claim beyond the 1D toy figure?
- What are the measured values of the residual epsilon_x and epsilon_{x'} (Appendix B) for the trained MLP and CNN in your experiments? Are they small enough to support the linear-projection assumption?
- How does variance dominance over BLL (Theorem 3.3) hold empirically when A is estimated via subsampling rather than exact least-squares? Can the theorem be extended to this realistic regime?
- Can you provide a joint concentration bound covering simultaneous estimation of L and Sigma from data, rather than treating L as fixed in Theorem 3.5?
- What are the wall-clock and memory costs of Rich-BLL (including the preprocessing to compute L via random projection) compared to BLL, VBLL, last-layer Laplace, and full LLA?
- What projection dimension q (Appendix C) was used in the CIFAR-10 experiments, and how sensitive are the results to this choice?
- Why was a single global transformation chosen over class-specific ones for classification? Can you provide a quantitative comparison?
- How does the method scale to larger datasets (e.g., ImageNet) and modern architectures (ResNet, ViT)? Are there fundamental obstacles?
- Were the borrowed Wheel Bandit baselines (VBLL, NeuralLinear, LinDiagPost) verified under your protocol? How would they compare if re-run locally with the same noise heuristic?
- How sensitive is performance to sigma^2, ridge lambda, last-layer width r, and the choice of muP vs standard parameterization?
- How does the empirical-Bayes noise heuristic in the bandit experiments affect Rich-BLL versus baselines? Is the regret gap preserved with a fixed sigma^2?
- How does the method behave when the subsample size k is close to r (which can occur in small UCI datasets at low subsampling ratios)? Is any regularization applied?

### Suggestions for Improvement
- Add a quantitative comparison against the full NTK-GP / LLA on at least the UCI regression datasets (and ideally on a small image-classification setup), reporting both predictive uncertainty and computational cost.
- Empirically measure the residual epsilon_x defined in Appendix B for the trained networks, ideally as a function of the last-layer width r, to directly support the linear-projection assumption.
- Sharpen Theorem 3.3's framing in the abstract and introduction: state precisely that exact dominance holds for the population estimator A, and quantify (or empirically illustrate) how subsampling-based estimation may temporarily violate this property.
- Extend the concentration analysis to cover joint estimation of L and Sigma, or at least discuss the qualitative effect.
- Provide wall-clock and memory measurements for Rich-BLL (including the L-computation pipeline) versus BLL, VBLL, LL-Laplace, and full LLA on at least one task.
- Add ablations on the projection dimension q, ridge lambda, last-layer width r, sigma^2, and on the global vs class-specific transformation choice for classification.
- Include pseudocode for Rich-BLL and Rich-BLL (S), and report test accuracy for CIFAR-10 in Table 5; reconsider bolding choices.
- Re-run the Wheel Bandit baselines under matched protocol, or at minimum discuss the protocol differences with Harrison et al. (2024).
- Add LL-LLA / KFAC Laplace baselines for regression and bandit experiments, since they are natural competitors at comparable cost.
- Verify and fix arXiv ID formatting (e.g., '2602.*' entries) and reference formatting for muTransfer.
- Discuss the regime where k is close to r, which arises in small UCI datasets at low subsampling ratios.

### Improvement Checklist
- Provide a quantitative comparison to the full NTK-GP / LLA on UCI (and ideally a small image task), reporting predictive variance match and computational cost.
- Empirically measure the Appendix B residual epsilon_x (train and test) for the trained MLP and CNN backbones used in the experiments.
- Soften the wording of variance dominance (Thm 3.3) in the abstract/intro to reflect that it is exact only for the population A, and add empirical evidence that the property holds in practice under estimation/subsampling.
- Extend or discuss the joint concentration of L and Sigma in Theorem 3.5.
- Report wall-clock and memory measurements, including the cost of computing L (Appendix C pipeline), against BLL, VBLL, LL-Laplace, and LLA where feasible.
- Add ablations: projection dimension q, ridge lambda, last-layer width r, sigma^2, global vs class-specific transformation for classification, and effect of the empirical-Bayes noise heuristic in bandits.
- Add pseudocode for Rich-BLL and Rich-BLL (S); include CIFAR-10 test accuracy in Table 5 and revise bolding for consistency.
- Re-run or clearly disclose protocol differences for the borrowed Wheel Bandit baselines.
- Add LL-LLA / KFAC Laplace baselines for regression and bandits.
- Discuss the small-k regime (k close to r) for small UCI datasets and any regularization needed.
- Fix reference formatting issues (apparently future-dated arXiv IDs, non-standard muTransfer entry).

