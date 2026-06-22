# Reviewer Agent Report
**Paper file:** `Variational_Learning_Induces_Adaptive_Label_Smoothing.pdf`  **Generated:** 2026-06-21T16:03:31.805527Z
---
## Summary of the Paper
The paper draws an explicit connection between variational learning with Gaussian posteriors and adaptive label smoothing. The authors prove that variational GD on logistic regression with q = N(θ_t, I) is exactly equivalent to standard GD with per-example label noise ε_{i|t} = σ(f_i(θ_t)) − E_{q_t}[σ(f_i(θ))] (Theorem 1), extend the result to general GLM losses by replacing σ with the log-partition derivative A' (Eq. 16), and to Newton/VON updates with learned full covariance Σ_t (Theorem 2, App. A.1). For neural networks, they derive an approximate form (Eq. 20) using a single-sample Monte Carlo and first-order Taylor expansion. The induced noise grows for atypical examples whose predictions sit near the decision boundary and have high predictive variance. Empirically, the authors show that (i) IVON assigns higher label noise to atypical MNIST digits (Fig. 3), (ii) its per-class smoothed-label distributions on CIFAR-10/100 visually resemble Online Label Smoothing (Fig. 4), and (iii) IVON consistently outperforms best-tuned LS and matches/beats best-tuned SAM on CIFAR-10/100 (symmetric, pair-flip, data-dependent noise) and Clothing1M. Ablations show learned Σ_t outperforms a fixed diagonal Σ_t (Fig. 6), and IVON appears less sensitive to its Hessian initialization than SAM is to its perturbation radius (Fig. 10).
## Recommendation
**weak accept**  (confidence 4/5)
### Score Card
- Soundness: 3/4
- Presentation: 3/4
- Contribution: 2/4
- Overall: 6/10
### Main Strengths
- Clean conceptual contribution that unifies two largely separate literatures (Bayesian deep learning and adaptive label smoothing) by reinterpreting the expected gradient under a Gaussian posterior as adaptive per-example label noise, with pedagogical value in subsuming several prior heuristic adaptive-LS schemes under a single principled objective.
- Theorem 1 and the GLM extension (Eqs. 10, 16) are correct, clearly derived, and yield exact closed-form expressions for the induced label noise in linear/GLM settings.
- The Newton/VON extension (Theorem 2, App. A.1) elegantly shows that learning Σ_t makes the induced noise adaptive in both location and spread, with empirical support from the fixed-vs-learned Σ ablation (Fig. 6).
- Empirical results are consistent in direction across multiple noise types (symmetric, pair-flip, data-dependent, natural) and datasets (CIFAR-10/100, Clothing1M), with comparisons against best-tuned LS and SAM and reporting over 5 seeds.
- The data-dependent noise diagnostic (Fig. 7) is a useful experiment showing striking robustness of IVON in high-noise regimes where LS and SAM collapse to near-chance.
- The hyperparameter-sensitivity comparison (Fig. 10 vs. SAM's ρ sweeps in Figs. 5, 8, 9) supports the practical claim that IVON is less brittle to its main tuning knob than SAM, and the included IVON pseudo-code (Alg. 1) plus an explicit separation of label vs. other induced noises aids interpretability.

### Main Weaknesses
- The most conceptually relevant baseline, Online Label Smoothing (Zhang et al., 2021), is only included for a visual similarity check (Fig. 4) and absent from all accuracy benchmarks. Other adaptive LS methods (Ko et al. 2023; Lee et al. 2022; Park et al. 2023) and standard noise-robust methods (GCE, SCE, ELR, Co-teaching, DivideMix) are not compared, despite being natural baselines, especially on Clothing1M.
- The neural-network derivation (Eq. 20) relies on single-sample MC plus a first-order Taylor expansion with second-order terms dropped, and is never empirically validated. There is no check that the analytic formula approximates the realized noise induced by IVON, and the decomposition into 'label noise' vs. feature/weight noise is non-unique.
- The 'no hyperparameter tuning' framing (Sec. 3.4, 4.3.1) is in tension with Table 1, which shows per-setting tuning of learning rate, Hessian init, and weight decay for IVON. Fig. 10 also shows IVON's accuracy varies substantially with Hessian init in some settings (e.g., pair-flip 20% collapses near h_0=0.05); the caption's hedge ('bigger than 0.05') is technically consistent but understates this sensitivity at the boundary.
- The introduction motivates miscalibration, OOD detection, and distribution shift, but the experiments cover only labeling errors. No calibration metrics (ECE, NLL, Brier) or OOD evaluations are reported despite the overconfidence framing.
- The 'surprisingly similar' OLS-IVON claim (Fig. 4) is based on log-scale bar plots for selected classes only; no quantitative similarity measure (KL divergence, rank agreement) is provided across all classes.
- Statistical reporting is limited: figures report mean accuracy over 5 seeds but error bars/confidence intervals and significance tests are not clearly visible or reported numerically.
- The headline '~51%' improvement on data-dependent noise occurs in a regime where baselines collapse to ~10% (near chance); presenting this as a general benefit may overstate the practical gain in moderately noisy regimes.
- On Clothing1M, the IVON gain over LS is only ~1%, and the LS baseline appears low relative to commonly reported numbers in the noisy-label literature, which may inflate the relative improvement.
- The novelty is primarily a reinterpretation/unification rather than a new algorithm: that variational/Bayesian objectives induce expected-gradient terms equivalent to soft labels is implicit in prior Bayesian deep learning and PAC-Bayes work. There is also no formal generalization or noise-robustness guarantee establishing when the induced adaptivity is provably beneficial.

### Detailed Comments
- Sec. 3.1: The proof of Theorem 1 is clean, but the regularity conditions for swapping expectation and gradient in Eq. 11 are left implicit. Stating them (e.g., differentiability and dominated convergence) would improve rigor.
- Sec. 3.3 / App. A.1: Theorem 2's proof is asserted to be 'identical' to Theorem 1's. Given that Σ_t is now learned and full, a complete derivation (even brief) would make the result self-contained.
- Sec. 3.4: The comment after Eq. 14 that the Taylor approximation 'does not get better for larger number of samples' is confusing and deserves clarification—presumably it refers to bias not vanishing with more MC samples rather than variance reduction.
- Sec. 4.1, Fig. 3: The MNIST visualization is illustrative but anecdotal. A quantitative measure (e.g., correlation between noise magnitude and predictive entropy, or model confidence on a separately validated 'atypicality' score) would strengthen the claim.
- Sec. 4.2, Fig. 4: The OLS-IVON similarity claim would be far more convincing with a quantitative aggregate metric (e.g., mean KL divergence between per-class smoothed-label distributions across all classes, not just selected ones).
- Sec. 4.3.1: Pair-flip class ordering in CIFAR-10 appears to follow class index rather than semantic similarity (a more common convention in the noisy-label literature). This may affect comparability with prior work; clarifying this choice is important.
- Sec. 4.3.2 / Fig. 7: The construction of P with κ + βi for i ∈ [1, K] means class K-1 has noise level κ + β(K-1), which for κ=0.4 and β=0.05 on CIFAR-10 exceeds 0.85, i.e., the last class is essentially unlearnable. The framing should distinguish gains in moderately noisy regimes from gains in essentially-random-label regimes.
- Sec. 4.3.3 / Fig. 9: A ~1% improvement on Clothing1M is a modest result. Reporting standard noise-robust baselines (e.g., GCE, ELR, DivideMix) would contextualize this.
- Fig. 6: The ablation is valuable, but the fixed-Σ baseline could also be shown across multiple variance scales chosen by validation, and the figure would benefit from clarifying which axes correspond to which dataset.
- App. B.1: Fig. 10's caption that variation is bounded by ~10% holds only when h_0 > 0.05; the sharp collapse at h_0=0.05 in the pair-flip curve should be acknowledged explicitly.
- Reproducibility: No code release is mentioned. Per-seed numerical results, code, and exact hyperparameters for all experiments (not just Table 1) would substantially improve reproducibility.
- Minor typos: 'variational method natural yields' (should be 'naturally yields'); 'mislabling'; 'neworks'; duplicated Pereyra et al. (2017a/b).

### Questions for Authors
- Why is Online Label Smoothing—the conceptually closest method—omitted from the accuracy benchmarks in Sec. 4.3? Can you add OLS (and other adaptive LS variants like ACLS and Ko et al. 2023) to all noisy-label experiments?
- Can you empirically verify that Eq. 20 approximates the actual difference E_q[∇ℓ_i] − ∇ℓ_i(θ_t) that IVON induces during NN training, e.g., by comparing realized label-noise magnitudes to the analytic prediction across training?
- Given the per-setting tuning of learning rate, Hessian init, and weight decay in Table 1, how do you reconcile the claim that IVON 'does not require hyperparameter tuning'? Would the gains over LS/SAM shrink under comparable per-setting tuning of those baselines?
- Can you report ECE/NLL/Brier scores for IVON, LS, and SAM to substantiate the overconfidence/calibration framing in the introduction?
- How sensitive are the OLS-IVON similarity conclusions (Fig. 4) to quantitative metrics such as mean KL divergence between smoothed-label distributions over all classes?
- On Clothing1M, how does IVON compare to standard noise-robust baselines (GCE, SCE, ELR, DivideMix), and what was the tuning protocol for the LS baseline?
- Do you have a direct ablation between variational GD (fixed identity covariance) and IVON in the NN setting to support the claim that second-order variational methods are more adaptive than first-order ones?
- Does combining LS or OLS with IVON yield further gains, or are the effects redundant?
- What is the rationale for using the class-index-based pair-flip ordering in CIFAR-10 rather than the semantically-motivated pairs used in much prior work?

### Suggestions for Improvement
- Add accuracy comparisons against OLS and at least one other adaptive LS method (ACLS or Ko et al. 2023) across all noisy-label settings; also include standard noise-robust baselines on Clothing1M.
- Empirically validate Eq. 20 by measuring the realized noise during IVON training and comparing it to the analytic prediction; this would substantiate the NN-level theoretical claim.
- Soften or qualify the 'no hyperparameter tuning' framing, and clearly disclose tuned hyperparameters (Table 1) in the main text rather than only in the appendix.
- Report calibration (ECE, NLL) and—if feasible—an OOD experiment, to back the overconfidence motivation in the introduction.
- Replace or supplement Fig. 4 with a quantitative aggregate similarity metric (e.g., KL or correlation) between IVON and OLS smoothed-label distributions across all classes.
- Add error bars / confidence intervals and at least one paired significance test for headline gains; report per-seed numbers in the appendix.
- Reframe the data-dependent noise result by distinguishing high-noise regimes where baselines reach chance from regimes where they are competitive; consider intermediate κ to show transitions.
- Provide a complete proof of Theorem 2 (rather than appealing to Theorem 1) and state the regularity conditions used in Eq. 11.
- Consider adding a formal result (e.g., generalization or noise-robustness bound) characterizing when variational-induced adaptive smoothing is provably beneficial.
- Release code and exact training configurations to enable reproduction.
- Fix typos and clarify the Fig. 10 caption about behavior at the h_0=0.05 boundary.

### Improvement Checklist
- Add OLS and at least one other adaptive LS baseline (ACLS, Ko et al. 2023) to all accuracy benchmarks in Sec. 4.3.
- Add standard noise-robust baselines (GCE, SCE, ELR, DivideMix) on Clothing1M and re-tune the LS baseline.
- Empirically validate the NN-level label-noise expression in Eq. 20 against realized noise during IVON training.
- Soften the 'no hyperparameter tuning' framing and surface Table 1 hyperparameters in the main text.
- Report calibration metrics (ECE, NLL, Brier) and, if possible, an OOD experiment.
- Replace selected-class log-scale Fig. 4 with a quantitative similarity metric (e.g., mean KL) between OLS and IVON smoothed labels across all classes.
- Add error bars/confidence intervals across 5 seeds and significance tests for headline claims; provide per-seed numbers in the appendix.
- Reframe the ~51% data-dependent noise improvement in context of baseline collapse to near chance; include intermediate κ to show transitions.
- Provide a self-contained proof of Theorem 2 and state regularity conditions used in Eq. 11.
- Add ablation: variational GD with identity covariance vs. IVON in the NN setting.
- Clarify the pair-flip class ordering choice and its relation to prior conventions.
- Release code and full training configurations for all experiments.
- Fix typos ('naturally yields', 'mislabeling', 'networks', duplicated Pereyra refs) and clarify Fig. 10 caption regarding behavior at h_0=0.05.

