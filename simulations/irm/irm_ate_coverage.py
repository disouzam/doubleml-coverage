import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LassoCV, LogisticRegressionCV

import doubleml as dml
from doubleml.datasets import make_irm_data

# Number of repetitions
n_rep = 1000

# DGP pars
theta = 0.5
n_obs = 500
dim_x = 20

# to get the best possible comparison between different learners (and settings) we first simulate all datasets
np.random.seed(42)
datasets = []
for i in range(n_rep):
    data = make_irm_data(theta=theta, n_obs=n_obs, dim_x=dim_x, return_type='DataFrame')
    datasets.append(data)

# set up hyperparameters
hyperparam_dict = {
    "learner": [("Lasso_Logistic", (LassoCV(), LogisticRegressionCV())),
                ("RF_RF", (RandomForestRegressor(n_estimators=100, max_features=20, max_depth=5, min_samples_leaf=2),
                           RandomForestClassifier(n_estimators=100, max_features=20, max_depth=5, min_samples_leaf=2)))],
    "level": [0.95, 0.90]
}

# set up the results dataframe
df_results_detailed = pd.DataFrame(columns=["coverage", "ci_length", "learner", "level", "repetition"])

# start simulation
np.random.seed(42)

for i_rep in range(n_rep):
    print(f"Repetition: {i_rep}/{n_rep}", end="\r")

    # define the DoubleML data object
    obj_dml_data = dml.DoubleMLData(datasets[i_rep], 'y', 'd')

    for learner_idx, (learner_name, (ml_g, ml_m)) in enumerate(hyperparam_dict["learner"]):
        # Set machine learning methods for g & m
        dml_irm = dml.DoubleMLIRM(
            obj_dml_data=obj_dml_data,
            ml_g=ml_g,
            ml_m=ml_m,
        )
        dml_irm.fit(n_jobs_cv=5)

        for level_idx, level in enumerate(hyperparam_dict["level"]):
            confint = dml_irm.confint(level=level)
            coverage = (confint.iloc[0, 0] < theta) & (theta < confint.iloc[0, 1])
            ci_length = confint.iloc[0, 1] - confint.iloc[0, 0]

            df_results_detailed = pd.concat(
                (df_results_detailed,
                 pd.DataFrame({
                    "coverage": coverage.astype(int),
                    "ci_length": confint.iloc[0, 1] - confint.iloc[0, 0],
                    "learner": learner_name,
                    "level": level,
                    "repetition": i_rep}, index=[0])),
                ignore_index=True)

df_results = df_results_detailed.groupby(["learner", "level"]).agg({"coverage": "mean", "ci_length": "mean"}).reset_index()
print(df_results)

# save results
df_results.to_csv("results/irm_ate_coverage.csv", index=False)
