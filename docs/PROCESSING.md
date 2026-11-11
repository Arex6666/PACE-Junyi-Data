# Processing and provenance

## Source selection

1. Keep content with learning_stage=elementary, subject=math and content_kind=Exercise; keep users in grades 1–6. Join logs using uuid and ucid.
2. Within that subset, require at least 10 records per user and 20 records per exercise. These are record-count thresholds, not distinct-item or distinct-person thresholds. The historical implementation applies them once, not iteratively.
3. Use the IDs in the existing 100-student profile file to export all their qualifying events. source_row_1based records the original Log_Problem.csv data-row position, excluding the header.
4. Select only needed columns; encode correctness as 0/1 and preserve seconds. No new imputation, outlier removal, time normalization or deduplication is applied. Repeated observations retain their weights.
5. Preserve the existing 7,500 seed JSONL byte-for-byte. Its CSV changes serialization and bool encoding only. Every seed was matched to the source event multiset by user, exercise, correctness and seconds.
6. Export filtered exercise metadata and selected user fields. Source anonymous IDs and PACE aliases permit joins; no real-world names or contacts are added.

The historical sampler uses numpy.default_rng(42), samples 100 fit-eligible users without replacement, then samples up to 7,500 events using a pandas random_state drawn from the same generator. This release preserves the saved selections.

## Field construction

Difficulty mapping: easy->2, normal->3, hard->4, unset->3; unknown values also default to 3 in the historical code. This differs from the original event level field.

The IRT probability form is P(correct)=sigmoid(theta-b). Proportions are clipped to [.01,.99] before logit transformation. The implemented five-round update is:
theta_new = logit(user_accuracy) + response-count-weighted mean(b);
theta_new -= mean(theta_new);
b_new = -logit(item_accuracy) + response-count-weighted mean(theta_new).
Repeated answers contribute counts. The saved metadata calls this “alternating MLE”; these equations describe the actual implemented approximation, not an independently verified exact optimizer. The release does not refit it.

KP b averages the fitted exercise difficulties. junyi_irt_params.json stores metadata and the ucid-to-KP map, not all per-user theta or per-item b. The sampled profiles and KP nodes contain their own saved parameter values.

initial_mastery uses historical student/KP accuracy, with sigmoid(theta-b_kp) for unobserved KPs, then adds N(0,.05^2), clips to [.05,.98], and rounds to 3 decimals. It is not unmodified empirical accuracy.

motivation uses badge counts: 0 -> low(0), 1–3 -> mid(1), >=4 -> high(2).
style is sampled with probabilities concrete=.35, abstract=.20, memorization=.25, inquiry=.20.
Misconception count is sampled by theta: >=.7 -> counts [0,1], probabilities [.7,.3]; >=0 -> [0,1,2]/[.3,.5,.2]; >=-.7 -> [1,2,3]/[.3,.5,.2]; lower -> [2,3,4]/[.3,.5,.2]. Types are sampled without replacement from 15 definitions. These fields are simulation inputs, not independently measured psychological labels.

## Version distinctions

Seed kp_name, kp_domain and kp_grade retain the original automatic classifications. The graph is the later corrected snapshot, schema 2.1-junyi-corrected: simplified display names, retained name_original, and domain/grade corrections. Join using kp_id or level3_id rather than names. Historical seed fields are not silently overwritten.

Graph prerequisite edges are heuristic. Use nodes[].applicable_misconceptions for the current domain-based associations. misconceptions[].applies_to retains IDs from the earlier template taxonomy and is not a reliable mapping to the 18 Junyi KPs.

Historical graph note text contains approximate/stale source counts. Use validation_report.json and actual table scopes for the release. Saved artifacts are preserved unchanged for provenance.

## Scripts

load_junyi.py and _kp_definitions.py are the existing offline implementation; fix_kg_manual_corrections.py records later corrections. To rerun, place the three original CSVs in a separate data directory and use:
python scripts/load_junyi.py --data_dir PATH_TO_DATA --all --seed 42
The correction script expects data/knowledge_graph_junyi.json relative to its working directory. Do not regenerate over the released files.

The 100-student subset does not alone reconstruct the full-population parameter fit, model training, or all manuscript results.
