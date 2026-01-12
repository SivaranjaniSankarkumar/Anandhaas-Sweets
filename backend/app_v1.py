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

# S3 Configuration - Multiple parquet files
S3_BUCKET = "anandhaas-sweets"
S3_KEYS = [
    "output/parquet/part-00000-38030c4c-a09f-4086-a3bf-eaf678a355a0-c000.snappy.parquet",  # July
    "output/parquet/part-00001-38030c4c-a09f-4086-a3bf-eaf678a355a0-c000.snappy.parquet"   # August
]

anandhaas_data = None
last_pdf_data = {"data": None, "title": "", "insights": "", "filename": ""}

# Slack configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNELS = {
    "test_channel_1": os.getenv("SLACK_CHANNEL_ID") or "C09UUJZ56QJ",
    "test_channel_2": "C0A6JK35E20"
}

print(f"DEBUG: SLACK_BOT_TOKEN loaded: {SLACK_BOT_TOKEN[:20] if SLACK_BOT_TOKEN else 'None'}...")
print(f"DEBUG: SLACK_CHANNELS loaded: {SLACK_CHANNELS}")

try:
    test_client = WebClient(token=SLACK_BOT_TOKEN)
    test_response = test_client.auth_test()
    print(f"DEBUG: Slack auth test successful: {test_response.get('ok')}")
except Exception as e:
    print(f"DEBUG: Slack auth test failed: {e}")

def load_anandhaas_data() -> pd.DataFrame | None:
    """Load data from S3 parquet files - combine July and August"""
    try:
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        combined_df = None
        
        # Load each parquet file and combine
        for i, s3_key in enumerate(S3_KEYS):
            try:
                print(f"📊 Loading file {i+1}/{len(S3_KEYS)}: {s3_key}")
                response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
                parquet_data = response['Body'].read()
                
                # Read parquet data
                df = pd.read_parquet(io.BytesIO(parquet_data))
                print(f"   Loaded {len(df)} records")
                
                # Combine with previous data
                if combined_df is None:
                    combined_df = df
                else:
                    combined_df = pd.concat([combined_df, df], ignore_index=True)
                    
            except Exception as e:
                print(f"⚠️ Failed to load {s3_key}: {e}")
                continue
        
        if combined_df is None or combined_df.empty:
            print(f"❌ No data loaded from any S3 files")
            return None
            
        print(f"📊 Combined S3 data loaded: {len(combined_df)} records")
        print(f"Available columns: {list(combined_df.columns)}")
        
        # Use exact column names from S3 data - NO MAPPING, NO DROPPING
        # Only convert data types for processing
        combined_df["Date"] = pd.to_datetime(combined_df["Date"], errors="coerce")
        combined_df["Row_Total"] = pd.to_numeric(combined_df["Row_Total"], errors="coerce")
        combined_df["Quantity_Inventory_UoM"] = pd.to_numeric(combined_df["Quantity_Inventory_UoM"], errors="coerce").fillna(1)
        
        print(f"Final combined dataset: {len(combined_df)} records (no rows dropped)")
        print(f"Date range: {combined_df['Date'].min()} to {combined_df['Date'].max()}")
        print(f"Branches: {combined_df['Branch_Name'].unique()[:5]}")
        print(f"Sample items: {combined_df['Item_Service_Description'].unique()[:5]}")
        
        return combined_df
        
    except Exception as e:
        print(f"❌ Cannot load data from S3: {e}")
        return None





def analyze_anandhaas_structure(data: pd.DataFrame) -> dict:
    if data is None or data.empty:
        return {}
    
    clean_branches = [b for b in data["Branch_Name"].dropna().unique()]
    clean_items = [i for i in data["Item_Service_Description"].dropna().unique()]
    
    analysis = {
        "total_records": len(data),
        "branches": clean_branches,
        "items": clean_items[:50],
        "date_range": {
            "start": data["Date"].min(),
            "end": data["Date"].max(),
        },
        "revenue_stats": {
            "total": float(data["Row_Total"].sum()),
            "avg": float(data["Row_Total"].mean()),
            "max": float(data["Row_Total"].max()),
            "min": float(data["Row_Total"].min()),
        },
    }
    
    # Add section and item group info
    if "SK_Section" in data.columns:
        analysis["sections"] = list(data["SK_Section"].unique())
    if "Item Group Name" in data.columns:
        analysis["item_groups"] = list(data["Item Group Name"].unique())
    if "Sales Group Name" in data.columns:
        analysis["sales_groups"] = list(data["Sales Group Name"].unique())
    
    return analysis

def get_ai_plan(query: str, data_analysis: dict) -> dict:
    branches = data_analysis.get("branches", [])
    items = data_analysis.get("items", [])
    sections = data_analysis.get("sections", [])
    item_groups = data_analysis.get("item_groups", [])
    sales_groups = data_analysis.get("sales_groups", [])

    try:
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

        prompt = f"""
Analyze this business query about sweets sales and create a visualization plan.

Query: "{query}"

Available Data:
- Branches: {branches[:20]}
- Sections: {sections[:20]}
- Sales Groups: {sales_groups}
- Item Groups: {item_groups[:20]}
- Items: {items[:30]}

Return ONLY valid JSON in this exact format:
{{
  "chart_type": "bar|pie|line|dual_bar",
  "x_axis": "Branch_Name|SK_Section|Item_Service_Description|Item Group Name|Sales Group Name|Month|Date",
  "y_axis": "Row_Total|Quantity_Inventory_UoM|count|dual",
  "aggregation": "sum|mean|count",
  "branch_filters": null or [string, ...],
  "section_filters": null or [string, ...],
  "item_filters": null or [string, ...],
  "item_group_filters": null or [string, ...],
  "sales_group_filters": null or [string, ...],
  "month_filter": null or month_number or [month_numbers],
  "date_filter": null or "YYYY-MM-DD" or ["YYYY-MM-DD", "YYYY-MM-DD"],
  "year_filter": null or year_number or [year_numbers],
  "limit": null or number,
  "title": "chart title",
  "dual_metrics": false or true
}}

CRITICAL RULES:
- CRITICAL: TOP N QUERIES - Extract limit numbers from queries:
  * "top 5", "top 10", "top 7", "first 5", "best 10" → extract as limit: 5, 10, 7, 5, 10
  * "highest 3", "lowest 5", "bottom 10" → extract as limit: 3, 5, 10
  * "show me 5", "give me 10", "list 7" → extract as limit: 5, 10, 7
  * "Top 10 Roast Items" → extract as limit: 10
  * "Top 5 branches" → extract as limit: 5
  * ANY query with "top [NUMBER]" or "[NUMBER] top" → ALWAYS extract the NUMBER as limit
  * When user specifies a number, ALWAYS extract it as limit
  * If no number specified, set limit: null to show all results
- CRITICAL: INTELLIGENT ITEM MATCHING RULES:
  * When user asks for "Bombay Mixture" → use item_filters: ["bombay mixture"] to find ALL bombay mixture variations
  * When user asks for "ALL Mysore Pak" or "all mysore pak items" → use item_filters: ["mysore pak"] to find ALL variations
  * When user asks for "ALL Achu Murukku" → use item_filters: ["achu murukku"] to find ALL variations  
  * When user asks for "Mysore Pak Special" → use item_filters: ["mysore pak special"] for specific item
  * CRITICAL: EXACT ITEM MATCHING - Use the EXACT item name user mentions, don't substitute with similar items
  * "Bombay Mixture" ≠ "Corn Mixture" - these are different items!
  * "Achu Murukku" ≠ "Ribbon Pakoda" - these are different items!
  * CRITICAL: When user says "ALL [ITEM_NAME]" → use single base filter ["item_name"] NOT multiple specific items
  * GROUP SEARCH: Use base item name ("mysore pak", "achu murukku", "bombay mixture") to find all variations
  * NEVER list specific items when user asks for "ALL" - always use base search term
  * NEVER substitute or guess item names - use EXACTLY what user says
  * Always prioritize showing ALL relevant items for revenue analysis unless user is very specific
- For months: january=1, february=2, march=3, april=4, may=5, june=6, july=7, august=8, september=9, october=10, november=11, december=12
- For dates: extract specific dates ("2024-08-19") or date ranges (["2024-08-19", "2024-08-20"])
- For years: extract year numbers (2023, 2024, etc.)
- Branches: "VV", "SK", "SBC", "RMN", "THD", "KMR", "SLR", "SMR", "AVR", "LMJ", "NLR", "SPM", "RSP", "RPP", "KCR", "TMR", "KNP", "PMR", "SNC", "KUN", etc.
- Sales Groups: "Sales - Ecom", "Sales - Online", "Sales - SAS", "Sales - Party Order"
- Sections: "Boli Section", "Milk Section", "Bakery", "Kovilpatti Section", "Mixture Section", etc.
- CRITICAL: Extract ALL branch names mentioned in query, including variations:
  * "VV branch" or "VV" → "VV"
  * "SK branch" or "SK" → "SK"
  * Look for patterns like "X branch, Y branch" or "X and Y branches"
  * Parse comma-separated lists: "VV, SK, SBC" should extract all three branches
- When user mentions "ecom", "e-commerce", "ecommerce" → use sales_group_filters: ["Sales - Ecom"] ONLY
- When user mentions "online" → use sales_group_filters: ["Sales - Online"] ONLY
- When user mentions "ecommerce alone" or "ecom alone" → use sales_group_filters: ["Sales - Ecom"] ONLY, NOT both ecom and online
- When user mentions "offline", "store", "SAS" → use sales_group_filters: ["Sales - SAS"]
- When user mentions "party order" → use sales_group_filters: ["Sales - Party Order"]
- When user mentions "section wise" → use x_axis: "SK_Section"
- When user mentions "item wise" → use x_axis: "Item_Service_Description"
- When user mentions "branch wise" → use x_axis: "Branch_Name"
- When user mentions "sales group wise" → use x_axis: "Sales Group Name"
- If user asks "how many" or "count" with quantity → use y_axis: "Quantity_Inventory_UoM" and aggregation: "sum"
- If user asks "how many" or "count" without quantity → use y_axis: "count" and aggregation: "count"
- For "each branch" or "by branch", use x_axis: "Branch_Name"
- For "each section" or "by section", use x_axis: "SK_Section"
- IMPORTANT: For "distribution", "breakdown", "share", "split", "proportion" → ALWAYS use chart_type: "pie"
- For "comparison", "compare", "vs" → use chart_type: "bar"
- CRITICAL: When user mentions "by months", "monthly", "month wise", "each month" → use x_axis: "Month" NOT "Date"
- For time/trend with specific dates, use chart_type: "line" with x_axis: "Date"
- For monthly analysis, ALWAYS use x_axis: "Month" and chart_type: "bar"
- For daily analysis over short periods, use x_axis: "Date" and chart_type: "line"
- CRITICAL: DUAL METRICS DETECTION - Set dual_metrics: true when:
  * User asks for "comparison" between different categories ("sweets vs kaaram", "revenue comparison for sweets and kaaram")
  * User mentions "compare", "comparison", "vs", "versus", "and" between different groups
  * User asks for multiple item groups ("sweets and kaaram", "bakery and mixture")
  * User asks for multiple branches ("VV and SK revenue", "compare VV vs SK")
  * User asks for multiple sections ("boli section vs milk section")
  * User asks for multiple sales groups ("ecom vs online", "ecom and sas comparison")
  * User asks for multiple dates ("19th vs 20th August", "july vs august")
  * User asks for multiple months ("january vs february", "compare jan and feb")
  * CRITICAL: When user says "revenue comparison for X and Y" → set dual_metrics: true, x_axis based on category type
  * For item group comparison → set x_axis: "Item Group Name"
  * For branch comparison → set x_axis: "Branch_Name"
  * For section comparison → set x_axis: "SK_Section"
- CRITICAL: Date filtering rules:
  * "today", "yesterday" → extract current/previous date
  * "19th August", "Aug 19", "August 19th" → extract as "2024-08-19" (assume current year if not specified)
  * "19th August and 20th August" → extract as date_filter: ["2024-08-19", "2024-08-20"]
  * "from Aug 19 to Aug 20" → extract date range
  * "August 2024", "Aug 2024" → extract month and year filters
  * "2024" → extract year filter
- Match user terms intelligently to available data
- IMPORTANT: When no year is specified in dates, assume 2024
"""

        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"temperature": 0.1},
        })
        response = bedrock.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
        raw = response["body"].read()
        result = json.loads(raw)
        ai_text = result["output"]["message"]["content"][0]["text"].strip()

        # Debug: Show what AI returned
        print(f"DEBUG: AI Response: {ai_text}")

        if "{" in ai_text and "}" in ai_text:
            start = ai_text.find("{")
            end = ai_text.rfind("}") + 1
            json_str = ai_text[start:end]
            plan = json.loads(json_str)
        else:
            raise ValueError("Model did not return JSON")

        # Set minimal defaults
        plan.setdefault("chart_type", "bar")
        plan.setdefault("x_axis", "Branch_Name")
        plan.setdefault("y_axis", "Row_Total")
        plan.setdefault("aggregation", "sum")
        plan.setdefault("title", "Sweets Sales Analysis")
        plan.setdefault("dual_metrics", False)
        plan.setdefault("limit", None)

        # Build filters dynamically like restaurant dashboard
        filters = []

        if plan.get("branch_filters"):
            if len(plan["branch_filters"]) == 1:
                filters.append(("Branch_Name", plan["branch_filters"][0]))
            else:
                filters.append(("Branch_in", plan["branch_filters"]))

        if plan.get("section_filters"):
            if len(plan["section_filters"]) == 1:
                filters.append(("SK_Section", plan["section_filters"][0]))
            else:
                filters.append(("Section_in", plan["section_filters"]))

        if plan.get("item_filters"):
            if len(plan["item_filters"]) == 1:
                filters.append(("Item_Service_Description", plan["item_filters"][0]))
            else:
                filters.append(("Item_in", plan["item_filters"]))

        if plan.get("item_group_filters"):
            if len(plan["item_group_filters"]) == 1:
                filters.append(("Item Group Name", plan["item_group_filters"][0]))
            else:
                filters.append(("Item_Group_in", plan["item_group_filters"]))

        if plan.get("sales_group_filters"):
            if len(plan["sales_group_filters"]) == 1:
                filters.append(("Sales Group Name", plan["sales_group_filters"][0]))
            else:
                filters.append(("Sales_Group_in", plan["sales_group_filters"]))

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
        
        print(f"\n=== DYNAMIC AI PLAN ===")
        print(f"Query: {query}")
        print(f"AI Generated Plan: {plan}")
        print(f"Extracted Filters: {plan.get('filters', [])}")
        print(f"LIMIT EXTRACTED: {plan.get('limit')}")
        print(f"========================\n")
        return plan

    except Exception as e:
        print(f"AI model failed to process query: {str(e)}")
        raise

def apply_dynamic_filters(data: pd.DataFrame, filters: list) -> pd.DataFrame:
    """Apply filters dynamically like restaurant dashboard"""
    filtered_data = data.copy()
    
    for filter_type, filter_value in filters:
        if filter_type == "date_month":
            filtered_data = filtered_data[filtered_data["Date"].dt.month == int(filter_value)]
        elif filter_type == "date_month_in":
            month_list = [int(m) for m in filter_value]
            filtered_data = filtered_data[filtered_data["Date"].dt.month.isin(month_list)]
        elif filter_type == "date_specific":
            try:
                if len(filter_value.split('-')) == 2:
                    current_year = 2024  # Assume 2024 for sweets data
                    filter_value = f"{current_year}-{filter_value}"
                target_date = pd.to_datetime(filter_value).date()
                filtered_data = filtered_data[filtered_data["Date"].dt.date == target_date]
                print(f"DEBUG: Date filter '{target_date}' resulted in {len(filtered_data)} records")
            except Exception as e:
                print(f"DEBUG: Date parsing error for '{filter_value}': {e}")
                continue
        elif filter_type == "date_range":
            start_date = pd.to_datetime(filter_value[0])
            end_date = pd.to_datetime(filter_value[1])
            filtered_data = filtered_data[(filtered_data["Date"] >= start_date) & (filtered_data["Date"] <= end_date)]
        elif filter_type == "date_year":
            filtered_data = filtered_data[filtered_data["Date"].dt.year == int(filter_value)]
        elif filter_type == "date_year_in":
            year_list = [int(y) for y in filter_value]
            filtered_data = filtered_data[filtered_data["Date"].dt.year.isin(year_list)]
        elif filter_type in ["Branch_Name", "SK_Section", "Item_Service_Description", "Item Group Name", "Sales Group Name"]:
            filter_value_str = str(filter_value).lower().strip()
            
            # For Item_Service_Description, always use contains matching to find variations
            if filter_type == "Item_Service_Description":
                # Use contains matching for group searches
                mask = filtered_data[filter_type].astype(str).str.contains(filter_value_str, case=False, na=False)
                filtered_data = filtered_data[mask]
                
                # Debug: Show what items were matched
                if not filtered_data.empty:
                    matched_items = filtered_data[filter_type].astype(str).unique()
                    print(f"DEBUG: Items matched for '{filter_value_str}': {sorted(matched_items)}")
                    total_revenue = filtered_data['Row_Total'].sum()
                    print(f"DEBUG: Total revenue: ₹{total_revenue:,.2f}")
                
                print(f"DEBUG: Filter '{filter_type}={filter_value}' resulted in {len(filtered_data)} records")
            else:
                # For other columns, try exact match first
                exact_match = filtered_data[filtered_data[filter_type].astype(str).str.lower().str.strip() == filter_value_str]
                
                if not exact_match.empty:
                    filtered_data = exact_match
                    print(f"DEBUG: Found exact match for '{filter_value_str}': {len(exact_match)} records")
                else:
                    # Use contains matching for partial searches
                    mask = filtered_data[filter_type].astype(str).str.contains(filter_value_str, case=False, na=False)
                    filtered_data = filtered_data[mask]
                    print(f"DEBUG: Filter '{filter_type}={filter_value}' resulted in {len(filtered_data)} records")
        elif filter_type in ["Branch_in", "Section_in", "Item_in", "Item_Group_in", "Sales_Group_in"]:
            col_map = {
                "Branch_in": "Branch_Name",
                "Section_in": "SK_Section",
                "Item_in": "Item_Service_Description",
                "Item_Group_in": "Item Group Name",
                "Sales_Group_in": "Sales Group Name",
            }
            col = col_map[filter_type]
            if col in filtered_data.columns:
                # For Item_in, use contains matching to find all variations
                if filter_type == "Item_in":
                    all_matches = pd.DataFrame()
                    for search_term in filter_value:
                        search_term_lower = str(search_term).lower().strip()
                        # Use contains matching to find all variations
                        mask = filtered_data[col].astype(str).str.contains(search_term_lower, case=False, na=False)
                        matches = filtered_data[mask]
                        all_matches = pd.concat([all_matches, matches], ignore_index=True)
                        
                        if not matches.empty:
                            matched_items = matches[col].astype(str).unique()
                            print(f"DEBUG: Found items for '{search_term}': {sorted(matched_items)}")
                    
                    filtered_data = all_matches.drop_duplicates()
                    print(f"DEBUG: Total items after Item_in filter: {len(filtered_data)} records")
                else:
                    # For other filters, use exact match
                    values = [str(v) for v in filter_value]
                    clean_data = filtered_data.dropna(subset=[col])
                    filtered_data = clean_data[clean_data[col].astype(str).isin(values)]
    
    if filtered_data.empty:
        print(f"DEBUG: Applied filters: {filters}")
        print(f"DEBUG: Original data shape: {data.shape}")
        raise ValueError(f"No data found after applying filters. Check filter values against available data.")
    
    return filtered_data

def create_anandhaas_visualization(data: pd.DataFrame, ai_plan: dict):
    dual_metrics = ai_plan.get("dual_metrics", False) or ai_plan.get("y_axis") == "dual"
    comparison_type = ai_plan.get("comparison_type", "metric")
    
    if dual_metrics:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 10))
    else:
        fig, ax = plt.subplots(figsize=(20, 12))
    
    # Apply AI-driven dynamic filters
    filtered_data = apply_dynamic_filters(data, ai_plan.get("filters", []))

    if filtered_data is None or filtered_data.empty:
        raise ValueError("No data found after applying filters.")

    x_col = ai_plan.get("x_axis", "Branch_Name")
    
    if x_col == "Month":
        filtered_data = filtered_data.copy()
        filtered_data["Month"] = filtered_data["Date"].dt.strftime("%B %Y")
        filtered_data["MonthSort"] = filtered_data["Date"].dt.to_period("M")
    
    if dual_metrics:
        x_col = ai_plan.get("x_axis", "Branch_Name")
        y_col_1 = ai_plan.get("y_axis", "Row_Total")
        y_col_2 = ai_plan.get("y_axis_secondary", "Quantity_Inventory_UoM")
        agg_1 = ai_plan.get("aggregation", "sum")
        agg_2 = ai_plan.get("aggregation_secondary", "sum")
        limit = ai_plan.get("limit")
        
        if comparison_type == "monthly" and ai_plan.get("month_filter"):
            # Month comparison logic
            month_list = [int(m) for m in ai_plan.get("month_filter", [])]
            month_names = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                          7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
            
            # Get top items first
            if y_col_1 == "count":
                top_items = filtered_data.groupby(x_col).size().sort_values(ascending=False)
            else:
                top_items = filtered_data.groupby(x_col)[y_col_1].agg(agg_1).sort_values(ascending=False)
            
            if limit and isinstance(limit, int) and limit > 0:
                top_items = top_items.head(limit)
            
            filtered_data = filtered_data[filtered_data[x_col].isin(top_items.index)]
            
            # Create data for each month
            metric1_data = {}
            for month in month_list:
                month_data = filtered_data[filtered_data["Date"].dt.month == month]
                if y_col_1 == "count":
                    month_metric = month_data.groupby(x_col).size()
                else:
                    month_metric = month_data.groupby(x_col)[y_col_1].agg(agg_1)
                metric1_data[month_names.get(month, f"Month {month}")] = month_metric.reindex(top_items.index, fill_value=0)
            
            # Create side-by-side bars
            items = list(top_items.index)
            x_pos = range(len(items))
            width = 0.35
            months = list(metric1_data.keys())
            colors = ['#1e40af', '#059669', '#d97706', '#dc2626']
            
            for i, month in enumerate(months):
                values = [metric1_data[month].get(item, 0) for item in items]
                bars = ax1.bar([x + width*i for x in x_pos], values, width, 
                              label=month, color=colors[i % len(colors)], alpha=0.95, edgecolor='white', linewidth=1.5)
                
                for bar in bars:
                    height = bar.get_height()
                    label = f'₹{height:,.0f}' if y_col_1 == 'Row_Total' else f'{height:.0f}'
                    ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01, 
                            label, ha='center', va='bottom', fontweight='bold', fontsize=8)
            
            ax1.set_xticks([x + width/2 for x in x_pos])
            ax1.set_xticklabels(items, rotation=45, ha='right', fontsize=10)
            ax1.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax1.set_ylabel(f"{y_col_1} ({agg_1})", fontsize=12, fontweight="bold")
            ax1.set_title(f"{' vs '.join(months)} {y_col_1} Comparison", fontsize=14, fontweight="bold")
            ax1.legend()
            
            # Second chart shows percentage comparison
            total_by_item = {item: sum(metric1_data[month].get(item, 0) for month in months) for item in items}
            percentages = {}
            for month in months:
                percentages[month] = [(metric1_data[month].get(item, 0) / total_by_item[item] * 100) if total_by_item[item] > 0 else 0 for item in items]
            
            for i, month in enumerate(months):
                bars = ax2.bar([x + width*i for x in x_pos], percentages[month], width, 
                              label=month, color=colors[i % len(colors)], alpha=0.95)
                
                for j, bar in enumerate(bars):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + 1, f'{height:.1f}%',
                            ha='center', va='bottom', fontweight='bold', fontsize=8)
            
            ax2.set_xticks([x + width/2 for x in x_pos])
            ax2.set_xticklabels(items, rotation=45, ha='right', fontsize=10)
            ax2.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax2.set_ylabel("Percentage Share", fontsize=12, fontweight="bold")
            ax2.set_title("Percentage Share Comparison", fontsize=14, fontweight="bold")
            ax2.legend()
            
            chart_data = []
            for item in items:
                item_data = {"name": str(item)}
                for month in months:
                    item_data[month.lower()] = float(metric1_data[month].get(item, 0))
                chart_data.append(item_data)
        
        else:
            # Regular dual metrics (two different metrics)
            if y_col_1 == "count":
                metric1_data = filtered_data.groupby(x_col).size().sort_values(ascending=False)
            else:
                metric1_data = filtered_data.groupby(x_col)[y_col_1].agg(agg_1).sort_values(ascending=False)
            
            if limit and isinstance(limit, int) and limit > 0:
                metric1_data = metric1_data.head(limit)
            
            if y_col_2 == "count":
                metric2_data = filtered_data.groupby(x_col).size().reindex(metric1_data.index, fill_value=0)
            else:
                metric2_data = filtered_data.groupby(x_col)[y_col_2].agg(agg_2).reindex(metric1_data.index, fill_value=0)
            
            # First metric chart
            bars1 = ax1.bar(range(len(metric1_data)), metric1_data.values, color='#1e40af', alpha=0.95, edgecolor='white', linewidth=1.5)
            ax1.set_xticks(range(len(metric1_data)))
            ax1.set_xticklabels(metric1_data.index, rotation=0 if len(metric1_data) <= 5 else 45, ha='center' if len(metric1_data) <= 5 else 'right', fontsize=11)
            ax1.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax1.set_ylabel(f"{y_col_1} ({agg_1})", fontsize=12, fontweight="bold")
            ax1.set_title(f"{y_col_1} Analysis", fontsize=14, fontweight="bold")
            
            for i, bar in enumerate(bars1):
                height = bar.get_height()
                if y_col_1 == 'Row_Total':
                    label = f'₹{height:,.0f}'
                elif y_col_1 == 'Quantity_Inventory_UoM':
                    common_uom = filtered_data["Inventory_UoM"].mode().iloc[0] if not filtered_data["Inventory_UoM"].mode().empty else "Units"
                    label = f'{height:.1f} {common_uom}'  # Show 1 decimal place
                else:
                    label = f'{height:.0f}'
                ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01, label,
                        ha='center', va='bottom', fontweight='bold', fontsize=9)
            
            # Second metric chart
            bars2 = ax2.bar(range(len(metric2_data)), metric2_data.values, color='#059669', alpha=0.95, edgecolor='white', linewidth=1.5)
            ax2.set_xticks(range(len(metric2_data)))
            ax2.set_xticklabels(metric2_data.index, rotation=0 if len(metric2_data) <= 5 else 45, ha='center' if len(metric2_data) <= 5 else 'right', fontsize=11)
            ax2.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax2.set_ylabel(f"{y_col_2} ({agg_2})", fontsize=12, fontweight="bold")
            ax2.set_title(f"{y_col_2} Analysis", fontsize=14, fontweight="bold")
            
            for i, bar in enumerate(bars2):
                height = bar.get_height()
                if y_col_2 == 'Row_Total':
                    label = f'₹{height:,.0f}'
                elif y_col_2 == 'Quantity_Inventory_UoM':
                    common_uom = filtered_data["Inventory_UoM"].mode().iloc[0] if not filtered_data["Inventory_UoM"].mode().empty else "Units"
                    label = f'{height:.1f} {common_uom}'  # Show 1 decimal place
                else:
                    label = f'{height:.0f}'
                ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01, label,
                        ha='center', va='bottom', fontweight='bold', fontsize=9)
            
            chart_data = []
            for item in metric1_data.index:
                chart_data.append({
                    "name": str(item),
                    "revenue": float(metric1_data.get(item, 0)),
                    "count": float(metric2_data.get(item, 0))
                })
        
    else:
        # Single metric visualization
        y_col = ai_plan.get("y_axis", "Row_Total")
        agg_method = ai_plan.get("aggregation", "sum")

        if y_col == "count":
            if x_col == "Month":
                grouped_data = filtered_data.groupby(["MonthSort", "Month"]).size().reset_index(name="count")
                grouped_data = grouped_data.set_index("Month")["count"].sort_index()
            else:
                grouped_data = filtered_data[x_col].value_counts().sort_values(ascending=False)
        else:
            if x_col == "Month":
                grouped_data = filtered_data.groupby(["MonthSort", "Month"])[y_col].agg(agg_method).reset_index()
                grouped_data = grouped_data.set_index("Month")[y_col].sort_index()
            else:
                grouped_data = filtered_data.groupby(x_col)[y_col].agg(agg_method).sort_values(ascending=False)

        # Apply limit if specified
        limit = ai_plan.get("limit")
        print(f"DEBUG: Single metric path - limit value: {limit}")
        print(f"DEBUG: Grouped data length before limit: {len(grouped_data)}")
        if limit and isinstance(limit, int) and limit > 0:
            grouped_data = grouped_data.head(limit)
            print(f"Applied limit: showing top {limit} results")
            print(f"DEBUG: Grouped data length after limit: {len(grouped_data)}")
        else:
            print(f"DEBUG: No limit applied - showing all {len(grouped_data)} results")

        chart_type = ai_plan.get("chart_type", "bar")

        if chart_type == "pie":
            grouped_data = grouped_data.sort_values(ascending=False)
            colors = ['#1e40af', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#65a30d', '#ea580c']
            colors = [colors[i % len(colors)] for i in range(len(grouped_data))]
            
            wedges, texts, autotexts = ax.pie(
                grouped_data.values,
                labels=None,
                autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
                colors=colors,
                startangle=90,
                pctdistance=0.85
            )
            
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_fontweight("bold")
                autotext.set_fontsize(10)
            
            ax.legend(wedges, [f'{name}: ₹{value:,.0f}' if y_col == 'Row_Total' else f'{name}: {value:.0f}' 
                              for name, value in grouped_data.items()], 
                     title=x_col, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10)
        elif chart_type == "line":
            ax.plot(range(len(grouped_data)), grouped_data.values, marker="o", linewidth=3, markersize=8)
            ax.set_xticks(range(len(grouped_data)))
            ax.set_xticklabels(grouped_data.index, rotation=45, ha='right', fontsize=11)
            ax.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax.set_ylabel(y_col, fontsize=12, fontweight="bold")
            ax.grid(True, alpha=0.3)
        else:
            colors = ['#1e40af', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#65a30d', '#ea580c']
            bar_colors = [colors[i % len(colors)] for i in range(len(grouped_data))]
            bars = ax.bar(range(len(grouped_data)), grouped_data.values, color=bar_colors, alpha=0.95)
            ax.set_xticks(range(len(grouped_data)))
            ax.set_xticklabels(grouped_data.index, rotation=45, ha='right', fontsize=11)
            ax.set_xlabel(x_col, fontsize=12, fontweight="bold")
            ax.set_ylabel(y_col, fontsize=12, fontweight="bold")
            
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if y_col == "Row_Total":
                    label = f"₹{height:,.0f}"
                elif y_col == "Quantity_Inventory_UoM":
                    # Get the most common UoM for this data
                    if not filtered_data.empty and "Inventory_UoM" in filtered_data.columns:
                        common_uom = filtered_data["Inventory_UoM"].mode().iloc[0] if not filtered_data["Inventory_UoM"].mode().empty else "Units"
                        label = f"{height:,.1f} {common_uom}"  # Show 1 decimal place for precision
                    else:
                        label = f"{height:,.1f} Units"  # Show 1 decimal place for precision
                else:
                    label = f"{height:.0f}"
                ax.text(bar.get_x() + bar.get_width() / 2.0, height + height*0.01, label,
                       ha="center", va="bottom", fontweight="bold", fontsize=9)
        
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
    
    return f"Created a {chart_desc} showing {ai_plan.get('y_axis', 'Total Amount')} by {ai_plan.get('x_axis', 'Branch Name')}."

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
            return jsonify({"error": "Data not available from S3"}), 404

        data_analysis = analyze_anandhaas_structure(anandhaas_data)
        ai_plan = get_ai_plan(query, data_analysis)
        chart_data, fig = create_anandhaas_visualization(anandhaas_data, ai_plan)
        response_text = generate_simple_response(ai_plan, chart_data)

        try:
            chart_title = ai_plan.get("title", "Anandhaas Sales Analysis")
            pdf_bytes = generate_pdf_report(fig, chart_title, response_text)
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            
            global last_pdf_data
            last_pdf_data = {
                'data': pdf_bytes,
                'title': chart_title,
                'insights': response_text,
                'filename': f"{chart_title.replace(' ', '_')}_report.pdf"
            }
        except Exception as e:
            print(f"PDF generation error: {e}")
            pdf_b64 = None

        plt.close(fig)

        return jsonify({
            "original_query": query,
            "chart_type": ai_plan.get("chart_type", "bar"),
            "title": ai_plan.get("title", "Analysis"),
            "data": chart_data,
            "x_axis": ai_plan.get("x_axis", "Branch_Name"),
            "y_axis": ai_plan.get("y_axis", "Row_Total"),
            "insights": response_text,
            "pdf_base64": pdf_b64,
            "pdf_filename": f"{ai_plan.get('title','report').replace(' ', '_')}.pdf",
            "dual_metrics": ai_plan.get("dual_metrics", False),
            "chart1_title": "Ecom Revenue" if ai_plan.get("dual_metrics") else None,
            "chart2_title": "Online Revenue" if ai_plan.get("dual_metrics") else None,
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

def generate_pdf_report(fig, title, insights):
    with io.BytesIO() as pdf_buffer:
        with PdfPages(pdf_buffer) as pdf:
            # Save only the chart - no separate insights page
            pdf.savefig(fig, bbox_inches="tight", dpi=150)
        pdf_buffer.seek(0)
        return pdf_buffer.read()

def send_pdf_to_slack(pdf_bytes, filename, title, initial_comment, channel_key="test_channel_1"):
    token = SLACK_BOT_TOKEN
    channel = SLACK_CHANNELS.get(channel_key)
    if not token or not channel:
        return {"success": False, "message": "Slack not configured or invalid channel"}
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
            return {"success": True, "message": f"Successfully sent to {channel_key}"}
        else:
            error_msg = response.get("error", "Unknown error") if response else "Unknown error"
            return {"success": False, "message": f"Failed to send to {channel_key}: {error_msg}"}
    except SlackApiError as e:
        error_msg = str(e.response.get("error", str(e))) if hasattr(e, 'response') else str(e)
        return {"success": False, "message": f"Slack API error: {error_msg}"}
    except Exception as e:
        return {"success": False, "message": f"Error sending to Slack: {str(e)}"}

@app.route("/api/send-to-slack", methods=["POST", "GET"])
def send_to_slack_api():
    try:
        global last_pdf_data
        if not last_pdf_data.get('data'):
            return jsonify({"success": False, "message": "No PDF available. Generate a chart first."}), 400
        
        # Get channel selection from request
        channel_key = "test_channel_1"  # default
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            channel_key = data.get("channel", "test_channel_1")
        
        result = send_pdf_to_slack(
            pdf_bytes=last_pdf_data['data'],
            filename=last_pdf_data['filename'],
            title=last_pdf_data['title'],
            initial_comment=last_pdf_data['insights'],
            channel_key=channel_key
        )
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/slack-channels", methods=["GET"])
def get_slack_channels():
    """Get available Slack channels"""
    return jsonify({
        "channels": [
            {"key": "test_channel_1", "name": "Slack Test Channel 1"},
            {"key": "test_channel_2", "name": "Slack Test Channel 2"}
        ]
    })

@app.route("/api/last-pdf-info", methods=["GET"])
def get_last_pdf_info():
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
    app.run(debug=True, port=5001)