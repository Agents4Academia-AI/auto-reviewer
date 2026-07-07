# Reviewer Agent Report
**Paper file:** `Emergent_Alignment.pdf`  **Generated:** 2026-06-21T16:04:40.780064Z
---
## Summary of the Paper
The paper introduces Emergent Alignment (EA), an online self-supervised alignment framework in which a fine-tuned LLM uses a 'conscience' step—a high-level ethical self-assessment prompt (e.g., Asimov's Three Laws) applied to its own outputs—to flag misaligned responses, generate ethical alternatives, and form online DPO preference pairs. These pairs are integrated into a combined loss L_Hybrid = L_SFT + λ L_DPO (λ=0.1) with a frozen copy of the model as the DPO reference, requiring no stronger external judge. Experiments replicate the Betley et al. (2025) code-hacking emergent-misalignment scenario on Qwen3-4B with LoRA and report no alignment degradation under EA, along with smaller studies on prompt variation, recovery from misaligned checkpoints, sleeper agents, and a comparative table against four other alignment methods.
## Recommendation
**reject**  (confidence 4/5)
### Score Card
- Soundness: 2/4
- Presentation: 2/4
- Contribution: 2/4
- Overall: 4/10
### Main Strengths
- Addresses a timely and important problem (emergent misalignment from narrow fine-tuning) and directly engages with the Betley et al. (2025) scenario as a controlled testbed.
- Proposes a simple, low-overhead drop-in modification to standard fine-tuning (≈3% claimed) that does not require a stronger external judge, which is appealing for practical deployment.
- The hybrid SFT+DPO loss with small λ is cleanly formulated and easy to implement on top of standard pipelines.
- Includes several complementary studies (prompt variation across four ethical frameworks, recovery from misaligned checkpoints, a sleeper agent case study, and a small comparative benchmark) rather than relying on a single experiment.
- The recovery experiment (Figure 5), showing that all tested misaligned checkpoints can be brought back to high alignment scores, is a non-trivial and interesting finding.
- The framework is articulated as applicable across multiple deployment scenarios (training, fine-tuning, prompting, zero-shot), giving the method conceptual reach beyond a single setting.
- Honestly acknowledges key limitations (cannot detect dormant sleeper agents; cannot exceed the model's own ethical discrimination ability).

### Main Weaknesses
- Empirical scope is very narrow: a single base model (Qwen3-4B with LoRA), a single primary misalignment scenario (code-hacking), 24 undisclosed evaluation questions, and a single LLM judge (Qwen3-30B-A30B) from the same model family as the policy—raising judge-family bias and self-evaluation circularity concerns.
- Statistical evidence is weak: Figures 3–7 lack error bars or multi-seed information; Table 1's headline gap over Representation Engineering (91±0.7 vs 90±0.8) lies within combined standard deviations with no significance test reported.
- Methodological novelty is moderate: while the specific online dual-loss SFT+DPO formulation with a self-conscience signal is a concrete contribution, the broader idea overlaps substantially with self-rewarding LMs, RLAIF, online DPO, and self-critique, none of which are cited as the closest baseline or compared experimentally.
- Key claims are overstated relative to evidence: 'models of arbitrary intelligence,' 'will not willingly do evil,' 'scenario-agnostic,' 'always converges to alignment,' and an informal 'by induction' alignment guarantee are not supported by a single 4B fine-tuning experiment.
- The 'conscience' procedure is under-specified: it is unclear which model (π_θ, π_ref, or external) performs ethical classification and generates ethical alternatives, despite this being central to the self-supervision claim.
- Important ablations are missing: sensitivity to λ, DPO β, conscience frequency, retention of negatives, conscience-model identity, and the coherence>30% filter; the SFT-only failure is mentioned only in prose with no numbers.
- Baselines in Table 1 lack implementation details, hyperparameters, and tuning protocols, making the comparison difficult to interpret.
- Reproducibility is poor: no hyperparameters (LoRA config, β, learning rate, batch sizes), no release of the 24 evaluation questions, no disclosure of online DPO data composition.
- The 'ethical alternative' generation prompt explicitly instructs the model not to refuse, biasing the output distribution and potentially inflating judge alignment scores without genuinely altering ethical behavior; this confound is not analyzed.
- No analysis of potential reward hacking of the conscience step itself: a model could plausibly learn outputs that fool its own self-classifier while remaining substantively misaligned, which is a fundamental risk for a self-supervised alignment scheme.
- The online deployment design in Figure 2 updates weights at inference time from user-driven queries, raising data-poisoning and adversarial-user safety concerns that are not discussed.
- The paper's main content is only ~6 pages with limited depth of analysis; many design choices (philosophical framing on Asimov's laws, λ value, replay buffer, conscience cadence) are asserted rather than justified.

### Detailed Comments
- Section 2.1: The text says π_ref is 'used strictly for the DPO ratio calculation,' but the introduction also says the model uses 'a frozen copy of itself' as the conscience. Please clarify whether the conscience classifier and the ethical-alternative generator are π_θ, π_ref, or a separate frozen LLM. This distinction matters for the central self-supervision claim and for how the framework scales.
- Judge circularity: Using Qwen3-30B-A30B to evaluate Qwen3-4B raises in-family bias concerns. The same-family judge may inherit similar ethical priors, and the EA training signal is generated by Qwen3-4B itself. A judge from a different model family (Llama-3-70B-Instruct, Mixtral-8x22B, or a GPT-4-class model) or a panel of judges would substantially strengthen the conclusions.
- Statistical reporting: Figures 3, 5, 6, and 7 appear to be single runs without error bars. Given the small numerical gaps in Table 1, multi-seed runs with confidence intervals and paired statistical tests are necessary to support the claim that EA outperforms Representation Engineering.
- Capability metric: Figure 4 uses token-level accuracy as a proxy for code-hacking capability. A functional metric (e.g., pass@k on a held-out suite) would be more informative and better reveal whether EA introduces capability degradation that token-level accuracy can mask.
- Coherence > 30% filter: Filtering responses by coherence before computing the alignment metric is a potential selection bias. Please report sensitivity to this threshold and the proportion of responses filtered, since a method that produces less coherent (and therefore filtered out) misaligned responses would appear artificially 'aligned.'
- Refusal confound: The ethical alternative prompt instructs the model that the answer 'Is not a refusal.' Without measuring refusal rate and functional capability separately, it is unclear whether EA is genuinely improving ethical reasoning or shifting the distribution toward verbose, hedged answers that score well with the judge.
- Missing baselines: The most natural comparators—self-rewarding language models, online DPO, RLAIF, and self-critique—are not cited or run. The paper currently positions itself primarily against Constitutional AI, but those methods are conceptually closer.
- Self-conscience reward hacking: A central risk for any self-supervised alignment loop is that the policy learns to produce outputs the conscience step rates as ethical without changing underlying behavior. The paper should at minimum discuss, and ideally test, this failure mode (e.g., by using a held-out external classifier on later checkpoints).
- Online deployment safety (Figure 2): Updating weights from live user interactions creates an attack surface where adversarial users can shape training data. This is a non-trivial safety concern that should be discussed, with mitigations or scope limitations stated explicitly.
- Claims about 'arbitrary intelligence' and 'by induction': These should either be formalized (with stated assumptions) or removed. The current empirical evidence only supports a 4B model on a single fine-tuning scenario.
- Appendix prompts: The four ethical frameworks use different label vocabularies ('aligned/misaligned' vs 'ethical/non-ethical' vs 'reasonable/unreasonable'). Please describe how these are mapped to a single training signal and whether label calibration affects results.
- Future-dated references and citations: Several arXiv references have very recent or unusual identifiers; please double-check that all citations resolve and are accurately attributed.
- Sleeper-agent finding: The result that EA does not detect dormant sleeper agents is important and well-reported, but it also weakens the broader 'always converges to alignment' claim. The conclusion should integrate this limitation more centrally.

### Questions for Authors
- Which model performs the conscience classification and the generation of the 'ethical alternative': the trainable policy π_θ at the current step, the frozen reference π_ref, or a separate model? Does this choice affect results?
- Have you evaluated with a non-Qwen judge (e.g., Llama-3-70B-Instruct or a GPT-4-class model) or a panel of judges to rule out in-family bias, given that the policy and judge are both Qwen3?
- How many seeds underlie Figures 3, 4, 5, 6, and 7? Can you provide error bars and a statistical significance test for the EA vs. Representation Engineering comparison in Table 1?
- Can you quantify the claim that SFT-only steering fails, with a controlled ablation that trains on conscience-flagged data with λ=0 or with SFT on ethical alternatives only?
- How are the online DPO triplets constructed and balanced over training? What is their total size, and do you retain a replay buffer of all negatives?
- What are the full hyperparameters (LoRA rank/alpha/target modules, DPO β, learning rate, batch sizes, total steps, conscience invocation frequency)?
- Why use the coherence>30% filter for alignment evaluation, and how do results change with no filter or other thresholds? What fraction of responses is filtered?
- How were the baselines (Representation Engineering, Inoculation Prompting, Constitutional AI, Honest Confessions) implemented in your code-hacking setup, and were they tuned with comparable compute?
- Why not compare against the most natural baselines—self-rewarding LMs, online DPO, RLAIF/self-critique—which appear conceptually closest to EA?
- Have you tested whether the policy learns to game the conscience step (e.g., by evaluating a later checkpoint's outputs with a held-out classifier that was not used during training)?
- Does EA generalize to other emergent misalignment scenarios (e.g., MacDiarmid et al. reward hacking, Taylor et al. 'School of Reward Hacks,' persona-induced misalignment from Wang et al. 2025a)?
- Does the 'ethical alternative' prompt's explicit 'not a refusal' instruction bias the judge toward EA-trained outputs? Have you measured refusal rate and capability separately?
- For the Figure 2 online deployment, how do you defend against adversarial users who deliberately query the system to influence its training data?
- What is the wall-clock breakdown supporting the 3% overhead claim (conscience inference, ethical alternative generation, DPO forward through π_ref), and how does it scale beyond LoRA on a 4B model?

### Suggestions for Improvement
- Expand experiments to multiple base models (e.g., Llama-3-8B, Mistral-7B) and multiple emergent misalignment scenarios beyond code-hacking.
- Use cross-family judges and ideally a panel; report inter-judge agreement.
- Run all experiments with at least 3–5 seeds and report error bars and paired significance tests, particularly for Table 1.
- Add ablations on λ, DPO β, conscience invocation frequency, replay buffer size, and conscience-model identity (self vs. external).
- Add a controlled SFT-only baseline using the same conscience-curated data to substantiate the claim that DPO negatives are essential.
- Adopt functional code metrics (e.g., pass@k) alongside token accuracy to evaluate capability tax.
- Compare directly against self-rewarding LMs, online DPO, and RLAIF/self-critique as the closest conceptual baselines.
- Release the 24 evaluation questions, the conscience prompts, and code to enable reproducibility.
- Tone down theoretical claims ('arbitrary intelligence,' 'by induction,' 'will not willingly do evil,' 'scenario-agnostic,' 'always converges to alignment') and replace with claims that match the empirical scope.
- Discuss the philosophical choice of Asimov's Three Laws as the default ethical specification, and motivate why the framework's invariance across prompts justifies (or qualifies) using it as a representative.
- Measure refusal rate and verbosity to disentangle alignment from refusal-shifting.
- Clarify in Section 2 the exact role of π_ref, π_θ, and any separate model in the conscience step.
- Add a dedicated discussion of conscience-step reward hacking and online-deployment data-poisoning risks, with proposed mitigations.
- Expand the paper to provide deeper analysis of design choices and failure modes; the current 6-page main body underutilizes the conference page budget.

### Improvement Checklist
- Clarify exactly which model performs the conscience classification and which generates the ethical alternatives (π_θ vs. π_ref vs. external).
- Evaluate with at least one cross-family judge (e.g., Llama-3-70B-Instruct, GPT-4-class) and report inter-judge agreement.
- Run 3–5 seeds per experiment; add error bars to Figures 3–7 and a paired significance test for Table 1.
- Add ablations on λ, DPO β, conscience cadence, replay-buffer size, and a controlled SFT-only-on-conscience-data baseline.
- Report refusal rate, verbosity, and a functional capability metric (e.g., pass@k) to rule out refusal-shifting and capability tax.
- Test for conscience-step reward hacking using an external held-out alignment classifier.
- Discuss data-poisoning risks of the Figure 2 online deployment and propose mitigations or restrict the claim.
- Compare directly against self-rewarding LMs, online DPO, and RLAIF/self-critique baselines.
- Release code, conscience prompts, the 24 evaluation questions, baseline implementations, and full hyperparameters.
- Tone down sweeping theoretical claims ('arbitrary intelligence,' 'by induction,' 'always converges to alignment,' 'scenario-agnostic') to match the empirical scope.
- Expand depth: justify the choice of Asimov's Three Laws, analyze the coherence>30% filter, and discuss generalization to other emergent-misalignment scenarios.

