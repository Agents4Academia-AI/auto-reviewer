# Reviewer Agent Report
**Paper file:** `Task_Tokens_A_Flexible_Approach_to_Adapting_Behavior_Foundation_Models.pdf`  **Generated:** 2026-06-21T16:02:54.258903Z
---
## Summary of the Paper
The paper introduces Task Tokens, a parameter-efficient method for adapting goal-conditioned behavior foundation models (specifically MaskedMimic) to downstream humanoid control tasks. A small MLP task encoder is trained with PPO to produce an additional 512-dim conditioning token that is concatenated with the BFM's existing prior and state tokens; gradients flow through the frozen transformer to update only the encoder (~200K parameters vs ~25M for full fine-tuning). The method preserves the BFM's multi-modal prompting interface, allowing users to compose learned tokens with text or joint priors and to use a finite-state machine for sequential phase switching. Experiments on five humanoid tasks (Reach, Direction, Steering, Strike, Long Jump) in Isaac Gym show that Task Tokens are competitive with or exceed MaskedMimic fine-tuning, PULSE, AMP, and PPO baselines in success rate while converging substantially faster than PULSE on Strike and using ~125x fewer trainable parameters than fine-tuning. A human study (~96 participants) finds Task Tokens to produce more human-like motions than fine-tuning, AMP, and PPO (though PULSE remains preferred). OOD perturbation sweeps on Steering (friction and gravity) suggest Task Tokens preserve the BFM's robustness better than fine-tuning.
## Recommendation
**Weak Reject**  (confidence 4/5)
### Score Card
- Soundness: 2/4
- Presentation: 3/4
- Contribution: 2/4
- Overall: 5/10
### Main Strengths
- Addresses a real and practically relevant problem: adapting GC-BFMs like MaskedMimic to downstream tasks without destroying pretrained priors or multi-modal prompting capabilities.
- Clean, well-described mechanism that integrates naturally with the transformer interface of the BFM; meaningful parameter efficiency (~200K vs ~25M trainable parameters per task).
- Reasonably broad empirical evaluation across five tasks with five seeds each, plus OOD perturbation sweeps, a human study, and qualitative demonstrations of multi-modal prompting and FSM composition.
- Demonstrates a genuinely useful capability that fine-tuning baselines lose: composing learned task tokens with user-defined text/joint priors and an FSM for sequential phase switching, illustrated on Direction and Strike. This hybrid control paradigm is a practical contribution distinct from prior PEFT work.
- OOD robustness results on Steering (friction/gravity) provide non-trivial evidence that the frozen-BFM design preserves pretrained robustness better than fine-tuning.
- Code and supplementary videos are released; the writing is generally clear and the figure illustrating the architecture is helpful.
- The ablation study (Section E) provides useful insight into the influence of encoder size and proprioceptive inputs.

### Main Weaknesses
- Limited methodological novelty: the approach is essentially soft-prompt/prefix tuning ported to a tokenized BFM, but the paper does not benchmark against the most directly relevant PEFT baselines (LoRA, adapters, prefix-tuning) at matched trainable-parameter budgets, despite citing them as inspirations (Hu et al. 2021; Houlsby et al. 2019; Li & Liang 2021).
- Several headline claims are partially supported or overstated. The 'up to 6x faster convergence' figure is derived specifically from the Strike task vs PULSE (Figure 3: ~50M vs ~300M steps), while in the same figure MaskedMimic Fine-Tune converges at a similar rate. The claim that Task Tokens 'match the high task performance of full fine-tuning' is contradicted on Strike, where Task Tokens (76.61) underperform Fine-Tune (83.07), PULSE (83.18), and pure PPO (81.36).
- The key claim that fine-tuning causes 'catastrophic forgetting' of multi-modal prompting is asserted qualitatively only; no dedicated experiment quantifies prompt-following fidelity after fine-tuning vs Task Tokens training.
- OOD robustness is evaluated on a single task (Steering); standard-deviation bands overlap substantially with Fine-Tune across much of the perturbation range, making the broad 'surpasses other methods in robustness' framing too strong.
- Several comparisons are confounded: PULSE is trained with 128 parallel envs vs 1024 for others (affecting convergence comparisons); AMP uses a locomotion-only motion dataset (likely disadvantaging it on Strike/Long Jump); Strike uses a hand-designed FSM scaffold and prior tokens not available to baselines; and Reach/Direction/Steering Task Tokens results bundle the encoder with J.C. priors, conflating their respective contributions.
- The FSM-based Strike pipeline is essentially hand-engineered task decomposition, which partially undermines the 'unified framework' framing and shifts some of the difficulty from learning to scripting.
- The human study has methodological limitations (uneven form sizes of 20/24/52, no statistical significance testing, no demographic information, possible conflation of motion quality with task success). The paper acknowledges that PULSE is preferred over Task Tokens, attributing this to PULSE's prior constraint, but does not reconcile this with the broader motion-quality narrative.
- The generality claim ('Task Tokens can be applicable to any transformer-based BFM') is asserted but not empirically validated: only MaskedMimic is tested.
- No quantitative motion-quality metrics (e.g., Fréchet motion distance, foot sliding, joint smoothness, distance to reference motion distribution) are reported to complement the human study.

### Detailed Comments
- Positioning vs PEFT literature: A LoRA or adapter applied to selected MaskedMimic transformer layers at the same ~200K parameter budget would be the most natural test of whether the token-injection design provides advantages beyond generic PEFT.
- Strike result interpretation: Task Tokens are clearly worse than Fine-Tune and PULSE on Strike. The paper attributes Fine-Tune's similar convergence to 'overfitting' in the Figure 3 caption without supporting evidence, which reads as post-hoc rationalization. A more honest discussion of when a single 512-d token has insufficient capacity for the task would strengthen the paper.
- Multi-modal prompting preservation: This is arguably the most important advantage of Task Tokens over fine-tuning, but the supporting evidence is qualitative. A simple experiment evaluating prompt-following accuracy on held-out J.C. or text prompts after fine-tuning vs Task Tokens training would substantially strengthen the claim.
- OOD evaluation breadth: Robustness is a major selling point but is evaluated only on Steering. Extending the friction/gravity (and ideally morphological or sensor-noise) sweeps to Reach, Strike, or Long Jump would significantly support the generalization narrative.
- Confounders in baselines: The differing env counts for PULSE vs others (128 vs 1024) directly affect convergence comparisons; the locomotion-only AMP dataset disadvantages it on the more complex tasks; and the Strike FSM+priors scaffold is not available to baselines. These should be addressed by re-running with parity or by clearly stating these caveats.
- Task Tokens vs Task Tokens + J.C.: For Reach/Direction/Steering, the headline results bundle Task Tokens with joint conditioning priors. An ablation (partially present in Table 3) should be elevated to the main text to disentangle the encoder's contribution.
- High-variance seed behavior: Some standard deviations (Fine-Tune Strike 47.36 ± 54.78; AMP Strike 52.21 ± 47.58; AMP Long Jump 76.59 ± 43.42) indicate bimodal seed outcomes warranting analysis (e.g., success-failure histograms).
- Compute clarification: The paper emphasizes trainable-parameter savings but does not clarify that backpropagation still requires a full forward/backward pass through the frozen BFM, so wall-clock and memory savings are smaller than the parameter ratio suggests.
- Minor textual issues: Section 4 introduction expands BFM as 'Behavioral Frequency Modulation,' which is a clear proofreading error (it should be Behavior Foundation Model). The meaning of '±' (std/SE/CI) should be stated consistently. The PPO objective, reward functions, critic architecture, and the FSM threshold for Strike are underspecified in the main text.

### Questions for Authors
- Can you provide a direct comparison to LoRA, adapters, or prefix-tuning applied to MaskedMimic at matched trainable-parameter budgets?
- Can you quantitatively demonstrate the catastrophic-forgetting-of-multi-modal-prompting claim, e.g., by measuring J.C. or text prompt-following accuracy on held-out prompts after fine-tuning vs after Task Tokens training?
- On Strike, why do Task Tokens underperform Fine-Tune, PULSE, and PPO? Does this indicate a capacity limitation of a single 512-d token for tasks requiring precise interaction?
- Can you report OOD perturbation results on tasks beyond Steering (e.g., Reach, Strike, Long Jump) to support the broader robustness claim?
- How sensitive are convergence results to the number of parallel environments? Could you rerun PULSE with 1024 envs (or your method with 128) to make the comparison apples-to-apples?
- Can you add a 'Task Tokens (no J.C.)' row for Reach/Direction/Steering in the main results table to disentangle the encoder contribution from the prior-token contribution?
- Were baselines (e.g., PPO, Fine-Tune) given access to the same FSM scaffold and orientation/text prior tokens used by Task Tokens on Strike? If not, can you re-run with parity?
- Could you report quantitative motion-quality metrics (e.g., distance to reference motion distribution, foot sliding, jerk) to complement the human study?
- Have you tested Task Tokens on any other transformer-based BFM beyond MaskedMimic to substantiate the generality claim?
- Can you clarify whether the reported '±' values are std, SE, or CI, and analyze the bimodal seed outcomes visible in high-variance results (e.g., AMP and Fine-Tune on Strike)?

### Suggestions for Improvement
- Add PEFT baselines (LoRA, adapters, prefix-tuning) on the MaskedMimic transformer at matched parameter budgets.
- Add a quantitative experiment measuring multi-modal prompt-following before and after fine-tuning vs Task Tokens training.
- Extend OOD perturbation sweeps to multiple tasks.
- Provide an ablation isolating the Task Token's contribution from the joint-conditioning priors on Reach/Direction/Steering in the main results table.
- Run baselines with parity in parallel environments (PULSE at 1024 or all methods at 128) and clearly state what the Strike scaffolding (FSM, priors) provides to Task Tokens but not to baselines.
- Add quantitative motion-quality metrics (e.g., Fréchet motion distance, foot sliding, smoothness) alongside the human study.
- Soften or qualify the strongest claims: 'match the high task performance of full fine-tuning' is not true on Strike; 'up to 6x faster convergence' should be stated as a single-task finding vs PULSE; 'applicable to any transformer-based BFM' should be marked as conjecture pending empirical evidence.
- Improve the human study: report participant demographics, perform significance testing, and separate naturalness from task-success judgments.
- Fix the 'Behavioral Frequency Modulation' typo in Section 4, clarify the meaning of '±' throughout, and document the PPO setup, reward functions, critic architecture, and FSM thresholds in the main text or an explicit reproducibility appendix.
- Discuss compute (wall-clock, GPU memory) explicitly, since backprop through the frozen BFM still incurs full forward/backward cost.

### Improvement Checklist
- Add PEFT baselines (LoRA / adapters / prefix-tuning) on MaskedMimic at matched parameter budgets.
- Quantitatively demonstrate the catastrophic-forgetting-of-prompting claim with a held-out prompt-following evaluation.
- Extend OOD perturbation experiments beyond Steering to at least one interaction task (e.g., Strike).
- Elevate the Task-Tokens-without-J.C. ablation to the main results table to disentangle encoder vs prior-token contributions.
- Equalize the number of parallel environments across PULSE and other baselines, or clearly caveat the convergence comparison.
- Clearly state what scaffolding (FSM, prior tokens) is available to Task Tokens but not to baselines on Strike, and ideally re-run with parity.
- Report quantitative motion-quality metrics (FMD, foot sliding, jerk) alongside the human study.
- Soften overclaims: qualify the 6x-faster, matches-fine-tuning, and 'any transformer-based BFM' statements.
- Improve human study reporting (demographics, significance tests, separation of naturalness from success).
- Fix the 'Behavioral Frequency Modulation' typo, clarify '±' notation, and add explicit reproducibility details (PPO hyperparameters, reward functions, critic architecture, FSM thresholds).
- Discuss wall-clock/memory implications of backprop through the frozen BFM.

