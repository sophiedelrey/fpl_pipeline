## FPL Project Script Changes - March 2nd

* generated the 2025-26 season from api (until gw 28)
* edited the FPLpipeline_v2.ipynb in order to create the dataset_no0min.csv
* the dataset_no0min.csv : only contains rows where Minutes Played > 0, from 2020-21 untill latest 2025-26 gws.

At the forecaster.ipynb: 
* Switch input file to dataset_no0min.csv in the main training script.
* Implement a Backtest Validation cell to predict the last known game for each player.
* Add Actual Points, Predicted Points, and Error columns to the evaluation output.
* Configure the script to export the validation results to lgbm_2026_truth.csv.