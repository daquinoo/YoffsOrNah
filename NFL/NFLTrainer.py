import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine

# Database connection using SQLAlchemy
database_url = 'mssql+pyodbc://danny1phantom:Popp151565__@yoffsornah.database.windows.net:1433/YoffsOrNah-train-NFL?driver=ODBC+Driver+18+for+SQL+Server'
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

# Approach 1: Individual Linear Regressions Followed by Multiple Regression
# Individual Linear Regressions
X_transformed = individual_regressions(X_train, y_train)

# Multiple Regression Model
model_multiple = LinearRegression()
model_multiple.fit(X_transformed, y_train)

# Evaluate Approach 1
X_test_transformed = individual_regressions(X_test, y_test)
y_pred_1 = model_multiple.predict(X_test_transformed)
y_pred_1_binary = np.where(y_pred_1 > 0.5, 1, 0)
accuracy_1 = accuracy_score(y_test, y_pred_1_binary)
print(f'Approach 1 Accuracy: {accuracy_1}')

# Approach 2: Comparison with Average Playoff Team Statistics
# Calculate Averages for Playoff Teams
playoff_averages = X[df['yoffs'] == 1].mean()

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
y_pred_2_binary = np.where(y_pred_2 > 0.5, 1, 0)
accuracy_2 = accuracy_score(y_test, y_pred_2_binary)
print(f'Approach 2 Accuracy: {accuracy_2}')

# Predict for 2023
# Filter Data for 2022 to use as input for 2023 prediction
test_2022_df = df[df['year'] == 2022]
X_2022 = test_2022_df[features]
X_2022_scaled = pd.DataFrame(scaler.transform(X_2022), columns=X_2022.columns)

# Individual Regressions for 2022 Data
X_2022_transformed = individual_regressions(X_2022_scaled, y[test_2022_df.index])
X_2022_diff = calculate_differences(X_2022_scaled, playoff_averages)

# Predict using both models
yoffs_pred_won = model_multiple.predict(X_2022_transformed)
yoffs_pred_too = model_multiple_diff.predict(X_2022_diff)

# Create new DataFrame for 2023 Predictions
pred_2023_df = test_2022_df[['team']].copy()
pred_2023_df['year'] = 2023
pred_2023_df['yoffs_pred_won'] = yoffs_pred_won
pred_2023_df['yoffs_pred_too'] = yoffs_pred_too

# Update Database with Predictions for 2023
pred_2023_df.to_sql('Football-Predict-Stats', engine, if_exists='append', index=False)
