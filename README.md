# PACE: Junyi data and variable documentation

Junyi data materials for A PACE Framework for Educational AI Agents in Personalized and Collaborative Learning.

Download the prepared ZIP from [release v1.0.0](https://github.com/Arex6666/PACE-Junyi-Data/releases/tag/v1.0.0). The same files can be browsed here.

## Included data

| File | Contents |
| --- | --- |
| data/processed/cleaned_events_100_students.csv | 21,069 qualifying source events for the existing 100 sampled learners; original row numbers retained |
| data/processed/elementary_math_content.csv | 784 elementary mathematics exercise units and KP mappings |
| data/processed/student_metadata_100.csv | Aliases, public anonymous IDs, source grade and badge counts |
| data/analysis/junyi_real_interactions.jsonl | Original 7,500 interaction seeds, preserved byte-for-byte |
| data/analysis/junyi_interaction_seeds_7500.csv | The same seeds in CSV; correctness encoded 0/1 |
| data/analysis/seed_summary_by_kp.csv | Descriptive seed summaries for 18 KPs |
| data/derived/students_100_junyi.json | Existing derived learner profiles |
| data/derived/initial_mastery_long.csv | 1,800 mastery values reshaped without changes |
| data/derived/knowledge_graph_junyi.json | 18 KPs, 19 heuristic edges, 15 simulation misconception definitions |
| data/derived/junyi_irt_params.json | Fit metadata and exercise-to-KP mappings; not full fitted parameter arrays |

There are 5,146 correct seed responses out of 7,500 (68.6133%). Seed correctness and response times are real historical labels, not generated answer text.

The cleaned file contains all eligible events for the existing 100-student sample, not the full elementary population. It was exported for this release from the original CSV using the saved sample IDs and preprocessing filters. Repeated events are retained.

## Original source and reuse

The complete original Junyi Academy Online Learning Activity Dataset is available from [Junyi Academy Foundation on Kaggle](https://www.kaggle.com/datasets/junyiacademy/learning-activity-public-dataset-by-junyi-academy). Follow the provider's download process. The full approximately 3 GB raw collection is linked rather than duplicated.

Credit Junyi Academy Foundation. The source data and Junyi-derived data retain [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). See LICENSE.md.

## Supporting documentation

- [Variable definitions and codes](docs/DATA_DICTIONARY.md)
- [Processing and provenance](docs/PROCESSING.md)
- [Current export validation](docs/validation_report.json)
- [Input SHA-256 hashes](docs/source_manifest.json)
- MANIFEST.sha256: checksums of released files

Run python scripts/verify_package.py to check file hashes, record counts, ranges and joins. Dependencies: scripts/requirements.txt. Existing offline processing scripts are supplied for inspection; they do not call a paid model API.

This release covers Junyi data materials only. It does not include PACE-AES data, generated language-model training texts, trained weights or end-to-end experiment logs, and does not claim to reproduce every manuscript result.
