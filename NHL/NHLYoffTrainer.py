import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sqlalchemy import create_engine, text

# Database connection using SQLAlchemy
hotstreak_db_url = 'mssql+pyodbc://danny1phantom:{pwd}@yoffsornah.database.windows.net:1433/YoffsOrNah-HotStreak-ChampNBA?driver=ODBC+Driver+18+for+SQL+Server'
hotstreak_engine = create_engine(hotstreak_db_url)

# Load Data
query_stats = "SELECT * FROM [dbo].[Basketball-Stats] WHERE year >= 2000 AND year <= 2024"
df = pd.read_sql(query_stats, hotstreak_engine)

# Define relevant columns for features and target
feature_columns = [
    'win_pct', 'conf_stdg', 'lg_rank', 'pts_pg', 'opp_pts_pg', 'threes_pg', 'opp_three_pg',
    'fg_perc', 'opp_fg_perc', 'oreb_pg', 'opp_oreb_pg', 'ast_pg', 'opp_ast_pg',
    'fta_pg', 'opp_fta_pg', 'ft_perc', 'turnovers_pg', 'opp_to_pg', 'stls_pg',
    'opp_stls_pg', 'blocks_pg', 'opp_blks_pg', 'yoffs_pred', 'treb_pg', 'opp_treb_pg'
]

invert_features = [
    'conf_stdg', 'lg_rank', 'opp_pts_pg', 'opp_three_pg', 'opp_fg_perc', 
    'opp_oreb_pg', 'opp_ast_pg', 'opp_fta_pg', 'opp_to_pg', 'opp_stls_pg', 
    'opp_blks_pg', 'opp_treb_pg'
]

differential_columns = [
    'win_pct', 'conf_stdg', 'lg_rank', 'pts_diff', 'threes_diff',
    'fg_diff', 'oreb_diff', 'treb_diff', 'ast_diff', 'fta_diff',
    'to_diff', 'stls_diff', 'blocks_diff', 'ft_effectiveness', 'yoffs_pred'
]

def calculate_differentials(averages):
    differentials = {
        'win_pct': averages[0],
        'conf_stdg': averages[1],
        'lg_rank': averages[2],
        'pts_diff': averages[3] - averages[4],
        'threes_diff': averages[5] - averages[6],
        'fg_diff': averages[7] - averages[8],
        'oreb_diff': averages[9] - averages[10],
        'treb_diff': averages[23] - averages[24],
        'ast_diff': averages[11] - averages[12],
        'fta_diff': averages[13] - averages[14],
        'ft_effectiveness': averages[13] * averages[15],
        'to_diff': averages[16] - averages[17],
        'stls_diff': averages[18] - averages[19],
        'blocks_diff': averages[20] - averages[21],
        'yoffs_pred': averages[22]
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
    
    pred_values = team_data[pred_columns].iloc[-1]
    actual_values = team_data[actual_columns].iloc[-1]
    
    adjusted_preds = []
    for pred_col, actual_col in zip(pred_columns, actual_columns):
        pred = pred_values[pred_col]
        actual = actual_values[actual_col]
        
        if pd.notnull(pred) and pd.notnull(actual):
            if pred < 0.5 and actual == 1:
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
train_df = df[df['year'] <= 2023]
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
    else:
        for feature in differential_columns:
            if feature in coefficients:
                X_weighted[feature] *= coefficients[feature]
    return X_weighted

def split_data(y_column):
    def get_team_averages(group):
        round_index = {
            'yoffs_rdone': 0,
            'yoffs_rtwo': 1,
            'yoffs_rdthr': 2,
            'yoffs_champ': 3
        }
    
        playoff_games = group[group[y_column].notnull()].sort_values('games_played')
    
        if not playoff_games.empty:
            index = round_index.get(y_column, 0)
            if index < len(playoff_games):
                first_playoff_game = playoff_games.iloc[index]
            else:
                first_playoff_game = playoff_games.iloc[-1]
        else:
            first_playoff_game = group.iloc[-1]
    
        return calculate_rolling_averages(group, group.name[0], group.name[1], first_playoff_game['games_played'], feature_columns)

    all_averages = train_df.groupby(['team', 'year']).apply(get_team_averages)
    all_averages = pd.DataFrame(all_averages.tolist(), index=all_averages.index, columns=feature_columns)
    
    playoff_teams = train_df[train_df[y_column].isin([0, 1])][['team', 'year']].drop_duplicates()
    
    X = all_averages.loc[playoff_teams.set_index(['team', 'year']).index]
    
    if y_column == 'yoffs_rdone':
        y = train_df[train_df[y_column].isin([0, 1])].groupby(['team', 'year'])[y_column].first()
    else:
        n = {'yoffs_rtwo': 2, 'yoffs_rdthr': 3, 'yoffs_champ': 4}[y_column]
        y = train_df[train_df[y_column].isin([0, 1])].groupby(['team', 'year']).apply(lambda x: x.iloc[n-1][y_column] if len(x) >= n else None)
        y = y.dropna()
        
    print(f"Debug: y_column = {y_column}")
    print(f"Debug: X shape = {X.shape}")
    print(f"Debug: y shape = {y.shape}")
    print(f"Debug: X index = {X.index}")
    print(f"Debug: y index = {y.index}")
    print(f"Debug: Difference in indices: X - y = {set(X.index) - set(y.index)}")
    print(f"Debug: Difference in indices: y - X = {set(y.index) - set(X.index)}")
    
    X = X.loc[y.index]
    
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

playoff_averages_rdone = get_playoff_rolling_averages(train_df, 'yoffs_rdone')
playoff_averages_rtwo = get_playoff_rolling_averages(train_df, 'yoffs_rtwo')
playoff_averages_rdthr = get_playoff_rolling_averages(train_df, 'yoffs_rdthr')
playoff_averages_champ = get_playoff_rolling_averages(train_df, 'yoffs_champ')

playoff_averages_rdone = calculate_differentials(playoff_averages_rdone)
playoff_averages_rtwo = calculate_differentials(playoff_averages_rtwo)
playoff_averages_rdthr = calculate_differentials(playoff_averages_rdthr)
playoff_averages_champ = calculate_differentials(playoff_averages_champ)

playoff_averages_rdone = apply_coefficients(playoff_averages_rdone, coefficients_rdone)
playoff_averages_rtwo = apply_coefficients(playoff_averages_rtwo, coefficients_rtwo)
playoff_averages_rdthr = apply_coefficients(playoff_averages_rdthr, coefficients_rdthr)
playoff_averages_champ = apply_coefficients(playoff_averages_champ, coefficients_champ)

def calculate_differences(X, playoff_averages):
    differences = pd.DataFrame(index=X.index)
    
    for feature in differential_columns:
        diff = X[feature] - playoff_averages[feature]
        if feature in invert_features:
            diff = -diff
        differences[feature] = diff
    
    return differences

X_diff_rdone = calculate_differences(X_weighted_rdone, playoff_averages_rdone)
X_diff_rtwo = calculate_differences(X_weighted_rtwo, playoff_averages_rtwo)
X_diff_rdthr = calculate_differences(X_weighted_rdthr, playoff_averages_rdthr)
X_diff_champ = calculate_differences(X_weighted_champ, playoff_averages_champ)

def train_model(X_train, y_train):
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model

print(f"Shape of X_train_rdone: {X_train_rdone.shape}")
print(f"Shape of y_train_rdone: {y_train_rdone.shape}")
print(f"Shape of X_weighted_rdone: {X_weighted_rdone.shape}")
print(f"Shape of X_diff_rdone: {X_diff_rdone.shape}")

model_rdone = train_model(X_diff_rdone, y_train_rdone)
model_rtwo = train_model(X_diff_rtwo, y_train_rtwo)
model_rdthr = train_model(X_diff_rdthr, y_train_rdthr)
model_champ = train_model(X_diff_champ, y_train_champ)

def clip_probabilities(predictions):
    return np.clip(predictions, 0.001, 0.999)

def format_prediction(prediction):
    if prediction > 50:
        adjusted_pred = 99
    elif prediction < -50:
        adjusted_pred = 1
    else:
        adjusted_pred = 50 + prediction    
    
    percentage = adjusted_pred / 100
    
    formatted_pred = clip_probabilities(percentage)
    
    return formatted_pred

def get_initial_round_to_predict(team_data):
    '''
    for index, row in team_data.iterrows():
        if pd.notnull(row['yoffs_rdone']) and pd.notnull(row['yoffs_rtwo']):
            return 'yoffs_rtwo'
        elif pd.notnull(row['yoffs_rdone']):
            return 'yoffs_rdone' 
    '''
    return 'yoffs_rdone'

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

def find_matching_game(df, team, opponent, year, current_games_played):
    team_games = df[(df['team'] == team) & (df['year'] == year) & (df['round_opp'] == opponent)].sort_values('games_played')
    opponent_games = df[(df['team'] == opponent) & (df['year'] == year) & (df['round_opp'] == team)].sort_values('games_played')
    
    print(f"Searching for match: Team: {team}, Opponent: {opponent}, Year: {year}, Current Games Played: {current_games_played}")
    
    team_game = None
    opponent_game = None
    
    playoff_columns = ['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone']
    playoff_pred_columns = ['yoffs_champ_pred', 'yoffs_rdthr_pred', 'yoffs_rdtwo_pred', 'yoffs_rdone_pred']
    
    print(f"Team games in series:")
    print(team_games[['games_played'] + playoff_pred_columns])
    print(f"Opponent games in series:")
    print(opponent_games[['games_played'] + playoff_pred_columns])
    
    if not team_games.empty and not opponent_games.empty:
        team_series_start = team_games['games_played'].min()
        opponent_series_start = opponent_games['games_played'].min()
        
        team_game_index = current_games_played - team_series_start
        opponent_game_index = team_game_index
        
        print(f"Team series start: {team_series_start}, Opponent series start: {opponent_series_start}")
        print(f"Team game index: {team_game_index}, Opponent game index: {opponent_game_index}")
        
        if team_game_index < len(team_games) and opponent_game_index < len(opponent_games):
            team_game = team_games.iloc[team_game_index]
            opponent_game = opponent_games.iloc[opponent_game_index]
            
            team_pred_column = next((col for col in playoff_pred_columns if pd.notnull(team_game[col])), None)
            opponent_pred_column = next((col for col in playoff_pred_columns if pd.notnull(opponent_game[col])), None)
            
            print(f"Team game selected: {team_game['games_played']}")
            print(f"Opponent game selected: {opponent_game['games_played']}")
            print(f"Team prediction columns: {[col for col in playoff_pred_columns if pd.notnull(team_game[col])]}")
            print(f"Opponent prediction columns: {[col for col in playoff_pred_columns if pd.notnull(opponent_game[col])]}")
            
            if team_pred_column and opponent_pred_column:
                print(f"Team game found: games_played = {team_game['games_played']}, prediction column = {team_pred_column}, prediction = {team_game[team_pred_column]}")
                print(f"Opponent game found: games_played = {opponent_game['games_played']}, prediction column = {opponent_pred_column}, prediction = {opponent_game[opponent_pred_column]}")
            else:
                print("No matching prediction columns found for team and opponent")
        else:
            print("No matching games found within the series")
    else:
        print("No games found for either team or opponent")
    
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
    evaluated_pairs = set()

    playoff_columns = ['yoffs_champ', 'yoffs_rdthr', 'yoffs_rtwo', 'yoffs_rdone']
    pred_columns = ['yoffs_champ_pred', 'yoffs_rdthr_pred', 'yoffs_rdtwo_pred', 'yoffs_rdone_pred']

    for team in teams:
        team_data = df[(df['team'] == team) & (df['year'] == year)]
        
        for actual_col, pred_col in zip(playoff_columns, pred_columns):
            playoff_game = team_data[(pd.notnull(team_data[actual_col])) & (pd.notnull(team_data[pred_col]))].iloc[0] if not team_data[(pd.notnull(team_data[actual_col])) & (pd.notnull(team_data[pred_col]))].empty else None
            
            if playoff_game is not None:
                opponent = playoff_game['round_opp']
                
                if frozenset([team, opponent]) in evaluated_pairs:
                    continue
                
                opponent_data = df[(df['team'] == opponent) & (df['year'] == year)]
                opponent_game = opponent_data[(opponent_data['round_opp'] == team) & (pd.notnull(opponent_data[actual_col])) & (pd.notnull(opponent_data[pred_col]))].iloc[0] if not opponent_data[(opponent_data['round_opp'] == team) & (pd.notnull(opponent_data[actual_col])) & (pd.notnull(opponent_data[pred_col]))].empty else None
                
                if opponent_game is not None:
                    team_actual = int(playoff_game[actual_col])
                    team_pred = playoff_game[pred_col]
                    team_pred_binary = 1 if team_pred > 0.5 else 0
                    
                    opponent_actual = int(opponent_game[actual_col])
                    opponent_pred = opponent_game[pred_col]
                    opponent_pred_binary = 1 if opponent_pred > 0.5 else 0
                    
                    valid_predictions.extend([team_pred_binary, opponent_pred_binary])
                    valid_actuals.extend([team_actual, opponent_actual])
                    
                    print(f"Accuracy Update: Year: {year}, {team} vs {opponent}, Round: {actual_col}")
                    print(f"{team}: Prediction: {team_pred_binary} (Prob: {team_pred:.4f}), Actual: {team_actual}")
                    print(f"{opponent}: Prediction: {opponent_pred_binary} (Prob: {opponent_pred:.4f}), Actual: {opponent_actual}")
                    
                    evaluated_pairs.add(frozenset([team, opponent]))

    if valid_predictions and valid_actuals:
        accuracy = accuracy_score(valid_actuals, valid_predictions)
        print(f"Year {year} Accuracy: {accuracy:.4f}")
    else:
        print(f"No valid predictions for year {year}")

    return valid_predictions, valid_actuals

def get_round_to_predict(row, prev_row, current_round=None):
    playoff_columns = ['yoffs_rdone', 'yoffs_rtwo', 'yoffs_rdthr', 'yoffs_champ']
    
    if current_round is None:
        # If no current round is specified, find the first null column
        return next((col for col in playoff_columns if pd.isnull(row[col])), None)
    else:
        current_index = playoff_columns.index(current_round)
        if prev_row is not None and pd.notnull(prev_row[current_round]):
            # Move to the next round
            for next_round in playoff_columns[current_index+1:]:
                if pd.isnull(row[next_round]):
                    return next_round
            return None  # All rounds completed
        else:
            # If the current round is still null in the previous row, keep predicting it
            return current_round

def make_predictions(years):
    all_predictions = []
    all_actuals = []
    
    for year in years:
        print(f"Processing year: {year}")
        max_games = df[df['year'] == year]['games_played'].max()
        teams = df[df['year'] == year]['team'].unique()
        
        team_rounds = {team: None for team in teams}
        
        for games_played in range(1, max_games + 1):
            print(f"Processing games_played: {games_played}")
            game_predictions = {}
            adjusted_predictions = {}
            
            for team in teams:
                team_data = df[(df['team'] == team) & (df['year'] == year)].sort_values('games_played')
                current_game_data = team_data[team_data['games_played'] == games_played]
                
                if current_game_data.empty:
                    print(f"No data for team {team} at games_played {games_played}. Skipping.")
                    continue
                
                row = current_game_data.iloc[0]
                # Get the previous row
                prev_row = team_data[team_data['games_played'] < games_played].iloc[-1] if games_played > 1 else None
            
                if games_played <= 6:
                    round_to_predict = get_initial_round_to_predict(team_data)
                else:
                    round_to_predict = get_round_to_predict(row, prev_row, current_round=team_rounds[team])
                
                team_rounds[team] = round_to_predict
                
                if round_to_predict:
                    pred_column = round_to_predict + "_pred" if round_to_predict != 'yoffs_rtwo' else 'yoffs_rdtwo_pred'
                    rolling_averages = calculate_rolling_averages(df, team, year, row['games_played'], feature_columns)
                    rolling_differentials = calculate_differentials(rolling_averages)
                    
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
                            diff = -diff
                        diffs.append(diff)
                    
                    print(f"Rolling differentials: {rolling_differentials}")
                    print(f"Correlated differentials: {weighted_averages}")
                    print(f"Playoff differentials for {round_to_predict}: {playoff_averages}")
                    print(f"Differences: {diffs}")
                    
                    wdiff = np.array(diffs)
                    print(f"Differences: {wdiff}")
                    
                    if round_to_predict == 'yoffs_rdone':
                        prediction = predict_round_advancement(model_rdone, wdiff.reshape(1, -1))
                    elif round_to_predict == 'yoffs_rtwo':
                        prediction = predict_round_advancement(model_rtwo, wdiff.reshape(1, -1))
                    elif round_to_predict == 'yoffs_rdthr':
                        prediction = predict_round_advancement(model_rdthr, wdiff.reshape(1, -1))
                    elif round_to_predict == 'yoffs_champ':
                        prediction = predict_round_advancement(model_champ, wdiff.reshape(1, -1))
                    
                    pred = format_prediction(prediction)
                    if isinstance(pred, (list, np.ndarray)):
                        pred = pred[0]
                    
                    game_predictions[team] = {
                        'pred_column': pred_column,
                        'pred': pred,
                        'opponent': row['round_opp'],
                        'actual': row[round_to_predict]
                    }
                    
                    df.loc[(df['team'] == team) & (df['year'] == year) & (df['games_played'] == games_played), pred_column] = pred
                    with hotstreak_engine.begin() as conn:
                        conn.execute(
                            text(f"UPDATE [dbo].[Basketball-Stats] SET {pred_column} = :pred WHERE team = :team AND year = :year AND games_played = :games_played"),
                            {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(games_played)}
                        )
                    
                    print(f"Initial Prediction: Team: {team}, Year: {year}, Games Played: {games_played}, Column: {pred_column}, Prediction: {pred:.4f}")
            
            # Adjust predictions
            if games_played >= 1:
                for team, pred_info in game_predictions.items():
                    opponent = pred_info['opponent']
                    if opponent in game_predictions and team not in adjusted_predictions:
                        team_row, opponent_row = find_matching_game(df, team, opponent, year, games_played)
                        if team_row is not None and opponent_row is not None:
                            playoff_pred_columns = ['yoffs_champ_pred', 'yoffs_rdthr_pred', 'yoffs_rdtwo_pred', 'yoffs_rdone_pred']
                            team_pred_column = next((col for col in playoff_pred_columns if pd.notnull(team_row[col])), None)
                            opponent_pred_column = next((col for col in playoff_pred_columns if pd.notnull(opponent_row[col])), None)
                            if team_pred_column and opponent_pred_column and team_pred_column == opponent_pred_column:
                                team_pred = team_row[team_pred_column]
                                opponent_pred = opponent_row[opponent_pred_column]
                                adjusted_team_pred, adjusted_opponent_pred = adjust_predictions(team_pred, opponent_pred)
                                adjusted_predictions[team] = {'pred': adjusted_team_pred, 'pred_column': team_pred_column}
                                adjusted_predictions[opponent] = {'pred': adjusted_opponent_pred, 'pred_column': opponent_pred_column}
                                print(f"Adjusted prediction for {team} vs {opponent}: {adjusted_team_pred:.4f} vs {adjusted_opponent_pred:.4f}")
                            else:
                                print(f"Skipping adjustment for {team} vs {opponent} due to mismatched prediction columns")
                        else:
                            print(f"Skipping adjustment for {team} vs {opponent} due to missing matching game")

            # Update predictions in DataFrame and database
            for team, pred_info in game_predictions.items():
                if team in adjusted_predictions:
                    pred = adjusted_predictions[team]['pred']
                    pred_column = adjusted_predictions[team]['pred_column']
                else:
                    pred = pred_info['pred']
                    pred_column = pred_info['pred_column']
    
                actual = pred_info['actual']
    
                df.loc[(df['team'] == team) & (df['year'] == year) & (df['games_played'] == games_played), pred_column] = pred
                with hotstreak_engine.begin() as conn:
                    conn.execute(
                        text(f"UPDATE [dbo].[Basketball-Stats] SET {pred_column} = :pred WHERE team = :team AND year = :year AND games_played = :games_played"),
                        {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(games_played)}
                    )
    
                print(f"Prediction Update: Team: {team}, Year: {year}, Games Played: {games_played}")
                print(f"Column: {pred_column}, Prediction: {pred:.4f}")
                
                # Add to predictions for accuracy evaluation only if actual is not null
                if pd.notnull(actual):
                    all_predictions.append(pred)
                    all_actuals.append(1 if actual == 1 else 0)
                    
                    # Spread this prediction to subsequent rows
                    subsequent_games = df[(df['team'] == team) & (df['year'] == year) & (df['games_played'] > games_played)]
                    for _, subsequent_row in subsequent_games.iterrows():
                        df.at[subsequent_row.name, pred_column] = pred
                        with hotstreak_engine.begin() as conn:
                            conn.execute(
                                text(f"UPDATE [dbo].[Basketball-Stats] SET {pred_column} = :pred WHERE team = :team AND year = :year AND games_played = :games_played"),
                                {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(subsequent_row['games_played'])}
                            )
                    print(f"Spread prediction {pred:.4f} to subsequent games for {team}")
        
        # Evaluate accuracy for the year
        year_preds, year_actuals = evaluate_accuracy(df, year)
        all_predictions.extend(year_preds)
        all_actuals.extend(year_actuals)
    
    # Calculate overall accuracy
    if all_predictions and all_actuals:
        binary_predictions = np.round(all_predictions).astype(int)
        overall_accuracy = accuracy_score(all_actuals, binary_predictions)
        print(f"Overall Accuracy: {overall_accuracy:.4f}")
    else:
        print("No valid predictions overall")

# Make predictions for training data (2000-2023)
make_predictions(list(range(2000, 2024)))

# Prepare 2024 data for prediction
test_2024_df = df[df['year'] == 2024]
X_2024 = test_2024_df[feature_columns]
X_2024_scaled = pd.DataFrame(scaler.transform(X_2024), columns=feature_columns)

make_predictions([2024])

print("Predictions updated for 2024.")

'''
def make_predictions(years):
    all_predictions = []
    all_actuals = []
    
    for year in years:
        year_predictions = {}
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
                    round_to_predict = get_round_to_predict(row, current_round=round_to_predict)
                if round_to_predict:
                    pred_column = round_to_predict + "_pred" if round_to_predict != 'yoffs_rtwo' else 'yoffs_rdtwo_pred'

                    rolling_averages = calculate_rolling_averages(df, team, year, row['games_played'], feature_columns)
                    rolling_differentials = calculate_differentials(rolling_averages)

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
                            diff = -diff
                        diffs.append(diff)

                    print(f"Rolling differentials: {rolling_differentials}")
                    print(f"Correlated differentials: {weighted_averages}")
                    print(f"Playoff differentials for {round_to_predict}: {playoff_averages}")
                    print(f"Differences: {diffs}")

                    wdiff = np.array(diffs)
                    print(f"Differences: {wdiff}")

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
                                UPDATE [dbo].[Basketball-Stats] 
                                SET {column_pred} = :pred 
                                WHERE team = :team AND year = :year AND games_played >= :games_played
                            """),
                            {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(row['games_played'])}
                        )

                    df.loc[(df['team'] == team) & (df['year'] == year) & (df['games_played'] >= row['games_played']), column_pred] = pred
                    
            if games_played >= 6:
                adjusted_predictions = {}
                for team in teams:
                    team_data = df[(df['team'] == team) & (df['year'] == year)].sort_values('games_played')

                    # Define adjustment ranges for each round
                    rdone_start = team_data[team_data['games_played'] >= 6]['games_played'].min()
                    rdone_end = team_data[team_data['yoffs_rdone'].notnull()]['games_played'].max() if not team_data[team_data['yoffs_rdone'].notnull()].empty else team_data['games_played'].max()
                    print(f"Round One: Start = {rdone_start}, End = {rdone_end}")

                    if rdone_end < team_data['games_played'].max():
                        rtwo_start = team_data[team_data['games_played'] > rdone_end]['games_played'].min()
                        rtwo_end = team_data[team_data['yoffs_rtwo'].notnull() & (team_data['games_played'] > rdone_end)]['games_played'].max() if not team_data[team_data['yoffs_rtwo'].notnull() & (team_data['games_played'] > rdone_end)].empty else team_data['games_played'].max()
                        print(f"Round Two: Start = {rtwo_start}, End = {rtwo_end}")

                        if rtwo_end < team_data['games_played'].max():
                            rdthr_start = team_data[team_data['games_played'] > rtwo_end]['games_played'].min()
                            rdthr_end = team_data[team_data['yoffs_rdthr'].notnull() & (team_data['games_played'] > rtwo_end)]['games_played'].max() if not team_data[team_data['yoffs_rdthr'].notnull() & (team_data['games_played'] > rtwo_end)].empty else team_data['games_played'].max()
                            print(f"Round Three: Start = {rdthr_start}, End = {rdthr_end}")

                            if rdthr_end < team_data['games_played'].max():
                                champ_start = team_data[team_data['games_played'] > rdthr_end]['games_played'].min()
                                champ_end = team_data[team_data['yoffs_champ'].notnull() & (team_data['games_played'] > rdthr_end)]['games_played'].max() if not team_data[team_data['yoffs_champ'].notnull() & (team_data['games_played'] > rdthr_end)].empty else team_data['games_played'].max()
                                print(f"Championship: Start = {champ_start}, End = {champ_end}")
                            else:
                                champ_start = champ_end = None
                        else:
                            rdthr_start = rdthr_end = None
                            champ_start = champ_end = None
                    else:
                        rtwo_start = rtwo_end = None
                        rdthr_start = rdthr_end = None
                        champ_start = champ_end = None

                    # Adjust predictions for each round
                    adjustment_ranges = [
                        ('yoffs_rdone_pred', rdone_start, rdone_end),
                        ('yoffs_rdtwo_pred', rtwo_start, rtwo_end),
                        ('yoffs_rdthr_pred', rdthr_start, rdthr_end),
                        ('yoffs_champ_pred', champ_start, champ_end)
                    ]

                    for pred_column, start, end in adjustment_ranges:
                        if start is not None and end is not None:
                            for games_played in range(start, end + 1):
                                row = team_data[team_data['games_played'] == games_played]
                                if not row.empty:
                                    opponent = row['round_opp'].values[0]
                                    if opponent:
                                        team_row, opponent_row = find_matching_game(df, team, opponent, year)
                                        if team_row is not None and opponent_row is not None:
                                            team_pred = team_row[pred_column]
                                            opponent_pred = opponent_row[pred_column]
                                            if team_pred is not None and opponent_pred is not None:
                                                adjusted_pred, _ = adjust_predictions(team_pred, opponent_pred)
                                                adjusted_predictions[(team, games_played)] = {
                                                    'pred': adjusted_pred,
                                                    'games_played': games_played,
                                                    'pred_column': pred_column,
                                                }
                                            else:
                                                print(f"Skipping adjustment for {team} at game {games_played} due to missing prediction")
                                        else:
                                            print(f"Skipping adjustment for {team} at game {games_played} due to missing match")
                                else:
                                    print(f"No data found for {team} at game {games_played}")

                # Update predictions in DataFrame and database
                for (team, idx), adj_info in adjusted_predictions.items():
                    pred = adj_info['pred']
                    games_played = adj_info['games_played']
                    pred_column = adj_info['pred_column']
        
                    df.at[idx, pred_column] = pred
                    with hotstreak_engine.begin() as conn:
                        conn.execute(
                            text(f"UPDATE [dbo].[Basketball-Stats] SET {pred_column} = :pred WHERE team = :team AND year = :year AND games_played = :games_played"),
                            {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(games_played)}
                        )
        
                    print(f"Adjusted Prediction Update: Team: {team}, Year: {year}, Games Played: {games_played}")
                    print(f"Column: {pred_column}, Adjusted Prediction: {pred:.4f}")
                    if pd.notnull(df.loc[idx, pred_column]):
                            # Update subsequent games with the last adjusted prediction
                            team_data = df[(df['team'] == team) & (df['year'] == year)]
                            subsequent_games = team_data[team_data['games_played'] > games_played]
                            for subsequent_idx, subsequent_row in subsequent_games.iterrows():
                                df.at[subsequent_idx, pred_column] = pred
                                with hotstreak_engine.connect() as conn:
                                    conn.execute(
                                        text(f"UPDATE [dbo].[Basketball-Stats] SET {pred_column} = :pred WHERE team = :team AND year = :year AND games_played = :games_played"),
                                        {'pred': pred, 'team': team, 'year': int(year), 'games_played': int(subsequent_row['games_played'])}
                                    )

        year_preds, year_actuals = evaluate_accuracy(df, year)
        all_predictions.extend(year_preds)
        all_actuals.extend(year_actuals)
                
    if all_predictions and all_actuals:
        overall_accuracy = accuracy_score(all_actuals, all_predictions)
        print(f"Overall Accuracy: {overall_accuracy:.4f}")
    else:
        print("No valid predictions overall")
'''
