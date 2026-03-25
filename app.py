import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import statsmodels.api as sm
from deep_translator import GoogleTranslator



# ----------------------------
# PAGE SETTINGS
# ----------------------------
st.set_page_config(page_title="IKEA Global Analysis", layout="wide")
st.title("IKEA Global Product Catalog Analysis")
st.write("Python-based analysis of IKEA activity and expansion possibilities.")

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def cap_outliers_iqr(df, col):
    """Cap extreme values using IQR method."""
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    df[col] = df[col].clip(lower, upper)
    return df

def normalize_online_sellable(x):
    """Convert online_sellable to numeric binary."""
    if pd.isna(x):
        return np.nan
    x = str(x).strip().lower()
    if x in ["yes", "true", "1", "y"]:
        return 1
    if x in ["no", "false", "0", "n"]:
        return 0
    return np.nan

def create_market_features(df):
    """Aggregate features at country level for clustering and classification."""
    market_df = df.groupby("country").agg(
        avg_price=("price", "mean"),
        median_price=("price", "median"),
        avg_rating=("product_rating", "mean"),
        total_products=("product_id", "count"),
        avg_rating_count=("product_rating_count", "mean"),
        total_rating_count=("product_rating_count", "sum"),
        avg_discount=("discount", "mean"),
        online_sellable_rate=("online_sellable_bin", "mean")
    ).reset_index()

    market_df["expansion_score"] = (
        0.30 * market_df["avg_rating"].fillna(market_df["avg_rating"].median()) +
        0.20 * np.log1p(market_df["total_products"]) +
        0.20 * np.log1p(market_df["total_rating_count"]) +
        0.15 * market_df["online_sellable_rate"].fillna(0) +
        0.10 * market_df["avg_discount"].fillna(0) / max(market_df["avg_discount"].max(), 1) -
        0.05 * market_df["avg_price"].fillna(market_df["avg_price"].median()) / max(market_df["avg_price"].max(), 1)
    )

    threshold = market_df["expansion_score"].median()
    market_df["high_potential_market"] = (market_df["expansion_score"] >= threshold).astype(int)

    return market_df

# ----------------------------
# FILE UPLOAD
# ----------------------------
uploaded_file = st.file_uploader("Upload the IKEA CSV file", type=["csv"])

if uploaded_file is None:
    st.info("Please upload the IKEA dataset CSV file to begin.")
    st.stop()

df = pd.read_csv(uploaded_file)

# ----------------------------
# RAW DATA PREVIEW
# ----------------------------
st.header("1. Raw Dataset")
st.write("Dataset shape:", df.shape)
st.dataframe(df.head())

st.subheader("Column names")
st.write(df.columns.tolist())

# ----------------------------
# SELECT RELEVANT COLUMNS
# ----------------------------
relevant_cols = [
    "unique_id", "product_id", "product_name", "product_type",
    "main_category", "sub_category", "product_rating",
    "product_rating_count", "online_sellable", "price",
    "currency", "discount", "sale_tag", "country"
]

data = df[relevant_cols].copy()

# ----------------------------
# DATA CLEANING
# ----------------------------
st.header("2. Data Cleaning")

numeric_cols = ["product_rating", "product_rating_count", "price", "discount"]
for col in numeric_cols:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data["online_sellable_bin"] = data["online_sellable"].apply(normalize_online_sellable)

st.subheader("Missing values before treatment")
st.dataframe(data.isna().sum().to_frame("missing_count"))

data["product_rating"] = data.groupby("main_category")["product_rating"].transform(
    lambda x: x.fillna(x.median())
)
data["product_rating_count"] = data["product_rating_count"].fillna(0)
data["discount"] = data["discount"].fillna(0)
data["price"] = data["price"].fillna(data["price"].median())
data["online_sellable_bin"] = data["online_sellable_bin"].fillna(data["online_sellable_bin"].mode()[0] if not data["online_sellable_bin"].mode().empty else 0)

for col in ["product_name", "product_type", "main_category", "sub_category", "country", "currency", "sale_tag"]:
    data[col] = data[col].fillna("Unknown")

st.subheader("Missing values after treatment")
st.dataframe(data.isna().sum().to_frame("missing_count"))

# ----------------------------
# EXTREME VALUES
# ----------------------------
st.header("3. Extreme Value Treatment")

col1, col2 = st.columns(2)

with col1:
    st.write("Price statistics before outlier treatment")
    st.dataframe(data["price"].describe().to_frame())

data = cap_outliers_iqr(data, "price")

with col2:
    st.write("Price statistics after outlier treatment")
    st.dataframe(data["price"].describe().to_frame())

# ----------------------------
# GROUPING AND AGGREGATION
# ----------------------------
st.header("4. Statistical Processing, Grouping and Aggregation")

country_summary = data.groupby("country").agg(
    avg_price=("price", "mean"),
    median_price=("price", "median"),
    avg_rating=("product_rating", "mean"),
    total_products=("product_id", "count"),
    avg_rating_count=("product_rating_count", "mean"),
    total_discount=("discount", "sum")
).reset_index()

st.subheader("Country summary")
st.dataframe(country_summary)

category_summary = data.groupby("main_category").agg(
    avg_price=("price", "mean"),
    avg_rating=("product_rating", "mean"),
    total_products=("product_id", "count")
).reset_index()

st.subheader("Main category summary")
st.dataframe(category_summary)

# ----------------------------
# MERGE / JOIN
# ----------------------------
st.header("5. Merge / Join Example")

country_category = data.groupby(["country", "main_category"]).agg(
    avg_price=("price", "mean"),
    total_products=("product_id", "count")
).reset_index()

country_rating = data.groupby(["country", "main_category"]).agg(
    avg_rating=("product_rating", "mean")
).reset_index()

merged_data = pd.merge(country_category, country_rating, on=["country", "main_category"], how="left")

st.subheader("Merged country-category dataset")
st.dataframe(merged_data.head(20))

# ----------------------------
# MATPLOTLIB VISUALIZATIONS
# ----------------------------
st.header("6. Graphical Representation with Matplotlib")

fig1 = plt.figure(figsize=(10, 5))
top_countries = country_summary.sort_values("total_products", ascending=False).head(10)
plt.bar(top_countries["country"], top_countries["total_products"])
plt.xticks(rotation=45)
plt.title("Top 10 Countries by Number of Products")
plt.ylabel("Number of Products")
plt.tight_layout()
st.pyplot(fig1)

fig2 = plt.figure(figsize=(10, 5))
top_categories = category_summary.sort_values("avg_price", ascending=False).head(10)
plt.bar(top_categories["main_category"], top_categories["avg_price"])
plt.xticks(rotation=45)
plt.title("Top 10 Main Categories by Average Price")
plt.ylabel("Average Price")
plt.tight_layout()
st.pyplot(fig2)

fig3 = plt.figure(figsize=(8, 5))
plt.scatter(data["price"], data["product_rating"], alpha=0.4)
plt.xlabel("Price")
plt.ylabel("Product Rating")
plt.title("Price vs Product Rating")
plt.tight_layout()
st.pyplot(fig3)

# ----------------------------
# ENCODING + SCALING + CLUSTERING
# ----------------------------
st.header("7. Encoding, Scaling and Clustering")

market_df = create_market_features(data)

cluster_features = [
    "avg_price", "median_price", "avg_rating", "total_products",
    "avg_rating_count", "total_rating_count", "avg_discount", "online_sellable_rate"
]

X_cluster = market_df[cluster_features].fillna(0)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_cluster)

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
market_df["cluster"] = kmeans.fit_predict(X_scaled)

st.subheader("Country clusters")
st.dataframe(market_df[["country"] + cluster_features + ["cluster"]])

fig4 = plt.figure(figsize=(8, 5))
plt.scatter(market_df["avg_price"], market_df["total_products"], c=market_df["cluster"], cmap="viridis")
plt.xlabel("Average Price")
plt.ylabel("Total Products")
plt.title("Country Clusters Based on Market Characteristics")
plt.tight_layout()
st.pyplot(fig4)

# ----------------------------
# LOGISTIC REGRESSION
# ----------------------------
st.header("8. Logistic Regression - High Potential Market")

reg_df = data[[
    "price",
    "product_rating",
    "product_rating_count",
    "discount",
    "online_sellable_bin",
    "main_category"
]].copy()

reg_df = pd.get_dummies(reg_df, columns=["main_category"], drop_first=True)
reg_df = reg_df.apply(pd.to_numeric, errors="coerce")

reg_df = reg_df.dropna()

y_reg = reg_df["price"]
X_reg = reg_df.drop(columns=["price"])

X_reg = X_reg.astype(float)
y_reg = y_reg.astype(float)

X_reg = sm.add_constant(X_reg)

ols_model = sm.OLS(y_reg, X_reg).fit()

X = market_df[cluster_features].fillna(0)
y = market_df["high_potential_market"]

scaler_log = StandardScaler()
X_scaled_log = scaler_log.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled_log, y, test_size=0.3, random_state=42, stratify=y
)

log_model = LogisticRegression(max_iter=1000)
log_model.fit(X_train, y_train)
y_pred = log_model.predict(X_test)

st.write("Accuracy:", round(accuracy_score(y_test, y_pred), 4))
st.text("Classification report:")
st.text(classification_report(y_test, y_pred, zero_division=0))

coef_df = pd.DataFrame({
    "feature": cluster_features,
    "coefficient": log_model.coef_[0]
}).sort_values("coefficient", ascending=False)

st.subheader("Logistic regression coefficients")
st.dataframe(coef_df)

st.subheader("Market potential ranking")
st.dataframe(
    market_df[["country", "expansion_score", "high_potential_market"]]
    .sort_values("expansion_score", ascending=False)
)

# ----------------------------
# MULTIPLE REGRESSION WITH STATSMODELS
# ----------------------------
st.header("9. Multiple Regression with statsmodels")

reg_df = data[[
    "price",
    "product_rating",
    "product_rating_count",
    "discount",
    "online_sellable_bin",
    "main_category"
]].copy()

reg_df = pd.get_dummies(reg_df, columns=["main_category"], drop_first=True)

reg_df["price"] = pd.to_numeric(reg_df["price"], errors="coerce")
reg_df["product_rating"] = pd.to_numeric(reg_df["product_rating"], errors="coerce")
reg_df["product_rating_count"] = pd.to_numeric(reg_df["product_rating_count"], errors="coerce")

reg_df["discount"] = (
    reg_df["discount"]
    .astype(str)
    .str.replace("%", "", regex=False)
)
reg_df["discount"] = pd.to_numeric(reg_df["discount"], errors="coerce")

reg_df["online_sellable_bin"] = reg_df["online_sellable_bin"].astype(int)

reg_df = reg_df.dropna()

y_reg = reg_df["price"].astype(float)
X_reg = reg_df.drop(columns=["price"]).astype(float)

X_reg = sm.add_constant(X_reg)

ols_model = sm.OLS(y_reg, X_reg).fit()

st.text("OLS Regression Summary:")
st.text(ols_model.summary())

# ----------------------------
# GEOPANDAS MAP
# ----------------------------
st.header("10. Geographical Analysis with GeoPandas")

try:
    with st.spinner("Loading world map data..."):
        url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
        world = gpd.read_file(url)
    
    country_col = "country"
    
    country_name_fixes = {
        "USA": "United States of America",
        "UK": "United Kingdom",
        "Czech Republic": "Czechia",
        "South Korea": "South Korea",
        "Russia": "Russian Federation"
    }
    
    map_data = market_df.copy()
    map_data[country_col] = (
        map_data[country_col]
        .astype(str)
        .str.strip()
        .replace(country_name_fixes)
    )
    
    numeric_cols = map_data.select_dtypes(include=["number"]).columns.tolist()
    
    if numeric_cols:
        default_metric = "total_products" if "total_products" in numeric_cols else numeric_cols[0]
        
        selected_metric = st.selectbox(
            "Select variable to visualize on map:",
            numeric_cols,
            index=numeric_cols.index(default_metric)
        )
        
        world_merged = world.merge(
            map_data,
            left_on="NAME", 
            right_on=country_col,
            how="left"
        )
        
        fig = plt.figure(figsize=(14, 8))
        ax = plt.gca()
        
        world_merged.plot(
            column=selected_metric,
            ax=ax,
            legend=True,
            missing_kwds={"color": "lightgrey"},
            cmap="YlOrRd"
        )
        
        plt.title(f"{selected_metric} by country")
        plt.axis("off")
        st.pyplot(fig)
    else:
        st.warning("No numeric columns available for map visualization.")

except Exception as e:
    st.error(f"Could not generate GeoPandas map: {e}")

# ----------------------------
# FINAL INTERPRETATION
# ----------------------------
st.header("11. Business Insights")

st.markdown("""
### Key insights:
- Countries with a high number of products, strong average ratings, and high rating counts may indicate stronger market engagement.
- Categories with higher average prices may represent IKEA’s premium product segments.
- Clustering identifies groups of countries with similar commercial profiles.
- Logistic regression helps classify which countries may represent *high expansion potential*.
- Multiple regression explains how rating, rating count, discounts, online availability, and category affect price.
- GeoPandas offers a spatial view of IKEA’s international product distribution.
""")