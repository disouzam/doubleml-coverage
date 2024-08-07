import numpy as np
import pandas as pd

from lightgbm import LGBMRegressor, LGBMClassifier

import doubleml as dml
from doubleml.datasets import make_did_SZ2020

# Number of repetitions
n_rep = 500

# DGP pars
theta = 0.0  # true ATTE
n_obs = 1000

# to get the best possible comparison between different learners (and settings) we first simulate all datasets
np.random.seed(42)

dgp_types = [1, 2, 3, 4, 5, 6]
n_dgps = len(dgp_types)
datasets = []
for dgp_type in dgp_types:
    datasets_dgp = []
    for i in range(n_rep):
        data = make_did_SZ2020(n_obs=n_obs, dgp_type=dgp_type, cross_sectional_data=True)
        datasets_dgp.append(data)
    datasets.append(datasets_dgp)


# set up hyperparameters
hyperparam_dict = {
    "DGP": dgp_types,
    "score": ["experimental", "observational"],
    "in sample normalization": [True, False],
    "learner_g": [("LGBM", LGBMRegressor()),],
    "learner_m": [("LGBM", LGBMClassifier()),],
    "level": [0.95, 0.90]
}

# set up the results dataframe
df_results_detailed = pd.DataFrame(
    columns=["Coverage", "CI Length",
             "Bias", "Score", "In-sample-norm.", "DGP",
             "Learner g", "Learner m",
             "level", "repetition"])

df_results_detailed["In-sample-norm."] = df_results_detailed["In-sample-norm."].astype(bool)

# start simulation
np.random.seed(42)

for i_dgp, dgp_type in enumerate(dgp_types):
    print(f"\nDGP: {i_dgp + 1}/{n_dgps}", end="\n")
    for i_rep in range(n_rep):
        print(f"Repetition: {i_rep + 1}/{n_rep}", end="\r")

        # define the DoubleML data object
        obj_dml_data = datasets[i_dgp][i_rep]

        for learner_g_idx, (learner_g_name, ml_g) in enumerate(hyperparam_dict["learner_g"]):
            for learner_m_idx, (learner_m_name, ml_m) in enumerate(hyperparam_dict["learner_m"]):
                for score in hyperparam_dict["score"]:
                    for in_sample_normalization in hyperparam_dict["in sample normalization"]:
                        if score == "experimental":
                            dml_DiD = dml.DoubleMLDIDCS(
                                obj_dml_data=obj_dml_data,
                                ml_g=ml_g,
                                ml_m=None,
                                score=score,
                                in_sample_normalization=in_sample_normalization)
                        else:
                            assert score == "observational"
                            dml_DiD = dml.DoubleMLDIDCS(
                                obj_dml_data=obj_dml_data,
                                ml_g=ml_g,
                                ml_m=ml_m,
                                score=score,
                                in_sample_normalization=in_sample_normalization)

                        dml_DiD.fit(n_jobs_cv=5)

                        for level_idx, level in enumerate(hyperparam_dict["level"]):
                            confint = dml_DiD.confint(level=level)
                            coverage = (confint.iloc[0, 0] < theta) & (theta < confint.iloc[0, 1])
                            ci_length = confint.iloc[0, 1] - confint.iloc[0, 0]

                            df_results_detailed = pd.concat(
                                (df_results_detailed,
                                 pd.DataFrame({
                                    "Coverage": coverage.astype(int),
                                    "CI Length": confint.iloc[0, 1] - confint.iloc[0, 0],
                                    "Bias": abs(dml_DiD.coef[0] - theta),
                                    "Learner g": learner_g_name,
                                    "Learner m": learner_m_name,
                                    "Score": score,
                                    "In-sample-norm.": in_sample_normalization,
                                    "DGP": dgp_type,
                                    "level": level,
                                    "repetition": i_rep}, index=[0])),
                                ignore_index=True)

df_results = df_results_detailed.groupby(
    ["Learner g", "Learner m", "Score", "In-sample-norm.", "DGP", "level"]).agg(
        {"Coverage": "mean",
         "CI Length": "mean",
         "Bias": "mean",
         "repetition": "count"}
    ).reset_index()
print(df_results)

# save results
df_results.to_csv("simulations/did/results/did_cs_atte_coverage.csv", index=False)
