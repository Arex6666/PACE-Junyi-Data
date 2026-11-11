# Variable definitions and encoding

CSV: UTF-8, comma-separated with headers. JSON/JSONL: UTF-8. IDs are strings; do not coerce to numbers or attempt reidentification. Behavioral values are source observations unless marked as inferred or sampled.

## Cleaned event table

| Field | Type / code | Definition |
| --- | --- | --- |
| source_row_1based | integer >=1 | Row in original Log_Problem.csv, header excluded |
| student_id | s001–s100 | PACE alias linking to profile id |
| uuid | string | Public upstream anonymous user identifier |
| ucid | string | Exercise-unit ID, not an individual problem ID |
| kp_id | k01–k18 | Level-3 KP mapping |
| is_correct | 0/1 | Observed incorrect/correct response |
| total_sec_taken | integer seconds | Source duration, without outlier modification |

## Exercise metadata

| Field | Type / code | Definition |
| --- | --- | --- |
| ucid | unique string | Exercise key |
| content_pretty_name | text | Original traditional-Chinese exercise name |
| content_kind | Exercise | Retained content type |
| difficulty | easy/normal/hard/unset | Platform difficulty; unset is an explicit category |
| subject | math | Retained subject |
| learning_stage | elementary | Retained stage |
| level1_id, level2_id, level3_id, level4_id | strings | Anonymous curriculum hierarchy keys |
| kp_id | k01–k18 | Saved mapping added at level3 granularity |

## User metadata

student_id is the PACE alias; uuid is the source anonymous key; user_grade is the observed integer school grade 1–6; badges_cnt is the nonnegative source badge count.

## Analysis seeds (CSV and JSONL)

| Field | Type / code | Definition |
| --- | --- | --- |
| student_id | s001–s100 | Sample alias |
| junyi_uuid | string | Same identifier as cleaned-table uuid |
| ucid | string | Exercise key |
| kp_id | k01–k18 | Aggregated knowledge point |
| kp_name | text | Original inferred label at seed generation |
| kp_domain | string category | Original inferred domain, possibly differing from corrected graph |
| kp_grade | integer | Inferred content grade, not the actual learner grade |
| is_correct | CSV 0/1; JSON bool | Observed correctness |
| junyi_difficulty | easy/normal/hard/unset | Source content difficulty |
| difficulty_level | 2,3,4 in this sample | easy=2, normal=3, hard=4, unset=3 |
| total_sec_taken | integer seconds | Source response duration |

seed_summary_by_kp.csv uses kp_id, n_records (event count), n_correct (sum of correctness), correct_rate (n_correct/n_records), mean_seconds (arithmetic mean), n_students (distinct aliases). Rates are record-weighted.

## Derived learner profiles and mastery

| Field | Type / code | Origin |
| --- | --- | --- |
| id | s001–s100 | Sample alias |
| theta | real | Saved ability estimate, 3 decimals |
| motivation | 0/1/2 | Low/mid/high badge-count heuristic |
| style | concrete/abstract/memorization/inquiry | Prior-sampled simulation category |
| misconception_ids | list m01–m15 | Prior-sampled simulation misconceptions |
| initial_mastery | map kp_id -> real [.05,.98] | Historical accuracy or IRT fallback, plus noise/clipping |
| _junyi_uuid | string | Upstream anonymous user key |
| _junyi_grade | 1–6 | Observed learner grade |
| _junyi_badges | integer >=0 | Observed badge count |

initial_mastery_long.csv has student_id, kp_id, initial_mastery: one row for each 100 x 18 pair, reshaped without changes.

## Knowledge graph

nodes[] fields: id (kp_id), name (corrected display label), name_original (earlier label), domain (corrected heuristic category), grade (corrected heuristic content grade), b (mean fitted exercise difficulty), difficulty_levels (1–5), applicable_misconceptions (associated m-codes), _junyi_level3_id (source hierarchy key), _junyi_n_items (exercise count), _junyi_l2_id (parent key).

Corrected domains are decimal, factor, fraction, geometry, integer, measurement, statistics, time and wordprob (word problems). Seed domains can retain earlier classifications.
edges[] has from/to (kp_id) and type=prerequisite; edges are heuristic.
misconceptions[] has id, name, description, wrong_pattern and legacy applies_to. See PROCESSING.md before using applies_to.
difficulty_offsets maps levels 1–5 to [-1,-.5,0,.5,1].
metadata includes source, domain, language, n_kp, n_edges, n_misconceptions, schema_version, irt_params and historical note text.

## IRT metadata

method is the saved method label; n_iter=5; n_students_fit/n_items_fit describe the full fit scope; theta_stats/b_stats hold mean and standard deviation; ucid_to_kp maps exercises to KPs. No full per-individual or per-exercise parameter arrays are stored in this file.

## Joins and missing values

student_id=id; uuid=junyi_uuid=_junyi_uuid; ucid joins exercise metadata; kp_id joins nodes[].id. Exported correctness and time fields have no missing values. Missing historical KP coverage was handled by the documented profile fallback. No train/test assignment is implied by these files.
