# Reviewer Agent Report
**Paper file:** `eagle.pdf`  **Generated:** 2026-06-19T06:25:35.299984Z
---
## Summary of the Paper
The paper proposes EAGLE, an optimizer that uses a per-parameter secant-style approximation of Newton's step — the ratio of consecutive parameter differences to consecutive gradient differences — to approximate the inverse-Hessian-gradient product. Because this update can diverge when gradient differences vanish or in locally non-convex regions, EAGLE incorporates an adaptive switching mechanism that falls back to Adam based on (1) an adaptive threshold on |Δ∇L| computed from the coefficient of variation of recent gradient norms and (2) sign-based conditions characterizing locally upward-curving loss regions. The authors evaluate EAGLE on two fine-tuning tasks (GPT-2 Small on SST-2 and ViT-B/16 on CIFAR-10), reporting step-wise speedups of 3.4–6.8× to reach baseline final loss and higher final train/test accuracy than SGD-Momentum and Adam, while acknowledging that pure-Python wall-clock time is 1.3–5.6× worse per epoch.
## Recommendation
**Reject**  (confidence 4/5)
### Score Card
- Soundness: 2/4
- Presentation: 2/4
- Contribution: 2/4
- Overall: 3/10
### Main Strengths
- Tackles a well-motivated problem: practical curvature-aware optimization remains an active research area.
- Clear, intuitive exposition of the update rule using a 1D quadratic illustration (Fig. 2) and a careful case analysis (Fig. 4, Table 1) of when the secant step fails.
- The adaptive switching mechanism is a sensible safeguard, and ablations (Appendix A, D) show both the learning-rate scaling and the choice of Adam as fallback matter.
- Honest acknowledgment of the wall-clock overhead in the Limitations section.
- Code is publicly released, supporting reproducibility on the two studied tasks.

### Main Weaknesses
- Missing critical related work: the proposed update rule closely resembles per-coordinate Barzilai–Borwein (BB) / secant methods. The paper neither cites nor compares to BB, quasi-Newton secant variants, nor modern curvature-aware deep learning optimizers (e.g., AdaHessian, Sophia, Shampoo, K-FAC, Hessian-free). The Related Work section discusses only Adam.
- The theoretical justification is limited to a deterministic 1D quadratic. In stochastic mini-batch training, ∇L(θ_n) and ∇L(θ_{n-1}) are evaluated on different mini-batches, which weakens the secant interpretation of (Δθ)/(Δg) as a curvature estimate. This central issue is not addressed.
- Condition 2 (Eq. 6): L_n · Δ∇L ≥ 0 is dimensionally ambiguous when applied per-coordinate, since L_n is a scalar and Δ∇L is a vector. The intended semantics need clarification (possibly ∇L_n · Δ∇L was meant).
- Empirical evaluation is narrow: only two small fine-tuning tasks, apparently a single seed, no error bars or statistical tests. No training-from-scratch experiments and no large-scale tasks.
- Baselines may be undertuned. Adam and EAGLE share the same learning rate without per-optimizer tuning, no LR schedule or AdamW is used, and Adam's test-loss curve (Fig. 5b) diverges significantly while train loss decreases, indicating instability that better hyperparameters could mitigate. This undermines the final-performance comparison.
- The headline 3.4–6.8× step-based speedups are directly contradicted by 1.3–5.6× worse wall-clock time per epoch (Table 6), undermining the paper's central practicality claim. No PyTorch/CUDA implementation is provided.
- No ablation isolating the contribution of the EAGLE update rule itself. Given that the EAGLE rule fires only ~10–20% of the time (Tables 3, 5), it is plausible that much of the observed improvement comes from the gating heuristics combined with Adam rather than from the secant step.
- No sensitivity analysis for the introduced hyperparameters (α, τ_min, τ_max, τ_0, initial threshold), and threshold settings differ across tasks (1e-4 vs 5e-4) without a stated selection protocol.
- Generalization of the 1D sign-based case analysis (Section 2.2.2, Table 1) to high-dimensional parameter spaces is asserted but not justified.

### Detailed Comments
- The EAGLE update rule, applied per coordinate, has a strong structural resemblance to a coordinate-wise Barzilai–Borwein step (y/s · g with y = Δ∇L, s = Δθ). The paper frames it as a Newton approximation, but the connection to the BB/secant literature should be acknowledged and discussed; the novelty appears to lie primarily in the gating/fallback mechanism rather than in the secant update itself.
- The Newton's method justification in Section 2.1 treats H^{-1} as a scalar ratio along the previous step direction, but applying this per-coordinate corresponds to assuming a diagonal Hessian. This assumption should be stated and discussed.
- Figure 5(b) shows Adam test loss diverging substantially while train loss decreases; this suggests overfitting/instability that LR tuning, weight-decay tuning, or schedules might address. Until baselines are properly tuned, the generalization claim is difficult to interpret.
- When the optimizer switches between EAGLE and Adam, how are Adam's first/second moment estimates maintained? Discontinuities here could affect both stability and fairness of comparison.
- The 'EAGLE usage ratio' decreasing over training is presented as evidence the mechanism works, but it could equally indicate that EAGLE is used mainly when gradients are large early in training — precisely when SGD/Adam also make rapid progress, complicating attribution of the speedup.
- Section 1 heading is misspelled ('Intrduction'). GPT-2 (Radford et al., 2019) is not cited.
- An algorithm box / pseudocode would substantially improve clarity, especially regarding per-coordinate vs aggregate evaluation of the switching conditions and Adam state management.

### Questions for Authors
- How does EAGLE relate to the Barzilai–Borwein method, which uses the same Δθ/Δg ratio? Why was this prior work not discussed or compared?
- In stochastic mini-batch training, ∇L(θ_n) and ∇L(θ_{n-1}) use different mini-batches. How does this affect the validity of the secant approximation, and have you analyzed or mitigated this (e.g., re-evaluating on the same batch, EMA smoothing)?
- Condition 2 contains L_n · Δ∇L. Is L_n the scalar loss multiplied with a vector, or did you mean ∇L_n · Δ∇L (per-coordinate)? Please clarify.
- Can you provide an ablation where the EAGLE branch is replaced by a no-op or standard Adam step but the gating remains, to isolate the contribution of the EAGLE update rule itself?
- Were baselines tuned per-optimizer (LR, schedule, AdamW vs Adam, weight-decay scope)? Why does Adam's test loss diverge in Fig. 5(b)?
- Can you report results over multiple seeds with error bars?
- How does EAGLE compare to AdaHessian, Sophia, K-FAC, Shampoo, or L-BFGS on these tasks?
- How sensitive is performance to α, τ_min, τ_max, τ_0, and the initial threshold? How were the per-task threshold values (1e-4 vs 5e-4) selected?
- How are Adam's momentum and variance estimates maintained across EAGLE↔Adam switches?
- How does EAGLE behave in training-from-scratch settings, where loss landscapes are less benign than during fine-tuning?

### Suggestions for Improvement
- Add a thorough Related Work discussion including Barzilai–Borwein, quasi-Newton secant methods, and modern curvature-aware deep learning optimizers (AdaHessian, Sophia, Shampoo, K-FAC, Hessian-free).
- Provide an ablation that isolates the EAGLE update rule from the gating + Adam fallback.
- Tune baselines per-optimizer (LR sweep, AdamW, LR schedule) and report multi-seed results with error bars.
- Implement a GPU-efficient version and compare wall-clock time fairly; without this, step-based speedup claims are misleading.
- Discuss the stochastic mini-batch issue explicitly and consider using EMA-smoothed gradients or same-batch evaluation at θ_{n-1} for the secant.
- Clarify Eq. (6) and provide an algorithm box with explicit per-coordinate semantics and Adam state handling at switching boundaries.
- Add training-from-scratch experiments and at least one larger-scale benchmark (e.g., ImageNet, a GLUE task with BERT, or a language modeling task).
- Conduct a sensitivity analysis for introduced hyperparameters and document the selection protocol.
- Fix typos ('Intrduction'), cite GPT-2 properly, and improve Figure 1 markers for clarity.

### Improvement Checklist
- Discuss and compare to Barzilai–Borwein, secant/quasi-Newton methods, and curvature-aware DL optimizers (AdaHessian, Sophia, Shampoo, K-FAC).
- Address the stochastic mini-batch issue affecting the secant approximation.
- Clarify Eq. (6) semantics and provide an algorithm box; specify Adam state handling at switches.
- Add ablation isolating the EAGLE update rule from the gating + Adam mechanism.
- Tune baselines per-optimizer; include AdamW, LR schedules, and report multi-seed results with error bars.
- Provide a GPU-efficient implementation and fair wall-clock comparisons.
- Add training-from-scratch and larger-scale experiments.
- Sensitivity analysis for α, τ_min, τ_max, τ_0, initial threshold; state selection protocol.
- Fix 'Intrduction' typo and cite GPT-2.

