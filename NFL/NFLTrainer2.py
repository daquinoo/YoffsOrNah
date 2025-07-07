import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine

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
X = train_df[features]
y = train_df['yoffs']

# Standardize Features
scaler = StandardScaler()
X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)

# Split Data
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

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

# Logistic Regression Model with increased max_iter
model_logistic = LogisticRegression(max_iter=10000)
model_logistic.fit(X_diff, y_train)

# Evaluate Model
X_test_diff = calculate_differences(X_test, playoff_averages)
y_pred_proba = model_logistic.predict_proba(X_test_diff)[:, 1]

# Adjust probabilities
def adjust_probabilities(predictions):
    adjusted = np.where(predictions > 1, 0.001, predictions)  # Adjust predictions over 1 to 0.001
    adjusted = np.where(adjusted < 0, 0.001, adjusted)  # Adjust predictions below 0 to 0.001
    return np.round(adjusted, 3)  # Round to 3 decimal places

y_pred_proba_adjusted = adjust_probabilities(y_pred_proba)
y_pred_binary = np.where(y_pred_proba_adjusted > 0.5, 1, 0)
accuracy = (y_pred_binary == y_test).mean()
print(f'Logistic Regression Accuracy: {accuracy}')

# Predict for 2023
# Filter Data for 2022 to use as input for 2023 prediction
test_2022_df = df[df['year'] == 2022]
X_2022 = test_2022_df[features]
X_2022_scaled = pd.DataFrame(scaler.transform(X_2022), columns=X_2022.columns)

# Calculate Differences for 2022 Data
X_2022_diff = calculate_differences(X_2022_scaled, playoff_averages)

# Predict using logistic regression model
yoffs_pred_proba_2023 = model_logistic.predict_proba(X_2022_diff)[:, 1]

# Adjust probabilities for 2023
yoffs_pred_proba_2023_adjusted = adjust_probabilities(yoffs_pred_proba_2023)

# Create new DataFrame for 2023 Predictions
pred_2023_df = test_2022_df[['team']].copy()
pred_2023_df['year'] = 2023
pred_2023_df['yoffs_pred_too'] = yoffs_pred_proba_2023_adjusted

# Update Database with Predictions for 2023
pred_2023_df.to_sql('Football-Predict-Stats', engine, if_exists='append', index=False)
