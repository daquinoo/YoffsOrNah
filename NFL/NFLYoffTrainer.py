import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sqlalchemy import create_engine, text

# Database connection using SQLAlchemy
hotstreak_db_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-HotStreak-ChampNFL?driver=ODBC+Driver+18+for+SQL+Server'
hotstreak_engine = create_engine(hotstreak_db_url)

# Load Data
query_stats = "SELECT * FROM [dbo].[Football-Stats] WHERE year >= 2000 AND year <= 2023"
df = pd.read_sql(query_stats, hotstreak_engine)

# Define relevant columns for features and target
feature_columns = [
    'win_pct', 'cur_div_rnk', 'lg_rank', 'oyds_p_game', 'oyds_all_pg', 'total_oTD_pg', 'oTD_allow_pg',
    'pass_ypg', 'pass_TD_pg', 'rush_ypg', 'rush_TD_pg', 'pts_pg', 'pts_all_pg',
    'int_frc_pg', 'int_pg', 'pass_yds_all_pg', 'rush_yds_all_pg',
    'pass_TD_all_pg', 'rush_TD_all_pg', 'fga_pg', 'fgperc_pg', 'xp_perc_pg',
    'sacks_pg', 'sackyds_pg', 'sacks_all_pg', 'sackyds_all_pg', 'yoffs_pred'
]

invert_features = [
    'cur_div_rnk', 'lg_rank', 'oyds_all_pg', 'oTD_allow_pg', 'pts_all_pg', 
    'int_pg', 'pass_yds_all_pg', 'rush_yds_all_pg', 'pass_TD_all_pg', 
    'rush_TD_all_pg', 'sacks_all_pg', 'sackyds_all_pg'
]

differential_columns = [
    'win_pct', 'cur_div_rnk', 'lg_rank', 'oyds_diff', 'oTD_diff',
    'pass_yds_diff', 'pass_TD_diff', 'rush_yds_diff', 'rush_TD_diff',
    'pts_diff', 'int_diff', 'fg_effectiveness', 'xp_perc_pg',
    'sacks_diff', 'sackyds_diff', 'yoffs_pred'
]

def calculate_differentials(averages):
    differentials = {
        'win_pct': averages[0],
        'cur_div_rnk': averages[1],
        'lg_rank': averages[2],
        'oyds_diff': averages[3] - averages[4],
        'oTD_diff': averages[5] - averages[6],
        'pass_yds_diff': averages[7] - averages[15],
        'pass_TD_diff': averages[8] - averages[17],
        'rush_yds_diff': averages[9] - averages[16],
        'rush_TD_diff': averages[10] - averages[18],
        'pts_diff': averages[11] - averages[12],
        'int_diff': averages[13] - averages[14],
        'fg_effectiveness': averages[19] * averages[20],
        'xp_perc_pg': averages[21],
        'sacks_diff': averages[22] - averages[24],
        'sackyds_diff': averages[23] - averages[25],
        'yoffs_pred': averages[26]
    }
    return pd.Series(differentials)

def calculate_rolling_averages(df, team, year, games_played, feature_columns):
    team_data = df[(df['team'] == team) & (df['year'] == year) & (df['games_played'] <= games_played)]
    if len(team_data) == 0:
        return [0] * len(feature_columns)
    
    rolling_averages = team_data[feature_columns[:-1]].mean()
    
    # Calculate new yoffs_pred
    pred_columns = [col for col in team_data.columns if col.endswith('_pred')]
    actual_columns = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
    
    pred_values = team_data[pred_columns].iloc[-1]  # Get the last row's prediction values
    actual_values = team_data[actual_columns].iloc[-1]  # Get the last row's actual values
    
    adjusted_preds = []
    for pred_col, actual_col in zip(pred_columns, actual_columns):
        pred = pred_values[pred_col]
        actual = actual_values[actual_col]
        
        if pd.notnull(pred) and pd.notnull(actual):
            if pred < 0.5 and actual == 1:
                # Team progressed despite low prediction
                adjusted_preds.append(0.5 + pred)
            else:
                adjusted_preds.append(pred)
    
    if adjusted_preds:
        new_yoffs_pred = sum(adjusted_preds) / len(adjusted_preds)
    else:
        new_yoffs_pred = 0
    
    rolling_averages = rolling_averages.tolist()
    rolling_averages.append(new_yoffs_pred)
    
    return rolling_averages

def get_playoff_rolling_averages(df, y_column):
    playoff_teams = df[df[y_column].isin([1])][['team', 'year']].drop_duplicates()
    playoff_averages = []
    
    for _, row in playoff_teams.iterrows():
        team_data = df[(df['team'] == row['team']) & (df['year'] == row['year'])]
        playoff_game = team_data[team_data[y_column].isin([1])].iloc[0]
        games_before_playoff = playoff_game['games_played']
        
        averages = calculate_rolling_averages(df, row['team'], row['year'], games_before_playoff, feature_columns)
        playoff_averages.append(averages)
    
    return pd.DataFrame(playoff_averages, columns=feature_columns).mean()

# Function to predict next round advancement
def predict_round_advancement(model, data):
    prediction = model.predict(data)
    return prediction[0]

# Prepare the model and scaler
scaler = StandardScaler()
model = LinearRegression()

# Training data
train_df = df[df['year'] <= 2022]
X = train_df[feature_columns]

# Function to perform individual linear regressions
def individual_regressions(X, y):
    predictions = {}
    for feature in X.columns:
        model = LinearRegression()
        model.fit(X[[feature]], y)
        predictions[feature] = model.predict(X[[feature]])
    return predictions

def apply_coefficients(X, coefficients):
    X_weighted = X.copy()
    if isinstance(X_weighted, pd.Series):
        for feature in differential_columns:
            if feature in coefficients:
                X_weighted[feature] *= coefficients[feature].mean()
    else:  # DataFrame
        for feature in differential_columns:
            if feature in coefficients:
                X_weighted[feature] *= coefficients[feature]
    return X_weighted


def split_data(y_column):
    # Calculate rolling averages for all teams up to their first playoff game
    def get_team_averages(group):
        first_playoff_game = group[group[y_column].isin([0, 1])].iloc[0] if any(group[y_column].isin([0, 1])) else group.iloc[-1]
        return calculate_rolling_averages(group, group.name[0], group.name[1], first_playoff_game['games_played'], feature_columns)

    all_averages = train_df.groupby(['team', 'year']).apply(get_team_averages)
    all_averages = pd.DataFrame(all_averages.tolist(), index=all_averages.index, columns=feature_columns)
    
    # Now filter for teams that made the playoffs
    playoff_teams = train_df[train_df[y_column].isin([0, 1])][['team', 'year']].drop_duplicates()
    
    # Get the averages and outcomes for playoff teams
    X = all_averages.loc[playoff_teams.set_index(['team', 'year']).index]
    y = train_df[train_df[y_column].isin([0, 1])].groupby(['team', 'year'])[y_column].first()
    
    # Ensure X and y have the same index
    X = X.loc[y.index]
    
    # Scale the features
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns, index=X.index)
    
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
    
    return X_train, X_test, y_train, y_test

X_train_rdone, X_test_rdone, y_train_rdone, y_test_rdone = split_data('yoffs_rdone')
X_train_rtwo, X_test_rtwo, y_train_rtwo, y_test_rtwo = split_data('yoffs_rtwo')
X_train_rdthr, X_test_rdthr, y_train_rdthr, y_test_rdthr = split_data('yoffs_rdthr')
X_train_champ, X_test_champ, y_train_champ, y_test_champ = split_data('yoffs_champ')

X_train_rdone_diff = X_train_rdone.apply(calculate_differentials, axis=1)
X_test_rdone_diff = X_test_rdone.apply(calculate_differentials, axis=1)
X_train_rtwo_diff = X_train_rtwo.apply(calculate_differentials, axis=1)
X_test_rtwo_diff = X_test_rtwo.apply(calculate_differentials, axis=1)
X_train_rdthr_diff = X_train_rdthr.apply(calculate_differentials, axis=1)
X_test_rdthr_diff = X_test_rdthr.apply(calculate_differentials, axis=1)
X_train_champ_diff = X_train_champ.apply(calculate_differentials, axis=1)
X_test_champ_diff = X_test_champ.apply(calculate_differentials, axis=1)

coefficients_rdone = individual_regressions(X_train_rdone_diff, y_train_rdone)
coefficients_rtwo = individual_regressions(X_train_rtwo_diff, y_train_rtwo)
coefficients_rdthr = individual_regressions(X_train_rdthr_diff, y_train_rdthr)
coefficients_champ = individual_regressions(X_train_champ_diff, y_train_champ)

X_weighted_rdone = apply_coefficients(X_train_rdone_diff, coefficients_rdone)
X_weighted_rtwo = apply_coefficients(X_train_rtwo_diff, coefficients_rtwo)
X_weighted_rdthr = apply_coefficients(X_train_rdthr_diff, coefficients_rdthr)
X_weighted_champ = apply_coefficients(X_train_champ_diff, coefficients_champ)

# Calculate Averages for Playoff Teams
playoff_averages_rdone = get_playoff_rolling_averages(train_df, 'yoffs_rdone')
playoff_averages_rtwo = get_playoff_rolling_averages(train_df, 'yoffs_rtwo')
playoff_averages_rdthr = get_playoff_rolling_averages(train_df, 'yoffs_rdthr')
playoff_averages_champ = get_playoff_rolling_averages(train_df, 'yoffs_champ')

#playoff_averages_rdone = playoff_averages_rdone[X_train_rdone.columns]
#playoff_averages_rtwo = playoff_averages_rtwo[X_train_rtwo.columns]
#playoff_averages_rdthr = playoff_averages_rdthr[X_train_rdthr.columns]
#playoff_averages_champ = playoff_averages_champ[X_train_champ.columns]

# Calculate differentials for playoff averages
playoff_averages_rdone = calculate_differentials(playoff_averages_rdone)
playoff_averages_rtwo = calculate_differentials(playoff_averages_rtwo)
playoff_averages_rdthr = calculate_differentials(playoff_averages_rdthr)
playoff_averages_champ = calculate_differentials(playoff_averages_champ)

playoff_averages_rdone = apply_coefficients(playoff_averages_rdone, coefficients_rdone)
playoff_averages_rtwo = apply_coefficients(playoff_averages_rtwo, coefficients_rtwo)
playoff_averages_rdthr = apply_coefficients(playoff_averages_rdthr, coefficients_rdthr)
playoff_averages_champ = apply_coefficients(playoff_averages_champ, coefficients_champ)

# Function to calculate differences from playoff averages
def calculate_differences(X, playoff_averages):
    differences = pd.DataFrame(index=X.index)
    
    for feature in differential_columns:
        diff = X[feature] - playoff_averages[feature]
        if feature in invert_features:
            diff = -diff
        differences[feature] = diff
    
    return differences

# Calculate Differences
X_diff_rdone = calculate_differences(X_weighted_rdone, playoff_averages_rdone)
X_diff_rtwo = calculate_differences(X_weighted_rtwo, playoff_averages_rtwo)
X_diff_rdthr = calculate_differences(X_weighted_rdthr, playoff_averages_rdthr)
X_diff_champ = calculate_differences(X_weighted_champ, playoff_averages_champ)

# Function to train a model
def train_model(X_train, y_train):
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model

print(f"Shape of X_train_rdone: {X_train_rdone.shape}")
print(f"Shape of y_train_rdone: {y_train_rdone.shape}")
print(f"Shape of X_weighted_rdone: {X_weighted_rdone.shape}")
print(f"Shape of X_diff_rdone: {X_diff_rdone.shape}")

# Train models for each round
model_rdone = train_model(X_diff_rdone, y_train_rdone)
model_rtwo = train_model(X_diff_rtwo, y_train_rtwo)
model_rdthr = train_model(X_diff_rdthr, y_train_rdthr)
model_champ = train_model(X_diff_champ, y_train_champ)

def clip_probabilities(predictions):
    return np.clip(predictions, 0.001, 0.999)

def format_prediction(prediction):
    # Adjust the prediction
    if prediction > 50:
        adjusted_pred = 99
    elif prediction < -50:
        adjusted_pred = 1
    else:
        adjusted_pred = 50 + prediction    
    
    # Convert the adjusted prediction to a percentage
    percentage = adjusted_pred / 100
    
    # Ensure the prediction is between 0 and 1
    formatted_pred = clip_probabilities(percentage)
    
    return formatted_pred

# Identify the first occurrence where both yoffs_rdone and yoffs_rtwo are not null in the same row
def get_initial_round_to_predict(team_data):
    for index, row in team_data.iterrows():
        if pd.notnull(row['yoffs_rdone']) and pd.notnull(row['yoffs_rtwo']):
            return 'yoffs_rtwo'
        elif pd.notnull(row['yoffs_rdone']):
            return 'yoffs_rdone'
    return 'yoffs_rdone'  # Default to yoffs_rdone if neither condition is met

def adjust_predictions(pred1, pred2):
    if pred1 > 0.5 and pred2 > 0.5:
        higher = max(pred1, pred2)
        lower = 1 - higher
    elif pred1 < 0.5 and pred2 < 0.5:
        lower = min(pred1, pred2)
        higher = 1 - lower
    else:
        diff = abs(pred1 - pred2) / 2
        higher = 0.5 + diff
        lower = 0.5 - diff
    return (higher, lower) if pred1 >= pred2 else (lower, higher)

def find_matching_game(df, team, opponent, year):
    team_games = df[(df['team'] == team) & (df['year'] == year) & (df['round_opp'] == opponent)]
    opponent_games = df[(df['team'] == opponent) & (df['year'] == year) & (df['round_opp'] == team)]
    
    print(f"Searching for match: Team: {team}, Opponent: {opponent}, Year: {year}")
    
    team_game = None
    opponent_game = None
    
    playoff_pred_columns = ['yoffs_champ_pred', 'yoffs_rdthr_pred', 'yoffs_rdtwo_pred', 'yoffs_rdone_pred']
    
    if not team_games.empty:
        # Find the most recent game with a playoff prediction
        for _, game in team_games.sort_values('games_played', ascending=False).iterrows():
            for col in playoff_pred_columns:
                if pd.notnull(game[col]):
                    team_game = game
                    print(f"Team game found: games_played = {team_game['games_played']}, prediction column = {col}, prediction = {team_game[col]}")
                    break
            if team_game is not None:
                break
    if team_game is None:
        print("Team game not found")
    
    if not opponent_games.empty:
        # Find the most recent game with a playoff prediction
        for _, game in opponent_games.sort_values('games_played', ascending=False).iterrows():
            for col in playoff_pred_columns:
                if pd.notnull(game[col]):
                    opponent_game = game
                    print(f"Opponent game found: games_played = {opponent_game['games_played']}, prediction column = {col}, prediction = {opponent_game[col]}")
                    break
            if opponent_game is not None:
                break
    if opponent_game is None:
        print("Opponent game not found")
    
    return team_game, opponent_game

def get_round_from_pred_column(pred_column):
    if pred_column.endswith('rdtwo_pred'):
        return 'yoffs_rtwo'
    else:
        return pred_column.replace('_pred', '')

def evaluate_accuracy(df, year):
    valid_predictions = []
    valid_actuals = []
    teams = df[df['year'] == year]['team'].unique()
    evaluated_pairs = set()  # To keep track of which team pairs we've already evaluated

    playoff_columns = ['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone']
    pred_columns = ['yoffs_champ_pred', 'yoffs_rdthr_pred', 'yoffs_rdtwo_pred', 'yoffs_rdone_pred']

    for team in teams:
        team_data = df[(df['team'] == team) & (df['year'] == year)]
        
        for actual_col, pred_col in zip(playoff_columns, pred_columns):
            # Find the first game where both the actual and prediction columns are not null
            playoff_game = team_data[(pd.notnull(team_data[actual_col])) & (pd.notnull(team_data[pred_col]))].iloc[0] if not team_data[(pd.notnull(team_data[actual_col])) & (pd.notnull(team_data[pred_col]))].empty else None
            
            if playoff_game is not None:
                opponent = playoff_game['round_opp']
                
                # Check if we've already evaluated this matchup
                if frozenset([team, opponent]) in evaluated_pairs:
                    continue
                
                # Find the corresponding game for the opponent
                opponent_data = df[(df['team'] == opponent) & (df['year'] == year)]
                opponent_game = opponent_data[(opponent_data['round_opp'] == team) & (pd.notnull(opponent_data[actual_col])) & (pd.notnull(opponent_data[pred_col]))].iloc[0] if not opponent_data[(opponent_data['round_opp'] == team) & (pd.notnull(opponent_data[actual_col])) & (pd.notnull(opponent_data[pred_col]))].empty else None
                
                if opponent_game is not None:
                    # Team prediction
                    team_actual = int(playoff_game[actual_col])
                    team_pred = playoff_game[pred_col]
                    team_pred_binary = 1 if team_pred > 0.5 else 0
                    
                    # Opponent prediction
                    opponent_actual = int(opponent_game[actual_col])
                    opponent_pred = opponent_game[pred_col]
                    opponent_pred_binary = 1 if opponent_pred > 0.5 else 0
                    
                    valid_predictions.extend([team_pred_binary, opponent_pred_binary])
                    valid_actuals.extend([team_actual, opponent_actual])
                    
                    print(f"Accuracy Update: Year: {year}, {team} vs {opponent}, Round: {actual_col}")
                    print(f"{team}: Prediction: {team_pred_binary} (Prob: {team_pred:.4f}), Actual: {team_actual}")
                    print(f"{opponent}: Prediction: {opponent_pred_binary} (Prob: {opponent_pred:.4f}), Actual: {opponent_actual}")
                    
                    # Mark this matchup as evaluated
                    evaluated_pairs.add(frozenset([team, opponent]))

    if valid_predictions and valid_actuals:
        accuracy = accuracy_score(valid_actuals, valid_predictions)
        print(f"Year {year} Accuracy: {accuracy:.4f}")
    else:
        print(f"No valid predictions for year {year}")

    return valid_predictions, valid_actuals

# Predict and update for each team and year
def make_predictions(years):
    all_predictions = []
    all_actuals = []
    
    for year in years:
        year_predictions = {} # ignore this shit was for something else
        teams = df[df['year'] == year]['team'].unique()
        max_games = df[df['year'] == year]['games_played'].max()
        for games_played in range(1, max_games + 1):
            game_predictions = {}
            teams = df[(df['year'] == year) & (df['games_played'] == games_played)]['team'].unique()

            for team in teams:
                team_data = df[(df['team'] == team) & (df['year'] == year)].sort_values(by='games_played')
                row = df[(df['team'] == team) & (df['year'] == year) & (df['games_played'] == games_played)].iloc[0]

                if games_played <= 6:
                    round_to_predict = get_initial_round_to_predict(team_data)
                else:
                    playoff_columns = ['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone']
                    round_to_predict = next((col for col in playoff_columns if pd.notnull(row[col])), None)
                if round_to_predict:
                    pred_column = round_to_predict + "_pred" if round_to_predict != 'yoffs_rtwo' else 'yoffs_rdtwo_pred'

                    rolling_averages = calculate_rolling_averages(df, team, year, row['games_played'], feature_columns)
                    rolling_differentials = calculate_differentials(rolling_averages)

                    # Calculate the differences between rolling averages and playoff averages
                    if round_to_predict == 'yoffs_rdone':
                        coefficients = coefficients_rdone
                        playoff_averages = playoff_averages_rdone
                    elif round_to_predict == 'yoffs_rtwo':
                        coefficients = coefficients_rtwo
                        playoff_averages = playoff_averages_rtwo
                    elif round_to_predict == 'yoffs_rdthr':
                        coefficients = coefficients_rdthr
                        playoff_averages = playoff_averages_rdthr
                    elif round_to_predict == 'yoffs_champ':
                        coefficients = coefficients_champ
                        playoff_averages = playoff_averages_champ
                        
                    print(f"Coefficients for {round_to_predict}:")
                    for feature, coeff in coefficients.items():
                        if isinstance(coeff, np.ndarray):
                            print(f"{feature}: mean = {coeff.mean():.4f}, max = {coeff.max():.4f}")
                        else:
                            print(f"{feature}: {coeff:.4f}")

                    # Apply coefficients and calculate differences
                    weighted_averages = []
                    for feature, avg in zip(feature_columns, rolling_differentials):
                        if feature in coefficients:
                            if isinstance(coefficients[feature], np.ndarray):
                                mean_coeff = coefficients[feature].mean()
                            else:
                                mean_coeff = coefficients[feature]
                            weighted_avg = avg * mean_coeff
                        else:
                            weighted_avg = avg
                        weighted_averages.append(weighted_avg)
                    
                    diffs = []
                    for feature, wa, pa in zip(feature_columns, weighted_averages, playoff_averages):
                        diff = wa - pa
                        if feature in invert_features:
                            diff = -diff  # Invert the difference for specified features
                        diffs.append(diff)

                    # Debug prints
                    print(f"Rolling differentials: {rolling_differentials}")
                    print(f"Correlated differentials: {weighted_averages}")
                    print(f"Playoff differentials for {round_to_predict}: {playoff_averages}")
                    print(f"Differences: {diffs}")

                    wdiff = np.array(diffs)  # Convert list to numpy array
                    print(f"Differences: {wdiff}")

                    # Select the appropriate model for the round
                    if round_to_predict == 'yoffs_rdone':
                        prediction = predict_round_advancement(model_rdone, wdiff.reshape(1, -1))
                    elif round_to_predict == 'yoffs_rtwo':
                        prediction = predict_round_advancement(model_rtwo, wdiff.reshape(1, -1))
                    elif round_to_predict == 'yoffs_rdthr':
                        prediction = predict_round_advancement(model_rdthr, wdiff.reshape(1, -1))
                    elif round_to_predict == 'yoffs_champ':
                        prediction = predict_round_advancement(model_champ, wdiff.reshape(1, -1))

                    column_pred = round_to_predict + "_pred" if round_to_predict != 'yoffs_rtwo' else 'yoffs_rdtwo_pred'
                    
                    pred = format_prediction(prediction)
                    if isinstance(pred, (list, np.ndarray)):
                        pred = pred[0]
                        
                    game_predictions[team] = {
                        'pred_column': pred_column,
                        'pred': pred,
                        'opponent': row['round_opp'],
                        'actual': row[round_to_predict]
                    }

                    with hotstreak_engine.begin() as conn:
                        conn.execute(
                            text(f"""
                                UPDATE [dbo].[Football-Stats] 
                                SET {column_pred} = :pred 
                                WHERE team = :team AND year = :year AND games_played >= :games_played
                            """),
                            {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(row['games_played'])}
                        )

                    # Also update the DataFrame
                    df.loc[(df['team'] == team) & (df['year'] == year) & (df['games_played'] >= row['games_played']), column_pred] = pred
                    
            if games_played >= 6:     
                # Adjust predictions for this game
                adjusted_predictions = {}
                for team, pred_info in game_predictions.items():
                    opponent = pred_info['opponent']
                    print(f"Checking team: {team}, Opponent: {opponent}")
        
                    team_row, opponent_row = find_matching_game(df, team, opponent, year)
        
                    if team_row is not None and opponent_row is not None:
                        playoff_pred_columns = ['yoffs_champ_pred', 'yoffs_rdthr_pred', 'yoffs_rdtwo_pred', 'yoffs_rdone_pred']
                        team_pred_column = next((col for col in playoff_pred_columns if pd.notnull(team_row[col])), None)
                        opponent_pred_column = next((col for col in playoff_pred_columns if pd.notnull(opponent_row[col])), None)
            
                        if team_pred_column and opponent_pred_column:
                            team_pred = team_row[team_pred_column]
                            opponent_pred = opponent_row[opponent_pred_column]
                            print(f"Team prediction: {team_pred}, Opponent prediction: {opponent_pred}")

                            if team_pred is not None and opponent_pred is not None:
                                adjusted_pred, adjusted_opponent_pred = adjust_predictions(team_pred, opponent_pred)
                                print(f"Adjusted predictions: Team: {adjusted_pred}, Opponent: {adjusted_opponent_pred}")
                                team_round_to_predict = get_round_from_pred_column(team_pred_column)
                                opponent_round_to_predict = get_round_from_pred_column(opponent_pred_column)

    
                                adjusted_predictions[team] = {
                                    'pred': adjusted_pred,
                                    'games_played': team_row['games_played'],
                                    'pred_column': team_pred_column,
                                    'round_to_predict': team_round_to_predict
                                }
                                adjusted_predictions[opponent] = {
                                    'pred': adjusted_opponent_pred,
                                    'games_played': opponent_row['games_played'],
                                    'pred_column': opponent_pred_column,
                                    'round_to_predict': opponent_round_to_predict
                                }
                            else:
                                print("Unable to adjust predictions: missing data for one or both teams")
                        else:
                            print("Unable to find prediction columns for one or both teams")
                    else:
                        print("No matching games found for either team")

                # Update database and DataFrame with adjusted predictions
                for team, adj_info in adjusted_predictions.items():
                    pred = adj_info['pred']
                    games_played = adj_info['games_played']
                    pred_column = adj_info['pred_column']
                    team_round_to_predict = adj_info['round_to_predict']
    
                    with hotstreak_engine.begin() as conn:
                        conn.execute(
                            text(f"UPDATE [dbo].[Football-Stats] SET {pred_column} = :pred WHERE team = :team AND year = :year AND games_played = :games_played"),
                            {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(games_played)}
                        )
    
                    df.loc[(df['team'] == team) & (df['year'] == year) & (df['games_played'] == games_played), pred_column] = pred
                    print("-" * 50)
                    print(f"Adjusted Prediction Update: Team: {team}, Year: {year}, Games Played: {games_played}")
                    print(f"Column: {pred_column}, Adjusted Prediction: {pred:.4f}")
                    print(f"Database and DataFrame updated with adjusted prediction: {pred:.4f}")

                    # Update subsequent games if necessary
                    team_data = df[(df['team'] == team) & (df['year'] == year)]
                    subsequent_games = team_data[team_data['games_played'] > games_played]
                    for idx, subsequent_row in subsequent_games.iterrows():
                        actual_column = team_round_to_predict
                        if pd.isnull(subsequent_row[actual_column]):  # Only update if actual result is not available
                            df.at[idx, pred_column] = pred
                            with hotstreak_engine.connect() as conn:
                                conn.execute(
                                    text(f"UPDATE [dbo].[Football-Stats] SET {pred_column} = :pred WHERE team = :team AND year = :year AND games_played = :games_played"),
                                    {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(subsequent_row['games_played'])}
                                )
            # Store predictions for this game - ignore this shit was for something else
            if year not in year_predictions:
                year_predictions[year] = {}
            year_predictions[year][games_played] = game_predictions
            
        year_preds, year_actuals = evaluate_accuracy(df, year)
        all_predictions.extend(year_preds)
        all_actuals.extend(year_actuals)
                
    if all_predictions and all_actuals:
        overall_accuracy = accuracy_score(all_actuals, all_predictions)
        print(f"Overall Accuracy: {overall_accuracy:.4f}")
    else:
        print("No valid predictions overall")

# Make predictions for training data (2000-2022)
make_predictions(list(range(2000, 2023)))

# Prepare 2023 data for prediction
test_2023_df = df[df['year'] == 2023]
X_2023 = test_2023_df[feature_columns]
X_2023_scaled = pd.DataFrame(scaler.transform(X_2023), columns=feature_columns)

make_predictions([2023])

print("Predictions updated for 2023.")
