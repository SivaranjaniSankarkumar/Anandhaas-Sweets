from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json
import boto3
import io
import os
import requests
import tempfile
import base64
from matplotlib.backends.backend_pdf import PdfPages
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

BEDROCK_MODEL_ID = "amazon.nova-pro-v1:0"
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"

anandhaas_data = None
last_pdf_data = {"data": None, "title": "", "insights": "", "filename": ""}

# Slack configuration - exact copy from restaurant dashboard
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID") or "C09UUJZ56QJ"

print(f"DEBUG: SLACK_BOT_TOKEN loaded: {SLACK_BOT_TOKEN[:20] if SLACK_BOT_TOKEN else 'None'}...")
print(f"DEBUG: SLACK_CHANNEL_ID loaded: {SLACK_CHANNEL_ID}")

try:
    test_client = WebClient(token=SLACK_BOT_TOKEN)
    test_response = test_client.auth_test()
    print(f"DEBUG: Slack auth test successful: {test_response.get('ok')}")
except Exception as e:
    print(f"DEBUG: Slack auth test failed: {e}")



def load_anandhaas_data(file_path: str = "anandhaas_sweets.csv") -> pd.DataFrame | None:
    try:
        df = pd.read_csv(file_path, quotechar='"')
        print(f"Available columns: {list(df.columns)}")
        print(f"Total rows loaded: {len(df)}")
        
        # Check for NaN values in key columns before processing
        print(f"NaN values in Net Value: {df['Net Value'].isna().sum()}")
        print(f"NaN values in Date: {df['Date'].isna().sum()}")
        
        # Use actual columns from CSV - Net Value for revenue, not TotalBillAmt
        required_cols = ["Branch Name", "Date", "ItemName", "Net Value"]
        optional_cols = ["Quantity"]
        column_mapping = {
            "ItemName": "Item Name",
            "Net Value": "Total Amount"
        }
        df = df.rename(columns=column_mapping)
        required_cols = ["Branch Name", "Date", "Item Name", "Total Amount"]
        
        # Add Quantity if available
        available_cols = required_cols.copy()
        if "Quantity" in df.columns:
            available_cols.append("Quantity")
            df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(1)
        
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            print(f"Missing required columns: {missing_cols}")
            return None
            
        df = df[available_cols].copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        
        # Clean the Total Amount column - remove commas and convert to numeric
        df["Total Amount"] = df["Total Amount"].astype(str).str.replace(',', '').str.replace('"', '')
        df["Total Amount"] = pd.to_numeric(df["Total Amount"], errors="coerce")
        
        print(f"After processing - NaN values in Total Amount: {df['Total Amount'].isna().sum()}")
        print(f"After processing - NaN values in Date: {df['Date'].isna().sum()}")
        print(f"Sample Total Amount values: {df['Total Amount'].head(10).tolist()}")
        print(f"Final dataset: {len(df)} records with {df['Total Amount'].notna().sum()} valid amounts.")
        return df
    except Exception as e:
        print(f"Cannot load {file_path}: {e}")
        return None

def analyze_anandhaas_structure(data: pd.DataFrame) -> dict:
    if data is None or data.empty:
        return {}
    clean_branches = [b for b in data["Branch Name"].dropna().unique()]
    clean_items = [i for i in data["Item Name"].dropna().unique()]
    analysis = {
        "total_records": len(data),
        "branches": clean_branches,
        "items": clean_items[:20],
        "date_range": {
            "start": data["Date"].min(),
            "end": data["Date"].max(),
        },
        "revenue_stats": {
            "total": float(data["Total Amount"].sum()),
            "avg": float(data["Total Amount"].mean()),
            "max": float(data["Total Amount"].max()),
            "min": float(data["Total Amount"].min()),
        },
    }
    return analysis

def get_ai_plan(query: str, data_analysis: dict) -> dict:
    branches = data_analysis.get("branches", [])
    items = data_analysis.get("items", [])

    try:
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

        prompt = f"""
Analyze this business query about sweets sales and create a visualization plan.

Query: "{query}"

Available Data:
- Branches: {branches}
- Items: {items}

Return ONLY valid JSON in this exact format:
{{
  "chart_type": "bar|pie|line|dual_bar",
  "x_axis": "Branch Name|Item Name|Date|Month|Item-Branch",
  "y_axis": "Total Amount|Quantity|count|dual",
  "aggregation": "sum|mean|count",
  "item_filters": null or [string, ...],
  "item_category_filter": null or string (for filtering all items containing keyword like "murukku"),
  "branch_filters": null or [string, ...],
  "month_filter": null or month_number or [month_numbers],
  "date_filter": null or "YYYY-MM-DD" or ["YYYY-MM-DD", "YYYY-MM-DD"],
  "year_filter": null or year_number or [year_numbers],
  "title": "chart title",
  "dual_metrics": false or true
}}

CRITICAL RULES:
- CRITICAL: For SPECIFIC item names (like "Butter murukku", "ABC Mysore Pak", "Usilampatti Murukku") → use item_filters: ["exact_name"] NOT item_category_filter
- CRITICAL: For GENERIC categories (like "murukku items", "all murukku", "murukku varieties") → use item_category_filter: "murukku"
- CRITICAL: "Butter murukku" is a SPECIFIC item → use item_filters: ["Butter murukku"]
- CRITICAL: "murukku items" is a CATEGORY → use item_category_filter: "murukku"
- Use EXACT item names as mentioned by user - DO NOT translate, interpret, or change them
- Extract filters EXACTLY as user mentions them
- CRITICAL: If user says "by branch" or "each branch" → DO NOT add branch_filters, set x_axis: "Branch Name" to show ALL branches
- CRITICAL: If user says "by item" or "each item" → DO NOT add item_filters, set x_axis: "Item Name" to show ALL items
- Only add branch_filters when user specifies a specific branch like "at CH-MW branch" or "in SPM branch"
- CRITICAL: When user says "[ANY_ITEM] items" (plural), "all [ANY_ITEM]", "[ANY_ITEM] varieties", "[ANY_ITEM] items individually" → use item_category_filter: "[ANY_ITEM]" AND set x_axis: "Item Name"
- CRITICAL: When user says specific item name (singular) like "Butter murukku", "ABC Mysore Pak" → use item_filters: ["exact_name"]
- CRITICAL: WHENEVER item_category_filter is used, ALWAYS set x_axis: "Item Name" to show individual items
- CRITICAL: For "[ITEM] items individually w.r.t all branches" → use item_category_filter: "[ITEM]", x_axis: "Item Name", NO branch_filters
- CRITICAL: For "[ITEM] items w.r.t branches" or "[ITEM] items across branches" → use item_category_filter: "[ITEM]", x_axis: "Item Name", NO branch_filters
- IMPORTANT: Calculate revenue using ALL records in the data - DO NOT remove duplicates, DO NOT be intelligent about bill numbers, USE EVERY ROW AS-IS
- Sum ALL Total Amount values that match the filters - include every single record
- For months: january=1, february=2, march=3, april=4, may=5, june=6, july=7, august=8, september=9, october=10, november=11, december=12
- For dates: extract specific dates ("2024-01-15") or date ranges (["2024-01-01", "2024-01-31"])
- For years: extract year numbers (2023, 2024, etc.)
- If user asks "how many", "quantity", "count" of items, use y_axis: "Quantity" and aggregation: "sum"
- If user asks "how many" records or transactions, use y_axis: "count" and aggregation: "count"
- CRITICAL: For quantity queries like "quantity of [item]", "how many [item] sold", use y_axis: "Quantity"
- For "distribution", "breakdown", "share", "split", "proportion", "across all branches", "across branches" → use chart_type: "pie"
- CRITICAL: For "Revenue Distribution of [ITEM] Items Across All Branches" → use chart_type: "pie", x_axis: "Item Name", item_category_filter: "[ITEM]"
- CRITICAL: For "[ITEM] distribution across branches" → use chart_type: "pie", x_axis: "Item Name", item_category_filter: "[ITEM]"
- CRITICAL: For "revenue distribution of items w.r.t month" or similar → use x_axis: "Item Name", chart_type: "pie", and apply month_filter
- CRITICAL: For queries asking "highest revenue X in which branch" or "which branch has highest X" → use x_axis: "Branch Name", apply item_filters for X, and sort by revenue descending
- CRITICAL: For queries asking "which X item gives highest revenue in Y branch" → use x_axis: "Item Name", apply branch_filters for Y, item_filters for X category
- CRITICAL: For "revenue of all murukku items of [branch]" or "murukku items revenue in [branch]" → use x_axis: "Item Name", chart_type: "bar", item_category_filter: "murukku", branch_filters: [branch]
- CRITICAL: For "distribution of murukku items in [branch]" → use x_axis: "Item Name", chart_type: "pie", item_category_filter: "murukku", branch_filters: [branch]
- CRITICAL: For "show murukku items in SPM branch" → use x_axis: "Item Name", filter murukku items in specific branch
- For "comparison", "compare", "vs" → use bar chart
- CRITICAL: When user mentions "by months", "monthly", "month wise", "each month", "compare months" → use x_axis: "Month" NOT "Date"
- For time/trend with specific dates, use line chart with Date
- For monthly analysis, ALWAYS use x_axis: "Month" and chart_type: "bar"
- For daily analysis over short periods, use x_axis: "Date" and chart_type: "line"
- For yearly comparisons, extract year_filter and use appropriate grouping
- If user asks for BOTH count AND revenue, set dual_metrics: true, chart_type: "dual_bar", y_axis: "dual"
- CRITICAL: Date filtering rules:
  * "today", "yesterday" → extract current/previous date
  * "last week", "this week" → extract date range
  * "January 2024", "Jan 2024" → extract month and year filters
  * "2024" → extract year filter
  * "February 12th", "Feb 12", "12th February" → extract as "02-12" (MM-DD format)
  * "February 12th, 2024" → extract as "2024-02-12"
  * "from Jan 1 to Jan 31", "between 2024-01-01 and 2024-01-31" → extract date range
  * "last 7 days", "past month" → calculate and extract date range
- Match user terms intelligently to available data
- IMPORTANT: When no year is specified in dates, assume current year (2025)
"""
        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"temperature": 0.1},
        })
        response = bedrock.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
        raw = response["body"].read()
        result = json.loads(raw)
        ai_text = result["output"]["message"]["content"][0]["text"].strip()

        if "{" in ai_text and "}" in ai_text:
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            json_str = ai_text[start:end]
            plan = json.loads(json_str)
        else:
            raise ValueError("Model did not return JSON")

        plan.setdefault("chart_type", "bar")
        plan.setdefault("x_axis", "Branch Name")
        plan.setdefault("y_axis", "Total Amount")
        plan.setdefault("aggregation", "sum")
        plan.setdefault("title", "Anandhaas Revenue Analysis")
        plan.setdefault("dual_metrics", False)

        # CRITICAL FIX: Force exact item filtering when item_filters is used
        if plan.get("item_filters"):
            plan["x_axis"] = "Item Name"  # Show the specific item
            
        # CRITICAL FIX: Force pie chart for distribution queries
        if any(word in query.lower() for word in ["distribution", "breakdown", "share", "split", "proportion", "across all branches", "across branches"]):
            plan["chart_type"] = "pie"

        filters = []

        if plan.get("item_filters"):
            if len(plan["item_filters"]) == 1:
                filters.append(("Item Name", plan["item_filters"][0]))
            else:
                filters.append(("Item_in", plan["item_filters"]))

        if plan.get("item_category_filter"):
            filters.append(("Item_category", plan["item_category_filter"]))

        if plan.get("branch_filters"):
            if len(plan["branch_filters"]) == 1:
                filters.append(("Branch Name", plan["branch_filters"][0]))
            else:
                filters.append(("Branch_in", plan["branch_filters"]))

        if plan.get("month_filter"):
            month_val = plan["month_filter"]
            if isinstance(month_val, list):
                filters.append(("date_month_in", month_val))
            else:
                filters.append(("date_month", month_val))

        if plan.get("date_filter"):
            date_val = plan["date_filter"]
            if isinstance(date_val, list) and len(date_val) == 2:
                filters.append(("date_range", date_val))
            else:
                filters.append(("date_specific", date_val))

        if plan.get("year_filter"):
            year_val = plan["year_filter"]
            if isinstance(year_val, list):
                filters.append(("date_year_in", year_val))
            else:
                filters.append(("date_year", year_val))

        plan["filters"] = filters
        print(f"\n=== AI PLAN DEBUG ===")
        print(f"Original Query: {query}")
        print(f"AI Plan: {plan}")
        print(f"Filters to apply: {filters}")
        print(f"===================\n")
        return plan

    except Exception as e:
        print(f"AI model failed to process query: {str(e)}")
        raise

def create_anandhaas_visualization(data: pd.DataFrame, ai_plan: dict):
    dual_metrics = ai_plan.get("dual_metrics", False) or ai_plan.get("y_axis") == "dual"
    
    if dual_metrics:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 10))
    else:
        fig, ax = plt.subplots(figsize=(20, 12))
    
    filtered_data = data.copy()
    filters = ai_plan.get("filters", [])

    for filter_type, filter_value in filters:
        if filter_type == "date_month":
            filtered_data = filtered_data[
                filtered_data["Date"].dt.month == int(filter_value)
            ]
        elif filter_type == "date_month_in":
            month_list = [int(m) for m in filter_value]
            filtered_data = filtered_data[
                filtered_data["Date"].dt.month.isin(month_list)
            ]
        elif filter_type == "date_specific":
            try:
                # Handle various date formats and add current year if missing
                if len(filter_value.split('-')) == 2:  # MM-DD format
                    current_year = pd.Timestamp.now().year
                    filter_value = f"{current_year}-{filter_value}"
                target_date = pd.to_datetime(filter_value).date()
                filtered_data = filtered_data[
                    filtered_data["Date"].dt.date == target_date
                ]
                print(f"DEBUG: Date filter '{target_date}' resulted in {len(filtered_data)} records")
            except Exception as e:
                print(f"DEBUG: Date parsing error for '{filter_value}': {e}")
                continue
        elif filter_type == "date_range":
            start_date = pd.to_datetime(filter_value[0])
            end_date = pd.to_datetime(filter_value[1])
            filtered_data = filtered_data[
                (filtered_data["Date"] >= start_date) & 
                (filtered_data["Date"] <= end_date)
            ]
        elif filter_type == "date_year":
            filtered_data = filtered_data[
                filtered_data["Date"].dt.year == int(filter_value)
            ]
        elif filter_type == "date_year_in":
            year_list = [int(y) for y in filter_value]
            filtered_data = filtered_data[
                filtered_data["Date"].dt.year.isin(year_list)
            ]
        elif filter_type in ["Item Name", "Branch Name"]:
            clean_data = filtered_data.dropna(subset=[filter_type])
            print(f"Filtering {filter_type} for: '{filter_value}'")
            print(f"Records before filtering: {len(clean_data)}")
            
            # CRITICAL FIX: Try exact match first (case-insensitive)
            exact_match = clean_data[clean_data[filter_type].astype(str).str.lower() == str(filter_value).lower()]
            
            if not exact_match.empty:
                filtered_data = exact_match
                print(f"Exact match found: {len(exact_match)} records")
            else:
                # If no exact match, try partial match with ALL words present
                search_words = str(filter_value).lower().split()
                mask = clean_data[filter_type].astype(str).str.lower()
                
                # Start with all records
                temp_data = clean_data.copy()
                
                # Each word must be present in the item name (AND logic)
                for word in search_words:
                    word_mask = temp_data[filter_type].astype(str).str.lower().str.contains(word, case=False, na=False)
                    temp_data = temp_data[word_mask]
                
                if not temp_data.empty:
                    filtered_data = temp_data
                    print(f"Partial match (ALL words) found: {len(temp_data)} records")
                    print(f"Matched items: {temp_data[filter_type].unique()[:5]}")
                else:
                    # No matches found - return empty to avoid wrong results
                    filtered_data = pd.DataFrame(columns=filtered_data.columns)
                    print(f"No matches found for '{filter_value}'")
            
            print(f"Records after filtering: {len(filtered_data)}")
            if not filtered_data.empty:
                print(f"Total Amount sum: {filtered_data['Total Amount'].sum()}")
                print(f"Sample filtered records:")
                print(filtered_data[['Branch Name', 'Item Name', 'Total Amount']].head(3))
                print(f"Unique items found: {filtered_data['Item Name'].unique()}")
        elif filter_type == "Item_category":
            # Filter for all items containing the category keyword
            clean_data = filtered_data.dropna(subset=["Item Name"])
            category_mask = clean_data["Item Name"].astype(str).str.contains(str(filter_value), case=False, na=False)
            filtered_data = clean_data[category_mask]
            print(f"Category filter '{filter_value}' resulted in {len(filtered_data)} records")
            if not filtered_data.empty:
                print(f"Items found: {filtered_data['Item Name'].unique()[:10]}")
        elif filter_type in ["Item_in", "Branch_in"]:
            col_map = {
                "Item_in": "Item Name",
                "Branch_in": "Branch Name",
            }
            col = col_map[filter_type]
            values = [str(v) for v in filter_value]
            clean_data = filtered_data.dropna(subset=[col])
            tmp = clean_data[clean_data[col].astype(str).isin(values)]
            filtered_data = tmp

    if filtered_data.empty:
        raise ValueError("No data found after applying filters.")

    x_col = ai_plan.get("x_axis", "Branch Name")
    
    # Handle month-wise grouping
    if x_col == "Month":
        filtered_data = filtered_data.copy()
        filtered_data["Month"] = filtered_data["Date"].dt.strftime("%B %Y")
        filtered_data["MonthSort"] = filtered_data["Date"].dt.to_period("M")
    elif x_col == "Item-Branch":
        filtered_data = filtered_data.copy()
        filtered_data["Item-Branch"] = filtered_data["Item Name"].astype(str) + " @ " + filtered_data["Branch Name"].astype(str)
    
    if dual_metrics:
        if x_col == "Month":
            revenue_data = filtered_data.groupby(["MonthSort", "Month"])["Total Amount"].sum().reset_index()
            revenue_data = revenue_data.set_index("Month")["Total Amount"].sort_index()
            if "Quantity" in filtered_data.columns:
                count_data = filtered_data.groupby(["MonthSort", "Month"])["Quantity"].sum().reset_index()
                count_data = count_data.set_index("Month")["Quantity"].sort_index()
            else:
                count_data = filtered_data.groupby(["MonthSort", "Month"]).size().reset_index(name="count")
                count_data = count_data.set_index("Month")["count"].sort_index()
        else:
            revenue_data = filtered_data.groupby(x_col)["Total Amount"].sum().sort_values(ascending=False)
            if "Quantity" in filtered_data.columns:
                count_data = filtered_data.groupby(x_col)["Quantity"].sum().sort_values(ascending=False)
            else:
                count_data = filtered_data[x_col].value_counts().sort_values(ascending=False)
        
        bars1 = ax1.bar(range(len(revenue_data)), revenue_data.values, color='#1e40af', alpha=0.95, edgecolor='white', linewidth=1.5)
        ax1.set_xticks(range(len(revenue_data)))
        ax1.set_xticklabels(revenue_data.index, rotation=0 if len(revenue_data) <= 5 else 45, ha='center' if len(revenue_data) <= 5 else 'right', fontsize=11)
        ax1.set_xlabel(x_col, fontsize=12, fontweight="bold")
        ax1.set_ylabel("Revenue in Lakhs", fontsize=12, fontweight="bold")
        ax1.set_title("Revenue Analysis", fontsize=14, fontweight="bold")
        
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/100000:.0f}'))
        
        for i, bar in enumerate(bars1):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01, f'₹{height:,.0f}',
                    ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        bars2 = ax2.bar(range(len(count_data)), count_data.values, color='#059669', alpha=0.95, edgecolor='white', linewidth=1.5)
        ax2.set_xticks(range(len(count_data)))
        ax2.set_xticklabels(count_data.index, rotation=0 if len(count_data) <= 5 else 45, ha='center' if len(count_data) <= 5 else 'right', fontsize=11)
        ax2.set_xlabel(x_col, fontsize=12, fontweight="bold")
        ax2.set_ylabel("Count", fontsize=12, fontweight="bold")
        ax2.set_title("Transaction Count", fontsize=14, fontweight="bold")
        
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}k' if x >= 1000 else f'{x:.0f}'))
        
        for i, bar in enumerate(bars2):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01, f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold', fontsize=9)
        
        all_branches = set(revenue_data.index) | set(count_data.index)
        chart_data = []
        for branch in all_branches:
            chart_data.append({
                "name": str(branch),
                "revenue": float(revenue_data.get(branch, 0)),
                "count": int(count_data.get(branch, 0))
            })
        
        chart_data.sort(key=lambda x: x["revenue"], reverse=True)
        
    else:
        y_col = ai_plan.get("y_axis", "Total Amount")
        agg_method = ai_plan.get("aggregation", "sum")

        if y_col == "count":
            if x_col == "Month":
                grouped_data = filtered_data.groupby(["MonthSort", "Month"]).size().reset_index(name="count")
                grouped_data = grouped_data.set_index("Month")["count"].sort_index()
            else:
                grouped_data = filtered_data[x_col].value_counts().sort_values(ascending=False)
        elif y_col == "Quantity" and "Quantity" in filtered_data.columns:
            if x_col == "Month":
                grouped_data = filtered_data.groupby(["MonthSort", "Month"])["Quantity"].agg(agg_method).reset_index()
                grouped_data = grouped_data.set_index("Month")["Quantity"].sort_index()
            else:
                grouped_data = filtered_data.groupby(x_col)["Quantity"].agg(agg_method).sort_values(ascending=False)
        else:
            if x_col == "Month":
                grouped_data = filtered_data.groupby(["MonthSort", "Month"])[y_col].agg(agg_method).reset_index()
                grouped_data = grouped_data.set_index("Month")[y_col].sort_index()
            else:
                grouped_data = filtered_data.groupby(x_col)[y_col].agg(agg_method).sort_values(ascending=False)

        chart_type = ai_plan.get("chart_type", "bar")

        if chart_type == "pie":
            grouped_data = grouped_data.sort_values(ascending=False)
            professional_colors = ['#1e40af', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#65a30d', '#ea580c']
            colors = [professional_colors[i % len(professional_colors)] for i in range(len(grouped_data))]
            
            wedges, texts, autotexts = ax.pie(
                grouped_data.values,
                labels=None,
                autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
                colors=colors,
                startangle=90,
                pctdistance=0.85,
                explode=[0.05 if i == 0 else 0 for i in range(len(grouped_data))]
            )
            
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_fontweight("bold")
                autotext.set_fontsize(10)
            
            ax.legend(wedges, [f'{name}: ₹{value:,.0f} ({value/grouped_data.sum()*100:.1f}%)' if y_col == 'Total Amount' else f'{name}: {value:.0f} ({value/grouped_data.sum()*100:.1f}%)' 
                              for name, value in grouped_data.items()], 
                     title=x_col, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10)
        elif chart_type == "line":
            ax.plot(
                range(len(grouped_data)),
                grouped_data.values,
                marker="o",
                linewidth=3,
                markersize=8,
            )
            ax.set_xticks(range(len(grouped_data)))
            ax.set_xticklabels(grouped_data.index, rotation=0 if len(grouped_data) <= 5 else 45, ha='center' if len(grouped_data) <= 5 else 'right', fontsize=11)
            ax.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax.set_ylabel(f"{y_col} {'(Lakhs)' if y_col == 'Total Amount' else ''}", fontsize=12, fontweight="bold")
            if y_col == "Total Amount":
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/100000:.0f}'))
            ax.grid(True, alpha=0.3)
        else:
            professional_colors = ['#1e40af', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#65a30d', '#ea580c']
            bar_colors = [professional_colors[i % len(professional_colors)] for i in range(len(grouped_data))]
            bars = ax.bar(
                range(len(grouped_data)),
                grouped_data.values,
                color=bar_colors,
                alpha=0.95,
                edgecolor='white',
                linewidth=1.5
            )
            ax.set_xticks(range(len(grouped_data)))
            ax.set_xticklabels(grouped_data.index, rotation=0 if len(grouped_data) <= 5 else 45, ha='center' if len(grouped_data) <= 5 else 'right', fontsize=11)
            ax.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax.set_ylabel(f"{y_col} {'(Lakhs)' if y_col == 'Total Amount' else ''}", fontsize=12, fontweight="bold")
            if y_col == "Total Amount":
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/100000:.0f}'))
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if y_col == "Total Amount":
                    label = f"₹{height:,.0f}"
                else:
                    label = f"{height:.0f}"
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + height*0.01,
                    label,
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                    fontsize=9
                )
        
        chart_data = [{"name": str(k), "value": float(v)} for k, v in grouped_data.items()]
    
    if not dual_metrics:
        ax.set_title(ai_plan.get("title", "Anandhaas Analysis"), fontsize=16, fontweight="bold", pad=20)
    else:
        fig.suptitle(ai_plan.get("title", "Anandhaas Analysis"), fontsize=16, fontweight="bold")
    
    plt.tight_layout()
    if dual_metrics:
        plt.subplots_adjust(top=0.9)
    return chart_data, fig

def generate_simple_response(ai_plan: dict, chart_data: list = None) -> str:
    chart_desc_map = {"bar": "comparison chart", "pie": "distribution chart", "line": "trend chart"}
    chart_desc = chart_desc_map.get(ai_plan.get("chart_type", "bar"), "chart")
    filters = ai_plan.get("filters", [])
    x_axis = ai_plan.get("x_axis", "Branch Name")
    
    # Generate specific insights for highest revenue queries
    if chart_data and x_axis == "Item-Branch" and ai_plan.get("y_axis") == "Total Amount":
        if chart_data:
            top_item = chart_data[0]
            item_branch = top_item["name"].split(" @ ")
            if len(item_branch) == 2:
                return f"The highest revenue murukku item is '{item_branch[0]}' at {item_branch[1]} branch with ₹{top_item['value']:,.0f} revenue."
    
    parts = []
    for filter_type, filter_value in filters:
        if filter_type == "date_month":
            month_names = [
                "",
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ]
            if isinstance(filter_value, int) and 1 <= filter_value <= 12:
                parts.append(f"in {month_names[filter_value]}")
        elif filter_type.endswith("_in"):
            parts.append(f"for {', '.join(map(str, filter_value))}")
        else:
            parts.append(f"for {filter_value}")
    filter_text = ""
    if parts:
        filter_text = " " + " ".join(parts)
    return (
        f"Created a {chart_desc} showing {ai_plan.get('y_axis', 'Total Amount')} by "
        f"{ai_plan.get('x_axis', 'Branch Name')}{filter_text}."
    )

@app.route("/api/dashboard-data", methods=["GET"])
def get_dashboard_data():
    global anandhaas_data
    if anandhaas_data is None:
        anandhaas_data = load_anandhaas_data()

    if anandhaas_data is None:
        return jsonify({"error": "Data not available"}), 404

    analysis = analyze_anandhaas_structure(anandhaas_data)
    if analysis.get("date_range"):
        analysis["date_range"]["start"] = analysis["date_range"]["start"].isoformat()
        analysis["date_range"]["end"] = analysis["date_range"]["end"].isoformat()
    return jsonify(analysis)

@app.route("/api/query", methods=["POST"])
def process_query():
    global anandhaas_data
    try:
        payload = request.get_json(silent=True) or {}
        query = payload.get("query", "").strip()
        if not query:
            return jsonify({"error": "Query is required"}), 400

        if anandhaas_data is None:
            anandhaas_data = load_anandhaas_data()
        if anandhaas_data is None:
            return jsonify({"error": "Data not available. Ensure anandhaas_sweets.xlsx exists."}), 404

        data_analysis = analyze_anandhaas_structure(anandhaas_data)
        ai_plan = get_ai_plan(query, data_analysis)
        chart_data, fig = create_anandhaas_visualization(anandhaas_data, ai_plan)
        response_text = generate_simple_response(ai_plan, chart_data)

        try:
            chart_title = ai_plan.get("title", "Anandhaas Revenue Analysis")
            pdf_bytes = generate_pdf_report(fig, chart_title, response_text)
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            
            # Store last PDF data like Streamlit session_state
            global last_pdf_data
            last_pdf_data = {
                'data': pdf_bytes,
                'title': chart_title,
                'insights': response_text,
                'filename': f"{chart_title.replace(' ', '_')}_report.pdf"
            }
            print(f"PDF stored: {chart_title}, size: {len(pdf_bytes)} bytes")
        except Exception as e:
            print(f"PDF generation error: {e}")
            pdf_b64 = None

        plt.close(fig)

        return jsonify({
            "original_query": query,
            "chart_type": ai_plan.get("chart_type", "bar"),
            "title": ai_plan.get("title", "Analysis"),
            "data": chart_data,
            "x_axis": ai_plan.get("x_axis", "Branch Name"),
            "y_axis": ai_plan.get("y_axis", "Total Amount"),
            "insights": response_text,
            "pdf_base64": pdf_b64,
            "pdf_filename": f"{ai_plan.get('title','report').replace(' ', '_')}.pdf",
            "dual_metrics": ai_plan.get("dual_metrics", False),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    temp_file_path = None
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file"}), 400
        
        audio_file = request.files["audio"]
        
        if not SARVAM_API_KEY:
            return jsonify({"transcript": "Please configure SARVAM_API_KEY in .env file"})
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        
        audio_file.save(temp_file_path)
        
        headers = {"api-subscription-key": SARVAM_API_KEY}
        with open(temp_file_path, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            response = requests.post(SARVAM_STT_URL, headers=headers, files=files, timeout=45)
        
        if response.status_code == 200:
            transcript = response.json().get("transcript", "")
            return jsonify({"transcript": transcript})
        else:
            return jsonify({"transcript": f"Transcription failed: {response.status_code}"})
        
    except Exception as e:
        return jsonify({"transcript": f"Error: {str(e)}"})
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

@app.route("/api/tts", methods=["POST"])
def tts_api():
    return jsonify({"error": "TTS not available"}), 500

def generate_pdf_report(fig, title, insights):
    with io.BytesIO() as pdf_buffer:
        with PdfPages(pdf_buffer) as pdf:
            pdf.savefig(fig, bbox_inches="tight", dpi=150)
            fig_text, ax_text = plt.subplots(figsize=(6, 4))
            ax_text.text(0.05, 0.95, title, fontsize=12, fontweight="bold", transform=ax_text.transAxes)
            ax_text.text(0.05, 0.85, "Key Insights:", fontsize=10, fontweight="bold", transform=ax_text.transAxes)
            insight_lines = insights.replace(". ", ".\n").split("\n")
            y_pos = 0.75
            for line in insight_lines[:10]:
                if line.strip():
                    ax_text.text(0.05, y_pos, line.strip(), fontsize=9, transform=ax_text.transAxes, wrap=True)
                    y_pos -= 0.08
            ax_text.axis("off")
            pdf.savefig(fig_text, bbox_inches="tight", dpi=150)
            plt.close(fig_text)
        pdf_buffer.seek(0)
        return pdf_buffer.read()

def send_pdf_to_slack(pdf_bytes, filename, title, initial_comment):
    """Send PDF to Slack - exact copy from working Streamlit version"""
    token = SLACK_BOT_TOKEN
    channel = SLACK_CHANNEL_ID
    if not token or not channel:
        return {"success": False, "message": "Slack not configured"}
    try:
        client = WebClient(token=token)
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_file.seek(0)
        response = client.files_upload_v2(
            channel=channel,
            file=pdf_file,
            filename=filename,
            title=title,
            initial_comment=initial_comment
        )
        if response and response.get("ok"):
            return {"success": True, "message": "Successfully sent to Slack"}
        else:
            error_msg = response.get("error", "Unknown error") if response else "Unknown error"
            return {"success": False, "message": f"Failed to send to Slack: {error_msg}"}
    except SlackApiError as e:
        error_msg = str(e.response.get("error", str(e))) if hasattr(e, 'response') else str(e)
        return {"success": False, "message": f"Slack API error: {error_msg}"}
    except Exception as e:
        return {"success": False, "message": f"Error sending to Slack: {str(e)}"}

@app.route("/api/send-to-slack", methods=["POST", "GET"])
def send_to_slack_api():
    print("=== SLACK ENDPOINT CALLED ===")
    try:
        global last_pdf_data
        print(f"PDF available: {bool(last_pdf_data.get('data'))}")
        print(f"PDF size: {len(last_pdf_data.get('data', b''))} bytes")
        
        if not last_pdf_data.get('data'):
            return jsonify({"success": False, "message": "No PDF available. Generate a chart first."}), 400
        
        print("Calling send_pdf_to_slack...")
        result = send_pdf_to_slack(
            pdf_bytes=last_pdf_data['data'],
            filename=last_pdf_data['filename'],
            title=last_pdf_data['title'],
            initial_comment=last_pdf_data['insights']
        )
        print(f"Slack result: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Slack endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/last-pdf-info", methods=["GET"])
def get_last_pdf_info():
    """Get info about the last generated PDF like Streamlit session_state"""
    global last_pdf_data
    if last_pdf_data.get('data'):
        return jsonify({
            "available": True,
            "filename": last_pdf_data['filename'],
            "title": last_pdf_data['title']
        })
    else:
        return jsonify({"available": False})

if __name__ == "__main__":
    app.run(debug=True, port=5000)