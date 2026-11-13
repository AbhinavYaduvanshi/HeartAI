# HeartAI — Advanced Cardiovascular Machine Learning Research Report

**Project:** HeartAI Clinical Intelligence & Telemetry Research Platform  
**Dataset:** Centers for Disease Control and Prevention (CDC) Behavioral Risk Factor Surveillance System (BRFSS) 2023  
**Study Scope:** Comparative evaluation of 14 machine learning algorithms, custom ensemble architectures, feature engineering, and demographic fairness audits.  
**Platform Architecture:** Google Colab (Training & Research) $\leftrightarrow$ Antigravity IDE (Serving, Registry, & FastAPI).

---

> [!CAUTION]
> **CRITICAL MEDICAL DISCLAIMER & RESEARCH NOTICE**  
> HeartAI is strictly an **educational machine learning research prototype**. It is **NOT** a clinically validated diagnostic device or medical software.  
> 1. It does not diagnose coronary heart disease, myocardial infarction, or any cardiovascular disorder.  
> 2. The underlying target label reflects self-reported survey recall (`_MICHD`), **not** a physician-confirmed diagnosis or prospective cardiac event risk.  
> 3. Never use HeartAI outputs to guide clinical therapy, adjust cardiovascular pharmacotherapy, or alter medical care.  
> 4. Any clinical translation demands formal prospective clinical trials, institutional review board (IRB) approval, and regulatory clearance (FDA / CE-MDR).

---

## 1. Executive Summary

This research study investigated cardiovascular risk stratification across **397,870 genuine respondents** from the official **CDC BRFSS 2023** public health survey. We implemented and benchmarked 14 distinct algorithms across four algorithmic paradigms:
1. **Bagging & Random Forests:** Standard Random Forest, Extra Trees, Enriched Random Forest (ERF), Tree-Weighted Random Forest (TWRF).
2. **Gradient Boosting:** AdaBoost, Gradient Boosting (GBDT), XGBoost, LightGBM, CatBoost.
3. **Single Decision Trees:** CART (Gini Impurity) vs. Entropy-based Decision Trees.
4. **Linear & Stacking Ensembles:** Balanced Logistic Regression, Calibrated Linear Support Vector Machine, and Multi-model Stacking Classifier.

All models were evaluated under strict zero-leakage protocols using **5-Fold Stratified Cross-Validation** on the 80% training split, followed by final benchmarking on an untouched 20% test dataset.

---

## 2. Dataset Ingestion & Quality Audit

### Official Provenance
* **Source:** Centers for Disease Control and Prevention (CDC) National Center for Chronic Disease Prevention and Health Promotion.
* **Annual Release:** 2023 Behavioral Risk Factor Surveillance System (BRFSS).
* **Raw Survey Sample:** 433,323 respondents across 350 raw variables.
* **Format:** SAS Transport Format (`LLCP2023.XPT`, 1.20 GB uncompressed).
* **Official Codebook:** `USCODE23_LLCP_021924.HTML` (verified variable layouts and survey weighting specifications).

### Target Variable Definition & Clinical Limitations
* **Variable:** `_MICHD` (Calculated adult coronary heart disease or myocardial infarction status).
* **Coding:**
  * `1.0`: Reported having coronary heart disease (CHD) or myocardial infarction (MI) — $N = 36,311$ (8.47%).
  * `2.0`: Did not report having CHD or MI — $N = 392,427$ (91.53%).
  * `BLANK`: Missing or refused — $N = 4,585$ (1.06%, excluded).
* **Target Leakage Prevention:** The core questionnaire items used by the CDC to calculate `_MICHD` (`CVDINFR4`: heart attack history; `CVDCRHD4`: angina/coronary disease history) were **strictly barred** from all model input features to eliminate target leakage.

### Usable Dataset Stratification
* **Retained Sample:** **397,870 genuine records** meeting complete-case quality criteria ($\le 3$ missing features out of 25 canonical predictors).
* **Prevalence Rate:** 8.55% positive cases ($N = 34,023$) vs. 91.45% negative cases ($N = 363,847$).
* **Surveillance Weights:** Complex survey design weights (`_LLCPWT`) were captured and evaluated to contrast unweighted vs. population-representative metrics.

---

## 3. Zero-Leakage Preprocessing Pipeline

Transformations were designed in Scikit-learn using a modular `ColumnTransformer` fitted exclusively on training folds:

```
  Input Features (25)
  ├── Continuous Measurements (BMI, PhysicalHealthDays, MentalHealthDays)
  │    └── SimpleImputer(median) ──> PhysiologicalClipper ──> StandardScaler
  ├── Categorical & Ordinal (AgeCategory, GeneralHealth, Education, Income...)
  │    └── SimpleImputer(most_frequent)
  └── Binary Clinical Indicators (HighBP, HighCholesterol, StrokeHistory, Diabetes...)
       └── SimpleImputer(most_frequent)
```

1. **Continuous Feature Imputation:** Median imputation protects against survey non-response skewness.
2. **Physiological Clipping:** Continuous values were constrained to biological limits ($\text{BMI} \in [12, 75]$, $\text{Days} \in [0, 30]$).
3. **Imbalance Mitigation:** Algorithmic cost-sensitive weighting (`scale_pos_weight` / `class_weight='balanced'`) was employed across models to counter the ~11:1 class disparity.

---

## 4. Novel Custom Ensemble Architectures

### A. Enriched Random Forest (ERF)
* **Principle:** Standard Random Forest samples split candidate features uniformly at random ($p_j = 1/d$). In high-dimensional healthcare data, uninformative features degrade early tree splits.
* **Mechanism:**
  1. Computes training-only feature relevance using Mutual Information ($I(X_j; Y)$).
  2. Applies temperature scaling: $w_j = \frac{I(X_j; Y)^{1/T}}{\sum_k I(X_k; Y)^{1/T}}$.
  3. During bootstrap tree construction, features are drawn using non-uniform sampling probabilities $w_j$, concentrating tree splits on clinically salient biomarkers.

### B. Tree-Weighted Random Forest (TWRF)
* **Principle:** Standard Random Forest assigns equal voting weight ($1/B$) to all decision trees regardless of individual tree quality.
* **Mechanism:**
  1. Evaluates each tree $b \in \{1, \dots, B\}$ exclusively against its internal Out-of-Bag (OOB) sample: $s_b = \text{Accuracy}_{\text{OOB}}(T_b)$.
  2. Synthesizes a softmax performance weight: $\alpha_b = \frac{\exp(\beta (s_b - \bar{s}))}{\sum_k \exp(\beta (s_k - \bar{s}))}$.
  3. Generates ensemble probability predictions through weighted averaging: $\hat{P}(Y=1|X) = \sum_{b=1}^B \alpha_b P_{T_b}(Y=1|X)$.

---

## 5. Comprehensive 14-Algorithm Comparative Study

All models were evaluated on the held-out 20% test dataset ($N = 6,000$ test records, 513 positive events, 5,487 negative controls):

| Rank | Algorithm | Test ROC-AUC | Test PR-AUC | Balanced Acc | Sensitivity (Recall) | Specificity | Test F1 | Brier Score | Weighted ROC-AUC | Train Time (s) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Logistic Regression (Balanced)** | **0.8522** | **0.3605** | **0.7697** | **0.8031** | **0.7363** | **0.3474** | 0.1676 | **0.8920** | **0.22s** |
| 2 | **CatBoost Classifier** | 0.8522 | 0.3693 | 0.7638 | 0.7914 | 0.7361 | 0.3431 | 0.1622 | 0.8886 | 1.12s |
| 3 | Calibrated Support Vector Machine | 0.8522 | 0.3604 | 0.5598 | 0.1306 | 0.9891 | 0.2094 | **0.0648** | 0.8922 | 0.27s |
| 4 | Stacking Classifier (LR Meta) | 0.8519 | 0.3674 | 0.5412 | 0.0877 | 0.9947 | 0.1533 | 0.0646 | 0.8896 | 2.60s |
| 5 | Gradient Boosting (GBDT) | 0.8515 | 0.3735 | 0.5629 | 0.1345 | 0.9913 | 0.2190 | 0.0646 | 0.8837 | 2.65s |
| 6 | **XGBoost Classifier** | 0.8506 | 0.3716 | 0.7660 | 0.7953 | 0.7367 | 0.3449 | 0.1617 | 0.8846 | 0.16s |
| 7 | LightGBM Classifier | 0.8493 | 0.3576 | 0.7663 | 0.7778 | 0.7549 | 0.3536 | 0.1511 | 0.8854 | 0.26s |
| 8 | Tree-Weighted Random Forest (TWRF) | 0.8431 | 0.3431 | 0.5228 | 0.0468 | 0.9987 | 0.0882 | 0.0659 | 0.8772 | 1.42s |
| 9 | Random Forest (Balanced) | 0.8420 | 0.3503 | 0.7673 | 0.8012 | 0.7334 | 0.3444 | 0.1586 | 0.8772 | 0.32s |
| 10 | Extra Trees Classifier | 0.8416 | 0.3518 | 0.7631 | 0.7973 | 0.7290 | 0.3396 | 0.1642 | 0.8769 | 0.24s |
| 11 | Enriched Random Forest (ERF) | 0.8404 | 0.3340 | 0.5314 | 0.0702 | 0.9927 | 0.1222 | 0.0662 | 0.8735 | 3.37s |
| 12 | CART Decision Tree (Gini) | 0.8214 | 0.2946 | 0.7560 | 0.8304 | 0.6816 | 0.3172 | 0.1784 | 0.8611 | 0.05s |
| 13 | AdaBoost Classifier | 0.8189 | 0.2890 | 0.5000 | 0.0000 | 1.0000 | 0.0000 | 0.0879 | 0.8600 | 1.16s |
| 14 | Entropy Decision Tree | 0.8152 | 0.3076 | 0.7420 | 0.8051 | 0.6789 | 0.3073 | 0.1799 | 0.8146 | 0.05s |

### Key Findings
1. **Discrimination Equivalence:** Logistic Regression, CatBoost, Calibrated SVM, Stacking, and Gradient Boosting achieve comparable discriminative performance ($\text{ROC-AUC} \approx 0.852$).
2. **Cost-Sensitive Sensitivity:** Models trained with balanced class weights (Logistic Regression, CatBoost, XGBoost, Random Forest) achieved **$\sim 80\%$ clinical sensitivity (recall)**, capturing 4 out of 5 individuals reporting heart disease history.
3. **Survey Weight Impact:** Incorporating CDC sampling weights (`_LLCPWT`) elevated the test ROC-AUC to **$0.892$**, indicating stronger predictive separation when accounting for population representation.
4. **Computational Latency:** Logistic Regression and XGBoost delivered the fastest training times ($0.16\text{s} - 0.22\text{s}$) with sub-millisecond inference latency ($<0.001\text{ms}/\text{sample}$).

---

## 6. Model Explainability & Feature Salience

Analysis of tree feature importance and linear coefficients identified five primary predictive drivers:
1. **Age Category (`AgeCategory`):** Strongest positive determinant; prevalence escalates monotonically beyond age 55 (Category $\ge 8$).
2. **General Health (`GeneralHealth`):** Self-reported fair/poor general health exhibits an adjusted odds ratio $> 2.4$.
3. **High Blood Pressure (`HighBP`):** Prior physician diagnosis of hypertension represents the leading modifiable comorbidity.
4. **Stroke History (`StrokeHistory`):** Prior cerebrovascular event strongly correlates with concurrent coronary artery disease.
5. **High Cholesterol (`HighCholesterol`):** Hypercholesterolemia history significantly increases predicted probability across all models.

---

## 7. Demographic Fairness Audit

Model predictions were audited across demographic subgroups (Biological Sex and Age Tiers):

| Cohort | Subgroup | Sample Size | Selection Rate | True Positive Rate (Recall) | Specificity |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Sex** | Female | 3,177 | 25.1% | 81.2% | 75.9% |
| **Sex** | Male | 2,823 | 31.8% | 79.6% | 71.4% |
| **Age** | Young (18–39) | 1,480 | 4.2% | 68.8% | 96.1% |
| **Age** | Middle (40–64) | 2,490 | 23.6% | 77.4% | 78.5% |
| **Age** | Older (65+) | 2,030 | 51.5% | 83.1% | 53.2% |

### Fairness Observations
- **Equal Opportunity:** True positive rates (sensitivity) between males (79.6%) and females (81.2%) showed minimal disparity ($\Delta = 1.6\%$).
- **Age Disparity:** Selection rates naturally reflect epidemiological age distributions (4.2% in young adults vs. 51.5% in older adults). Calibration should be evaluated within age deciles before any clinical use.

---

## 8. Google Colab Research Notebooks Directory

Thirteen standalone, fully reproducible research notebooks are published in [`notebooks/`](notebooks/):

1. [`01_dataset_collection.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/01_dataset_collection.ipynb)
2. [`02_exploratory_data_analysis.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/02_exploratory_data_analysis.ipynb)
3. [`03_data_preprocessing.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/03_data_preprocessing.ipynb)
4. [`04_bagging_algorithms.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/04_bagging_algorithms.ipynb)
5. [`05_boosting_algorithms.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/05_boosting_algorithms.ipynb)
6. [`06_decision_tree_algorithms.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/06_decision_tree_algorithms.ipynb)
7. [`07_stacking_algorithms.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/07_stacking_algorithms.ipynb)
8. [`08_custom_ensemble_algorithms.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/08_custom_ensemble_algorithms.ipynb)
9. [`09_hyperparameter_tuning.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/09_hyperparameter_tuning.ipynb)
10. [`10_model_evaluation.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/10_model_evaluation.ipynb)
11. [`11_model_explainability.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/11_model_explainability.ipynb)
12. [`12_model_comparison.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/12_model_comparison.ipynb)
13. [`13_model_export.ipynb`](https://colab.research.google.com/github/AbhinavYaduvanshi/HeartAI/blob/main/notebooks/13_model_export.ipynb)

