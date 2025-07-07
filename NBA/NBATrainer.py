import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

# Database connection using SQLAlchemy
database_url = 'mssql+pyodbc://danny1phantom:{pwd}@yoffsornah.database.windows.net:1433/YoffsOrNah-train-NBA?driver=ODBC+Driver+18+for+SQL+Server'
engine = create_engine(database_url)

# Load Data
query = "SELECT * FROM [dbo].[Basketball-Training-Stats]"
df = pd.read_sql(query, engine)

# Preprocess Data
df = df.dropna().reset_index(drop=True)

# Filter Data for Training (2000-2022)
train_df = df[df['year'] <= 2023].reset_index(drop=True)

# Extract Features and Target
features = train_df.columns.difference(['year', 'team', 'yoffs'])
features = features.difference(['conf'])
X = train_df[features]
y = train_df['yoffs']

# Standardize Features
scaler = StandardScaler()
X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)

# Split Data
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Function to perform individual linear regressions
def individual_regressions(X, y):
    model = LinearRegression()
    transformed_features = pd.DataFrame(index=X.index)
    
    for feature in X.columns:
        model.fit(X[[feature]], y)
        predictions = model.predict(X[[feature]])
        transformed_feature = np.where(predictions < 0.5, 1 - predictions, predictions)
        transformed_features[feature] = transformed_feature
    
    return transformed_features

# Calculate Averages for Playoff Teams
playoff_teams = train_df[train_df['yoffs'] == 1].reset_index(drop=True)
playoff_teams_scaled = X_scaled.loc[playoff_teams.index]
playoff_averages = playoff_teams_scaled.mean()

# Function to calculate differences from playoff averages
def calculate_differences(X, playoff_averages):
    differences = pd.DataFrame(index=X.index)
    
    for feature in X.columns:
        differences[feature] = X[feature] - playoff_averages[feature]
    
    return differences

# Calculate Differences
X_diff = calculate_differences(X_train, playoff_averages)

# Multiple Regression Model
model_multiple_diff = LinearRegression()
model_multiple_diff.fit(X_diff, y_train)

# Evaluate Approach 2
X_test_diff = calculate_differences(X_test, playoff_averages)
y_pred_2 = model_multiple_diff.predict(X_test_diff)

# Apply clipping to ensure probabilities are in range [0.001, 0.999]
def clip_probabilities(predictions):
    return np.clip(predictions, 0.001, 0.999)

y_pred_2_adjusted = clip_probabilities(y_pred_2)
y_pred_2_binary = np.where(y_pred_2_adjusted > 0.5, 1, 0)
accuracy_2 = accuracy_score(y_test, y_pred_2_binary)
print(f'Approach 2 Accuracy: {accuracy_2}')

# Predict for Training Data
X_train_diff = calculate_differences(X_scaled, playoff_averages)
yoffs_pred_train = model_multiple_diff.predict(X_train_diff)
yoffs_pred_train_adjusted = clip_probabilities(yoffs_pred_train)
yoffs_pred_train_adjusted = np.round(yoffs_pred_train_adjusted, 3)

# Create new DataFrame for Training Predictions
pred_train_df = train_df[['team', 'year']].copy()
pred_train_df['yoffs_pred'] = yoffs_pred_train_adjusted

# Update Database with Predictions for Training Data
with engine.begin() as conn:
    updated_count = 0
    inserted_count = 0
    for index, row in pred_train_df.iterrows():
        team = row['team']
        year = row['year']
        yoffs_pred = row['yoffs_pred']
        
        result = conn.execute(
            text("SELECT COUNT(*) FROM [dbo].[Basketball-Predict-Stats] WHERE team = :team AND year = :year"),
            {'team': team, 'year': year}
        ).fetchone()
        
        if result[0] > 0:
            # Update the existing row
            conn.execute(
                text("UPDATE [dbo].[Basketball-Predict-Stats] SET yoffs_pred = :yoffs_pred WHERE team = :team AND year = :year"),
                {'yoffs_pred': yoffs_pred, 'team': team, 'year': year}
            )
            updated_count += 1
            print(f"Updated team: {team}, year: {year}, yoffs_pred: {yoffs_pred}")
        else:
            # Insert new row
            conn.execute(
                text("INSERT INTO [dbo].[Basketball-Predict-Stats] (year, team, yoffs_pred) VALUES (:year, :team, :yoffs_pred)"),
                {'year': year, 'team': team, 'yoffs_pred': yoffs_pred}
            )
            inserted_count += 1
            print(f"Inserted team: {team}, year: {year}, yoffs_pred: {yoffs_pred}")
    
    if updated_count == 0 and inserted_count == 0:
        print("No rows were inserted or updated.")

# Predict for 2024
# Filter Data for 2024 to use as input for 2024 prediction
test_2024_df = df[df['year'] == 2024].reset_index(drop=True)
X_2024 = test_2024_df[features]
X_2024_scaled = pd.DataFrame(scaler.transform(X_2024), columns=X_2024.columns)

# Calculate differences for 2023 Data
X_2024_diff = calculate_differences(X_2024_scaled, playoff_averages)

# Predict using the model and apply clipping
yoffs_pred_2024 = model_multiple_diff.predict(X_2024_diff)
yoffs_pred_2024_adjusted = clip_probabilities(yoffs_pred_2024)

# Round to 3 decimal places
yoffs_pred_2024_adjusted = np.round(yoffs_pred_2024_adjusted, 3)

# Create new DataFrame for 2024 Predictions
pred_2024_df = test_2024_df[['team']].copy()
pred_2024_df['year'] = 2024
pred_2024_df['yoffs_pred'] = yoffs_pred_2024_adjusted

# Load the actual 2024 values for comparison
actual_2024_df = df[df['year'] == 2024].reset_index(drop=True)
actual_yoffs_2024 = actual_2024_df['yoffs'].values

# Evaluate accuracy of 2024 predictions
accuracy_2024 = accuracy_score(actual_yoffs_2024, yoffs_pred_2024_adjusted > 0.5)
print(f'2024 Prediction Accuracy: {accuracy_2024}')

# Update Database with Predictions for 2024
with engine.connect() as conn:
    for index, row in pred_2024_df.iterrows():
        team = row['team']
        year = row['year']
        yoffs_pred = row['yoffs_pred']
        
        result = conn.execute(
            text("SELECT COUNT(*) FROM [dbo].[Basketball-Predict-Stats] WHERE team = :team AND year = :year"),
            {'team': team, 'year': year}
        ).fetchone()
        
        if result[0] > 0:
            # Update the existing row
            conn.execute(
                text("UPDATE [dbo].[Basketball-Predict-Stats] SET yoffs_pred = :yoffs_pred WHERE team = :team AND year = :year"),
                {'yoffs_pred': yoffs_pred, 'team': team, 'year': year}
            )
        else:
            # Insert new row
            conn.execute(
                text("INSERT INTO [dbo].[Basketball-Predict-Stats] (year, team, yoffs_pred) VALUES (:year, :team, :yoffs_pred)"),
                {'year': year, 'team': team, 'yoffs_pred': yoffs_pred}
            )

