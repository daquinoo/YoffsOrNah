import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

# Database connection using SQLAlchemy
database_url = 'mssql+pyodbc://danny1phantom:{pwd}@yoffsornah.database.windows.net:1433/YoffsOrNah-train-NFL?driver=ODBC+Driver+18+for+SQL+Server'
engine = create_engine(database_url)

# Load Data
query = "SELECT * FROM [dbo].[Football-Training-Stats]"
df = pd.read_sql(query, engine)

# Preprocess Data
df = df.dropna()

# Filter Data for Training (2000-2022)
train_df = df[df['year'] <= 2022]

# Extract Features and Target
features = train_df.columns.difference(['year', 'team', 'yoffs'])
features = features.difference(['div'])
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
playoff_averages = X[df['yoffs'].reindex(X.index) == 1].mean()

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
            text("SELECT COUNT(*) FROM [dbo].[Football-Predict-Stats] WHERE team = :team AND year = :year"),
            {'team': team, 'year': year}
        ).fetchone()
        
        if result[0] > 0:
            # Update the existing row
            conn.execute(
                text("UPDATE [dbo].[Football-Predict-Stats] SET yoffs_pred = :yoffs_pred WHERE team = :team AND year = :year"),
                {'yoffs_pred': yoffs_pred, 'team': team, 'year': year}
            )
            updated_count += 1
            print(f"Updated team: {team}, year: {year}, yoffs_pred: {yoffs_pred}")
        else:
            # Insert new row
            conn.execute(
                text("INSERT INTO [dbo].[Football-Predict-Stats] (year, team, yoffs_pred) VALUES (:year, :team, :yoffs_pred)"),
                {'year': year, 'team': team, 'yoffs_pred': yoffs_pred}
            )
            inserted_count += 1
            print(f"Inserted team: {team}, year: {year}, yoffs_pred: {yoffs_pred}")
    
    if updated_count == 0 and inserted_count == 0:
        print("No rows were inserted or updated.")

# Predict for 2023
# Filter Data for 2023 to use as input for 2023 prediction
test_2023_df = df[df['year'] == 2023]
X_2023 = test_2023_df[features]
X_2023_scaled = pd.DataFrame(scaler.transform(X_2023), columns=X_2023.columns)

# Calculate differences for 2023 Data
X_2023_diff = calculate_differences(X_2023_scaled, playoff_averages)

# Predict using the model and apply clipping
yoffs_pred_too = model_multiple_diff.predict(X_2023_diff)
yoffs_pred_too_adjusted = clip_probabilities(yoffs_pred_too)

# Round to 3 decimal places
yoffs_pred_too_adjusted = np.round(yoffs_pred_too_adjusted, 3)

# Create new DataFrame for 2023 Predictions
pred_2023_df = test_2023_df[['team']].copy()
pred_2023_df['year'] = 2023
pred_2023_df['yoffs_pred'] = yoffs_pred_too_adjusted

# Load the actual 2023 values for comparison
actual_2023_df = df[df['year'] == 2023]
actual_yoffs_2023 = actual_2023_df['yoffs'].values

# Evaluate accuracy of 2023 predictions
accuracy_2023 = accuracy_score(actual_yoffs_2023, yoffs_pred_too_adjusted > 0.5)
print(f'2023 Prediction Accuracy: {accuracy_2023}')

# Update Database with Predictions for 2023
with engine.connect() as conn:
    for index, row in pred_2023_df.iterrows():
        team = row['team']
        year = row['year']
        yoffs_pred = row['yoffs_pred']
        
        # Corrected SQL execution
        result = conn.execute(
            text("SELECT COUNT(*) FROM [dbo].[Football-Predict-Stats] WHERE team = :team AND year = :year"),
            {'team': team, 'year': year}
        ).fetchone()
        
        if result[0] > 0:
            # Update the existing row
            conn.execute(
                text("UPDATE [dbo].[Football-Predict-Stats] SET yoffs_pred = :yoffs_pred WHERE team = :team AND year = :year"),
                {'yoffs_pred': yoffs_pred, 'team': team, 'year': year}
            )
        else:
            # Insert new row
            conn.execute(
                text("INSERT INTO [dbo].[Football-Predict-Stats] (year, team, yoffs_pred) VALUES (:year, :team, :yoffs_pred)"),
                {'year': year, 'team': team, 'yoffs_pred': yoffs_pred}
            )


