#pip install pandas streamlit matplotlib seaborn google-genai python-dotenv

import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from google import genai

# 1. Load environment variables
load_dotenv()

st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="📊",
    layout="wide"
)

st.title("📊 AI Data Analyst")
st.write("Analyze your data and ask questions using Gemini AI.")

# 2. Connect to Gemini
api_key = os.getenv("GEMINI_API_KEY")

# 3. Upload CSV file
uploaded_file = st.file_uploader(
    "Upload your sales CSV file",
    type=["csv"]
)

# Sample data for first-time testing
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read the CSV file: {e}")
        st.stop()
else:
    df = pd.DataFrame({
        "Product": [
            "Laptop", "Mouse", "Phone", "Keyboard",
            "Laptop", "Phone", "Mouse"
        ],
        "Quantity": [2, 10, 3, 5, 1, 4, 15],
        "Price": [50000, 500, 20000, 1500,
                  50000, 20000, 500],
        "Region": [
            "West", "West", "South", "North",
            "South", "West", "North"
        ]
    })

# 4. Basic data cleaning
df.columns = df.columns.astype(str).str.strip()
df = df.dropna(how="all")

if df.empty:
    st.warning("The uploaded CSV contains no data.")
    st.stop()

# Calculate revenue when the required columns exist
if {"Quantity", "Price"}.issubset(df.columns):
    df["Revenue"] = (
        pd.to_numeric(df["Quantity"], errors="coerce")
        * pd.to_numeric(df["Price"], errors="coerce")
    )

st.subheader("Dataset Preview")
st.dataframe(df.head(20), use_container_width=True)
st.write("Available columns:", df.columns.tolist())


# Download Analysis Report
st.subheader("📥 Download Your Report")

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Analysis Report",
    data=csv_data,
    file_name="sales_report.csv",
    mime="text/csv"
)


# 5. Show dashboard metrics
numeric_cols = df.select_dtypes(include="number").columns.tolist()

col1, col2, col3 = st.columns(3)

col1.metric("Total Rows", len(df))
col2.metric("Total Columns", len(df.columns))
col3.metric("Missing Values", int(df.isna().sum().sum()))

# 6. Show a chart
if numeric_cols:
    st.subheader("Explore Your Data")

    category_cols = df.select_dtypes(
        include=["object", "category", "string"]
    ).columns.tolist()

    category = st.selectbox(
        "Choose a category",
        ["None"] + category_cols
    )

    metric = st.selectbox(
        "Choose a numeric column",
        numeric_cols
    )

    if category != "None":
        chart_data = df.groupby(
            category, dropna=False
        )[metric].sum().sort_values(ascending=False)

        st.bar_chart(chart_data)
    else:
        st.line_chart(df[metric].reset_index(drop=True))




# 7. Natural-language charts and date analysis

def get_gemini_chart_insight(question, chart_summary):
    if not api_key:
        return "Please configure your Gemini API key in the .env file."

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an AI data analyst.

    User question: {question}
    Chart data:
    {chart_summary}

    Explain in simple English:
    1. The main finding.
    2. The highest and lowest values.
    3. One useful business recommendation.

    Use only the data provided. Do not invent facts.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",

        contents=prompt
    )

    return response.text


st.subheader("📈 Ask for a Chart")

chart_question = st.text_input(
    "Describe the chart you want",
    placeholder="Example: Show monthly revenue"
)

if st.button("Generate Chart"):

    if not chart_question.strip():
        st.warning("Please describe the chart.")

    else:
        q = chart_question.lower()

        # Find numeric columns
        numeric_cols = df.select_dtypes(
            include="number"
        ).columns.tolist()

        # Find date and category columns
        date_col = next(
            (
                c for c in df.columns
                if "date" in str(c).lower()
            ),
            None
        )

        category_cols = df.select_dtypes(
            include=["object", "category", "string"]
        ).columns.tolist()

        # Choose the numeric metric
        metric = next(
            (
                c for c in numeric_cols
                if str(c).lower() in q
            ),
            None
        )

        if metric is None:
            metric = next(
                (
                    c for c in numeric_cols
                    if str(c).lower() == "revenue"
                ),
                numeric_cols[0] if numeric_cols else None
            )

        # Check whether the user requested a time trend
        wants_monthly = any(
            word in q
            for word in [
                "monthly", "month", "over time",
                "trend", "date", "daily"
            ]
        )

        if metric is None:
            st.error(
                "No numeric column is available for charting."
            )

        elif wants_monthly and date_col is not None:

            # Convert dates and metric safely
            temp = df[[date_col, metric]].copy()
            temp[date_col] = pd.to_datetime(
                temp[date_col], errors="coerce"
            )
            temp[metric] = pd.to_numeric(
                temp[metric], errors="coerce"
            )
            temp = temp.dropna(
                subset=[date_col, metric]
            )

            if temp.empty:
                st.warning(
                    "No valid dates or numeric values were found."
                )
            else:
                # Group by month
                temp["Month"] = (
                    temp[date_col]
                    .dt.to_period("M")
                    .astype(str)
                )

                monthly = (
                    temp.groupby("Month")[metric]
                    .sum()
                    .sort_index()
                )

                st.markdown(f"### Monthly {metric}")
                st.line_chart(monthly)

                best_month = monthly.idxmax()
                st.write(
                    f"Highest month: {best_month}, "
                    f"with {monthly.max():,.2f} {metric}."
                )

        else:
            # Identify a category such as Product or Region
            category = next(
                (
                    c for c in category_cols
                    if str(c).lower() in q
                ),
                None
            )

            if category is None:
                category = next(
                    (
                        c for c in category_cols
                        if str(c).lower() in [
                            "product", "region", "category"
                        ]
                    ),
                    None
                )

            if category is None:
                st.warning(
                    "Please mention a category such as "
                    "Product or Region, or ask for a monthly trend."
                )

            else:
                temp = df[[category, metric]].copy()
                temp[metric] = pd.to_numeric(
                    temp[metric], errors="coerce"
                )
                temp = temp.dropna(subset=[metric])

                grouped = (
                    temp.groupby(category)[metric]
                    .sum()
                    .sort_values(ascending=False)
                )

                st.markdown(
                    f"### {metric} by {category}"
                )
                st.bar_chart(grouped)

                if not grouped.empty:
                    st.write(
                        f"Top {category}: {grouped.index[0]}, "
                        f"with {grouped.iloc[0]:,.2f} {metric}."
                    )
                with st.spinner("Gemini is analyzing your chart..."):
                    try:
                        summary = grouped.to_string()
                        insight = get_gemini_chart_insight(
                            chart_question, summary
                        )
                        st.subheader("🤖 Gemini's Business Insights")
                        st.write(insight)
                    except Exception as e:
                        st.error(f"Could not generate AI insights: {e}")


# Ask Your Data Analyst
st.subheader("🤖 Ask Your Data Analyst")

question = st.text_input(
    "Ask a question about your data",
    placeholder="What is the total revenue?"
)

if st.button("Get Answer"):
    q = question.lower().strip()

    if not q:
        st.warning("Please enter a question.")

    #elif "revenue" in q:
    #elif "revenue" in q and "highest" not in q and "most" not in q:  
    elif (
    "revenue" in q
    and "highest" not in q
    and "most" not in q
    and "lowest" not in q
    and "least" not in q
):
        if "Revenue" not in df.columns:
            if {"Quantity", "Price"}.issubset(df.columns):
                df["Revenue"] = (
                    pd.to_numeric(df["Quantity"], errors="coerce")
                    * pd.to_numeric(df["Price"], errors="coerce")
                )
            else:
                st.error("Please check your Quantity and Price columns.")

        if "Revenue" in df.columns:
            total = pd.to_numeric(
                df["Revenue"], errors="coerce"
            ).sum()
            st.success(f"Total revenue is {total:,.2f}")
    
    elif "lowest revenue" in q or "least revenue" in q:
        if "Product" in df.columns and "Revenue" in df.columns:
            product_revenue = df.groupby("Product")["Revenue"].sum()

            if not product_revenue.empty:
                lowest_product = product_revenue.idxmin()
                lowest_revenue = product_revenue.min()

                st.success(
                    f"Product with lowest revenue: {lowest_product}"
                )
                st.write(f"Revenue: ₹{lowest_revenue:,.2f}")
            else:
                st.warning("No product revenue data found.")
        else:
            st.warning("Product and Revenue columns are required.")

    elif "rows" in q:
        st.success(f"Your dataset has {len(df)} rows.")

    elif "columns" in q:
        st.success(f"Your dataset has {len(df.columns)} columns.")
    
    elif "average price" in q or "average of price" in q:
        if "Price" in df.columns:
            average_price = pd.to_numeric(
                df["Price"], errors="coerce"
            ).mean()

            if pd.notna(average_price):
                st.success(f"Average price is ₹{average_price:,.2f}")
            else:
                st.warning("No valid price values found.")
        else:
            st.warning("Your dataset does not have a Price column.")
       
    elif ("highest revenue" in q or "most revenue" in q) and "region" not in q:
    
        if "Product" in df.columns and "Revenue" in df.columns:
            product_revenue = df.groupby("Product")["Revenue"].sum()

            if not product_revenue.empty:
                best_product = product_revenue.idxmax()
                best_revenue = product_revenue.max()

                st.success(
                    f"Product with highest revenue: {best_product}"
                )
                st.write(f"Revenue: {best_revenue:,.2f}")
            else:
                st.warning("No product revenue data found.")
      
    elif "different products" in q or "unique products" in q:
        if "Product" in df.columns:
            product_count = df["Product"].nunique()
            st.success(f"Number of different products: {product_count}")
        else:
            st.warning("Your dataset does not have a Product column.")
  
    elif "region" in q and ("highest" in q or "most" in q):
        if "Region" in df.columns and "Revenue" in df.columns:
            region_revenue = df.groupby("Region")["Revenue"].sum()

            if not region_revenue.empty:
                best_region = region_revenue.idxmax()
                best_revenue = region_revenue.max()

                st.success(
                    f"Region with highest revenue: {best_region}"
                )
                st.write(f"Revenue: ₹{best_revenue:,.2f}")
            else:
                st.warning("No region revenue data found.")
        else:
            st.warning(
                "Your dataset needs Product and Revenue columns."
            )
