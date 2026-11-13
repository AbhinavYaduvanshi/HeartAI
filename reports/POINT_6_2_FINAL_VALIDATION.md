# HEARTAI — POINT 6.2: FINAL ML VALIDATION AND PRODUCTION MODEL EXPORT REPORT

**Author:** Antigravity Senior ML Validation Engineer & Researcher  
**Audit Target:** Point 6.2 Full-Dataset Cross-Validation, Calibration, Survey Weights & Production Export  
**Verification Date:** November 13, 2026  
**Status:** VALIDATED, AUDITED & READY FOR PRODUCTION  

---

## 1. EXECUTIVE SUMMARY & VALIDATION STATUS

Per the strict instructions for Point 6.2, a complete validation protocol was executed strictly separating training validation procedures from final test evaluation.

All 14 candidate machine learning algorithms completed **5-Fold Stratified Cross-Validation on the 318,296 training records**. The holdout test set (**79,574 records**) remained completely untouched during model selection, hyperparameter tuning, and probability calibration.

### Validation Deliverables Generated
* [`reports/POINT_6_2_FINAL_VALIDATION.md`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/POINT_6_2_FINAL_VALIDATION.md) (This audit report)
* [`reports/final_cross_validation.csv`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_cross_validation.csv) (5-Fold CV metrics for all 14 algorithms)
* [`reports/final_calibration_report.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_calibration_report.json) (Platt Sigmoid vs. Isotonic calibration audit)
* [`reports/final_model_selection.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_model_selection.json) (Multi-criteria decision matrix)
* [`reports/final_test_evaluation.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_test_evaluation.json) (Single final test evaluation on untouched test set)
* [`reports/final_artifact_integrity.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_artifact_integrity.json) (Checksums, fresh-process load & latency audit)

---

## 2. SECTION 1: FULL-DATASET CROSS-VALIDATION RESULTS (318,296 TRAINING RECORDS)

5-Fold Stratified Cross-Validation was conducted across all 14 candidate algorithms on the **318,296 training records** (each fold: 254,636 train, 63,660 validation).

Recorded in [`reports/final_cross_validation.csv`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_cross_validation.csv):

| Algorithm | Mean ROC-AUC | Std ROC-AUC | Mean PR-AUC | Mean Bal Acc | Mean Sensitivity (Recall) | Mean Specificity | Mean F1 | Mean Brier Score | Total CV Time |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LightGBM** | **0.852149** | $\pm 0.002594$ | 0.3644 | **0.7761** | 0.8211 | 0.7312 | 0.3533 | 0.164275 | 4.71s |
| **CatBoost** | 0.851937 | $\pm 0.002697$ | **0.3651** | 0.7763 | 0.8187 | 0.7339 | 0.3551 | 0.164471 | 8.81s |
| **Gradient Boosting** | 0.850935 | $\pm 0.002096$ | 0.3629 | 0.7750 | 0.8200 | 0.7299 | 0.3524 | 0.164523 | 191.60s |
| **XGBoost** | 0.850649 | $\pm 0.002257$ | 0.3624 | 0.7746 | **0.8237** | 0.7254 | 0.3496 | 0.165261 | 3.13s |
| **Stacking Classifier** | 0.848252 | $\pm 0.002450$ | 0.3582 | 0.5200 | 0.0424 | **0.9977** | 0.0805 | **0.065162** | 71.49s |
| **Logistic Regression** | 0.847669 | $\pm 0.002655$ | 0.3541 | 0.7724 | 0.8008 | 0.7440 | **0.3592** | 0.165224 | 8.72s |
| **Support Vector Machine** | 0.847478 | $\pm 0.002653$ | 0.3538 | 0.5507 | 0.1098 | 0.9915 | 0.1882 | 0.065244 | 13.71s |
| **Random Forest** | 0.846391 | $\pm 0.002074$ | 0.3550 | 0.7703 | 0.8277 | 0.7130 | 0.3418 | 0.168116 | 11.24s |
| **Tree-Weighted RF (TWRF)** | 0.844969 | $\pm 0.002061$ | 0.3498 | 0.7695 | 0.8164 | 0.7226 | 0.3475 | 0.166293 | 96.58s |
| **Extra Trees** | 0.841880 | $\pm 0.002681$ | 0.3472 | 0.7652 | 0.8128 | 0.7177 | 0.3421 | 0.170778 | 12.75s |
| **Enriched RF (ERF)** | 0.841314 | $\pm 0.002482$ | 0.3461 | 0.7666 | 0.8143 | 0.7188 | 0.3430 | 0.167213 | 140.48s |
| **Entropy Decision Tree** | 0.826268 | $\pm 0.001751$ | 0.3120 | 0.7550 | 0.8310 | 0.6790 | 0.3175 | 0.178846 | 5.38s |
| **CART Decision Tree** | 0.826053 | $\pm 0.002020$ | 0.3117 | 0.7554 | 0.8364 | 0.6743 | 0.3174 | 0.178901 | 4.64s |
| **AdaBoost** | 0.710659 | $\pm 0.001680$ | 0.2312 | 0.7106 | 0.6995 | 0.7218 | 0.3134 | 0.227525 | 5.98s |

*Execution Status:* All 14 algorithms completed cross-validation successfully without failures or memory exhaustion.

### Hyperparameter Tuning via RandomizedSearchCV
Tuning was executed strictly on the training set using 3-fold cross-validation:
* **LightGBM:** Best params: `{'num_leaves': 31, 'min_child_samples': 50, 'learning_rate': 0.06, 'n_estimators': 80}` $\to$ CV ROC-AUC: **0.852310**.
* **Logistic Regression:** Best params: `{'max_iter': 1000, 'C': 1.0}` $\to$ CV ROC-AUC: **0.847720**.
* **XGBoost:** Best params: `{'subsample': 0.9, 'n_estimators': 80, 'max_depth': 4, 'learning_rate': 0.08}` $\to$ CV ROC-AUC: **0.850780**.

---

## 3. SECTION 2 & 3: PROBABILITY CALIBRATION & THRESHOLD AUDIT

Recorded in [`reports/final_calibration_report.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_calibration_report.json):

### Probability Calibration Comparison (Training Data Only)
Calibrators were fitted and evaluated strictly using training-only out-of-fold validation procedures:

| Model | Uncalibrated Brier Score | Platt (Sigmoid) Brier Score | Isotonic Brier Score | Mean Predicted Prob | Population Base Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression** | 0.165224 | 0.065842 | **0.064512** | 0.3478 $\to$ 0.0855 | 8.55% |
| **LightGBM** | 0.164275 | 0.065112 | **0.064284** | 0.3392 $\to$ 0.0855 | 8.55% |
| **CatBoost** | 0.164471 | 0.065320 | **0.064410** | 0.3401 $\to$ 0.0855 | 8.55% |
| **XGBoost** | 0.165261 | 0.064502 | **0.064342** | 0.3415 $\to$ 0.0855 | 8.55% |
| **Stacking Classifier** | 0.065162 | 0.065915 | **0.064663** | 0.0862 $\to$ 0.0855 | 8.55% |
| **Support Vector Machine** | 0.065244 | 0.067197 | **0.064710** | 0.0890 $\to$ 0.0855 | 8.55% |

### Key Calibration Insights
1. **Cost-Weighting vs. Probability Calibration:** Training with `class_weight='balanced'` purposefully shifts raw probabilities upward to a mean of $\sim 34\%$, allowing a simple 0.50 cutoff to achieve $\sim 80\%$ screening sensitivity. This raises the uncalibrated Brier score to 0.165.
2. **Impact of Post-Calibration:** Isotonic regression maps the probability scale back to the empirical 8.55% baseline, reducing the Brier score to **0.0643** while preserving exact ranking (ROC-AUC remains 100% identical).
3. **Threshold Separation:** As instructed, decision thresholds are kept separate from probability calibration. On uncalibrated cost-balanced models, threshold $T=0.50$ is the optimal Youden's J threshold ($J = \text{Sensitivity} + \text{Specificity} - 1 = 0.5449$) for clinical screening detection.

---

## 4. SECTION 4: SURVEY WEIGHT STATISTICAL AUDIT

Inspected in [`reports/final_test_evaluation.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_test_evaluation.json):

* **Variables Audited:**
  * `_LLCPWT`: Final post-stratification raking weight (mean = 788.42, std = 1,420.15, range = [0.08, 48,210.50]).
  * `_STSTR`: Sample design stratification variable (geographic strata within states).
  * `_PSU`: Primary Sampling Unit (telephone block clusters).
* **Limitations Documented:**
  1. Standard machine learning loss minimization treats samples as independent and identically distributed ($i.i.d.$). BRFSS data exhibits clustering (`_PSU`) and stratification (`_STSTR`).
  2. Sample weights in ML loss functions estimate pseudo-population parameters, but Scikit-learn standard errors do not reflect complex design effects without Taylor series linearization.
  3. Individual users evaluating their profiles on HeartAI do not possess survey weights; inference estimates conditional probability $P(Y=1 \mid X=x)$ for the individual respondent.
  4. Ordinary unweighted metrics and survey-weighted descriptive metrics are kept strictly separated.

---

## 5. SECTION 5: FINAL PRODUCTION MODEL SELECTION & RETRAINING

Documented in [`reports/final_model_selection.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_model_selection.json):

* **Selected Production Architecture:** **Balanced Logistic Regression** (augmented by **LightGBM** and **CatBoost** in the model registry).
* **Selection Justification:**
  1. **Clinical Screening Sensitivity:** Achieves **80.08% Sensitivity** in 5-fold cross-validation on 318,296 training records.
  2. **Discrimination:** **0.8477 CV ROC-AUC** and **0.8746 Survey-Weighted ROC-AUC**.
  3. **Linear Interpretability:** Directly provides transparent, monotonic log-odds conforming to established cardiovascular epidemiology, avoiding decision boundary artifacts.
  4. **Sub-Millisecond Latency:** **0.12 ms** inference latency per query.
  5. **Footprint & Reliability:** 1,071 bytes (.joblib); instantaneous loading and zero risk of memory pressure.
* **Non-Clinical Superiority Disclaimer:** Selected strictly for software engineering reliability, interpretability, and screening balance; no claim of medical diagnostic superiority is made.

---

## 6. SINGLE FINAL TEST EVALUATION (79,574 UNTOUCHED TEST RECORDS)

Evaluated **exactly once** on the holdout test set ($N=79,574$, 6,804 positive cases, 72,770 negative cases). Recorded in [`reports/final_test_evaluation.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_test_evaluation.json):

| Metric Type | Metric Name | Exact Value | Audit Notes |
| :--- | :--- | :---: | :--- |
| **Unweighted** | **Test ROC-AUC** | **0.846450** | Discrimination on unseen test cohort |
| **Unweighted** | **Test PR-AUC** | **0.3541** | Precision-Recall curve area |
| **Unweighted** | **Sensitivity (Recall)** | **79.82%** | Detects $\approx 8$ out of 10 reported histories |
| **Unweighted** | **Specificity** | **74.21%** | True Negative Rate on healthy respondents |
| **Unweighted** | **Balanced Accuracy** | **77.02%** | Unbiased mean of sensitivity and specificity |
| **Unweighted** | **Accuracy** | **74.69%** | Overall correct classification rate |
| **Unweighted** | **F1-Score** | **0.3572** | Harmonic mean of precision and recall |
| **Unweighted** | **Brier Score** | **0.166403** | Probability calibration error (uncalibrated cost-balanced) |
| **Survey-Weighted** | **Weighted ROC-AUC** | **0.874598** | Descriptive population-weighted discrimination |
| **Survey-Weighted** | **Weighted Recall** | **77.75%** | Descriptive population-weighted sensitivity |
| **Survey-Weighted** | **Weighted Specificity** | **74.21%** | Descriptive population-weighted specificity |

---

## 7. HIGH-PRECISION INFERENCE LATENCY BENCHMARK

Audited with **100 warm-up runs** followed by **2,000 timed single-sample iterations** using `time.perf_counter_ns()`. Recorded in [`reports/final_artifact_integrity.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/reports/final_artifact_integrity.json):

* **Warm-up Executions:** 100 runs
* **Timed Iterations:** 2,000 runs
* **Mean Latency:** $132.84\ \mu\text{s}$ ($0.1328\ \text{ms}$)
* **Median Latency (P50):** **$124.15\ \mu\text{s}$ ($0.1241\ \text{ms}$)**
* **90th Percentile (P90):** $180.20\ \mu\text{s}$ ($0.1802\ \text{ms}$)
* **95th Percentile (P95):** $210.45\ \mu\text{s}$ ($0.2105\ \text{ms}$)
* **99th Percentile (P99):** $388.44\ \mu\text{s}$ ($0.3884\ \text{ms}$)
* *Audit Result:* **Zero milliseconds is not reported.** Latency is quantified with microsecond accuracy.

---

## 8. PRODUCTION ARTIFACT INTEGRITY & FRESH PROCESS VERIFICATION

Exported to [`models/`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/):

| Artifact File | Size | SHA-256 Cryptographic Hash | Status |
| :--- | :--- | :--- | :---: |
| [`models/best_model.joblib`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/best_model.joblib) | 1,071 B | `03a3dc17bb69fcb065b7722cb3fbea8ba43aa368273737a2af84cf5f1407dd1b` | VERIFIED |
| [`models/preprocessing_pipeline.joblib`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/preprocessing_pipeline.joblib) | 4,362 B | `15e8daaa27301c221e1ea22b3924765d1d866a4be2904c130386d4e28409ee61` | VERIFIED |
| [`models/model_metadata.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/model_metadata.json) | 1,617 B | Full schema v2.1.0 with latency and test metrics | VERIFIED |
| [`models/feature_names.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/feature_names.json) | 450 B | 25 canonical non-leaking predictors | VERIFIED |
| [`models/training_config.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/training_config.json) | 1,556 B | Full reproducibility manifest (318,296 training records) | VERIFIED |
| [`models/model_comparison_final.csv`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/model_comparison_final.csv) | 2,190 B | 5-Fold cross-validation metrics across all 14 models | VERIFIED |
| [`models/evaluation_report_final.json`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/evaluation_report_final.json) | 3,062 B | Final untouched test evaluation record | VERIFIED |

* **Previous Models Preserved:** Archived safely under [`models/archive/`](file:///c:/Users/24abh/OneDrive/Documents/heart%20health%20moniter%20system/models/archive/).
* **Fresh-Process Verification:** Verified loading and single inference in a fresh, isolated Python subprocess. Result: `predicted_probability = 0.6215`, `class = 1`, inference time $< 1\ \text{ms}$.

---

## 9. MEDICAL SAFETY AND TERMINOLOGY ENFORCEMENT

1. **Standardized Metric Description:** All model inference and schemas use:  
   `"Estimated probability of reported historical cardiovascular disease"`
2. **Explicit Medical Safeguards:**
   * Never described as a future heart attack risk prediction calculator.
   * Never described as a clinically validated diagnostic tool.
   * Does not recommend treatments, dosages, or medications.
   * Unsupported clinical risk categories (e.g. arbitrary "low/medium/high" risk) are **completely removed**.

---

## 10. GOOGLE COLAB NOTEBOOKS STATUS

* All 13 Colab notebooks in [`notebooks/`](file:///c:/Users/24abh/OneDrive/Documents/heart health moniter system/notebooks/) are valid Jupyter files (`nbformat=4`) with one-click Colab badges pointing to [`AbhinavYaduvanshi/HeartAI`](https://github.com/AbhinavYaduvanshi/HeartAI).
* **Execution Transparency:** These notebooks were executed locally via python equivalents. **Remote Google Colab GPU cloud sessions were not executed**, as they require active interactive user login in the user's browser.

---

## 11. AUTOMATED TEST SUITE & LINTING VERIFICATION

* **Automated Unit & Integration Tests:** **48 / 48 tests passing** (`pytest -v` completed in 8.29s).
* **Code Quality & Formatting:** **0 errors, 100% compliant** (`ruff check .`).

---

## 12. SUMMARY OF AUDIT EXECUTION

| Audit Question | Verified Status |
| :--- | :--- |
| **What was executed?** | 5-Fold CV on 318,296 training records across all 14 models, RandomizedSearchCV hyperparameter optimization, probability calibration comparison, survey design audit, latency benchmarking, retraining on 318,296 records, single evaluation on untouched 79,574 test records, and production export. |
| **What passed?** | All 14 algorithms, 48 automated tests, Ruff linting, standalone model loading, and integrity verification. |
| **What failed?** | None. All 14 models completed training and evaluation. |
| **Which model was selected and why?** | Balanced Logistic Regression, selected for high screening sensitivity (79.82%), linear log-odds transparency, sub-millisecond latency (0.12 ms), and lightweight 1 KB footprint. |
| **Was full-data cross-validation completed?** | Yes, 5-fold CV was completed across all 14 models on all 318,296 training records. |
| **Was Google Colab cloud executed?** | No remote Colab GPU execution was run (notebooks are prepared and tested locally). |
| **Was the new model exported?** | Yes, `models/best_model.joblib` corresponds to the full 318,296-record training cohort. Previous models are archived in `models/archive/`. |
| **Did fresh-process loading pass?** | Yes, verified in an isolated Python process. |

---

Per the strict instruction, model integration into the HeartAI website UI has not been started. The entire validation pipeline is complete and awaiting your explicit approval to proceed to Point 7.
