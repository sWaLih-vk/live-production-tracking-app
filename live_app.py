import streamlit as st
import pandas as pd
import gspread
import time
from streamlit_option_menu import option_menu
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components 

# Streamlit Page Config
st.set_page_config(
    page_title="Production Dashboard", 
    layout="wide",
    # ADDED: Removes the hamburger menu, footer, and deploy button
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    } 
    # NOTE: Setting menu_items=None entirely usually works, but the above is more robust 
    # to specifically clear the default menu.
)
KPI_VALUE_FONT_SIZE = 70
KPI_LABEL_FONT_SIZE = 20 
# Google Sheets Config
SHEET_NAME = "Calculation" # Used for KPI data
RECENT_SCANNED_SHEET_NAME = "Recent Scanned" # Sheet name for scanned data
SPREADSHEET_ID = "1tqxNHszQ3tJ09mT2F1XxzmywmBP_4uFlHkB24EwvN7s"

# Image Configuration (KEYS MUST MATCH 'Area - Line')
EMPLOYEE_IMAGES = {
    # Key format: "Area - Line"
    "Line-1 - Building": [
        ("Line-1-Building-John paul.jpeg", "John paul"),
        ("Line-1-Building-Normandy.jpg", "Normandy"),
    ],
    "Line-1 - Curing": [
        ("Line-1-Curing-Charles.JPG", "Charles"),
        ("Line-1-Curing-Chathuranga madushan.jpg", "Madushan"),
        
    ],
    "Line-2 - Building": [
        ("Line-2-Building-Jonh eurhis.jpeg", "Jonh eurhis"),
        ("Line-2-Building-Samuel.jpg", "Samuel"),
        
    ],
    "Line-2 - Curing": [
        ("Line-2-Curing-Gilbert Mutura.jpg", "Gilbert Mutura"),
        ("Line-2-Curing-Sudip.jpg", "Sudip"),
    ],
        
    "Line-3 - Building": [
        ("Line-3-Building-Ian.jpg", "Ian"),
        
        
    ],
    "Line-3 - Curing": [
        ("Line-3-Curing-Joseph.jpg", "Joseph"),
        
    ],
    "Line-4 - Building": [
        ("Line-4-Building-Asela.jpg", "Asela"),
        
    ],
    "Line-4 - Curing": [
        ("Line-4-Curing-Danushka.jpg", "Danushka"),
        
    ],
    "Line-MMV - Building": [
        ("Line-MMV-Building-Pramoth.jpg", "Pramoth"),
        ("Line-MMV-Building-Ramesh.jpeg", "Ramesh"),
        
        
        
    ],
    "Line-MMV - Curing": [
        
        ("Line-MMV-Building-Simon.jpeg", "Simon"),
        ("Line-MMV-Building-Chemal.jpg", "Chamal"),
        ("Line-MMV-Building-Chamidu.JPG", "Chamidu"),
    ],
}

LOGO_PATH = "urbmlogonew.png"

# Google Sheets Client (Resource Caching)
@st.cache_resource(ttl=3600)
def get_gspread_client():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Missing 'gcp_service_account' in st.secrets.toml.")
            return None
            
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        return gc
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets API. Check your secrets.toml configuration. Error: {e}")
        return None

# Load & Clean KPI Data (Refreshes every 10 seconds)
@st.cache_data(ttl=10) # TTL of 10 seconds for production data refresh
def load_data():
    gc = get_gspread_client()
    if gc is None:
        return pd.DataFrame()

    try:
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        data = worksheet.get_all_values()

        if not data or len(data) < 2:
            st.warning("Google Sheet is empty or only contains headers.")
            return pd.DataFrame()

        df = pd.DataFrame(data[1:], columns=data[0])

        df.rename(columns={
            'Planning': 'Planned Sleeves',
            'Building': 'Sleeves Build',
            'Pending': 'Not Produced Sleeves',
            'Percentage': 'Production rate %'
        }, inplace=True)

        # --- START: ERROR HANDLING FIX ---
        ERROR_REPLACEMENTS = {
            '#DIV/0!': '0.0', 
            '#N/A': '0.0', 
            '#NAME?': '0.0', 
            '#REF!': '0.0', 
            '#VALUE!': '0.0',
            '#ERROR!': '0.0',
            '': '0.0',
            '-': '0.0',
        }
        numeric_cols = ['Planned Sleeves', 'Sleeves Build', 'Not Produced Sleeves']

        for col in numeric_cols:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(',', '')
                .replace((ERROR_REPLACEMENTS))
                .astype(float)
                .astype(int)
            )

        # Special handling for Production rate % (which might also contain #DIV/0!)
        df['Production rate %'] = (
            df['Production rate %']
            .astype(str)
            .str.replace('%', '')
            .replace(ERROR_REPLACEMENTS) # **New: Replace GSheet errors and empty strings**
            .astype(float) / 100
        )
        
        # 🌟 CORRECTED: Create a display column as a float, rounded to handle floating-point issues.
        # DO NOT convert to a string here.
        df['Production rate Display'] = df['Production rate %'].round(3)
        df['Area_Line_Key'] = df['Area'] + ' - ' + df['Line']

        return df

    except Exception as e:
        st.error(f"Error loading data from Google Sheet. Check Sheet ID/Name/Permissions. Error: {e}")
        return pd.DataFrame()

# 🌟 Load Recent Scanned Data:
@st.cache_data(ttl=10) 
def load_recent_scanned_data():
    gc = get_gspread_client()
    if gc is None:
        return pd.DataFrame()
    
    try:
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(RECENT_SCANNED_SHEET_NAME) 
        data = worksheet.get_all_values()

        if not data or len(data) < 2:
            return pd.DataFrame()

        df = pd.DataFrame(data[1:], columns=data[0])
        
        df.rename(columns={
            'line': 'Line Name',
            'Process': 'Process', 
            'BELT NAME': 'Sleeve Name', 
            'Duration': 'Time Taken'
        }, inplace=True)
        
        df = df[['Line Name', 'Process', 'Sleeve Name', 'Time Taken']]

        return df

    except Exception as e:
        st.warning(f"Error loading 'Recent Scanned' data. Please ensure the sheet name '{RECENT_SCANNED_SHEET_NAME}' exists. Error: {e}")
        return pd.DataFrame()

# CACHED Function to display OPERATORS
@st.cache_data(ttl=None) 
def display_operators_cacheable(area_line_key):
    st.markdown("#### 👷 Operators")
    
    images_and_names = EMPLOYEE_IMAGES.get(area_line_key, [])

    if images_and_names:
        num_cols = min(len(images_and_names), 4)
        cols = st.columns(num_cols) 
        for i, (img_path, emp_name) in enumerate(images_and_names):
            if i < num_cols: 
                try:
                    cols[i].image(img_path, caption=emp_name, width=70) 
                except Exception:
                    cols[i].warning("Img Fail") 

        if len(images_and_names) > 4:
            st.info(f"Showing {num_cols} of {len(images_and_names)} operators for fit.")
    else:
        st.info(f"No operators listed for the current line.")


# Function to display the KPI data for a single sub-line
def display_sub_line(line_df, area_name, line_name):
    if line_df.empty:
        st.warning(f"No data to display for {area_name} - {line_name}.")
        return

    row = line_df.iloc[0]
    area_line_key = row['Area_Line_Key']

    st.markdown(f"### ⚙️**{line_name}** Line")
    
    metric_cols = st.columns(2) 
    
    planned = row["Planned Sleeves"]
    built = row["Sleeves Build"]
    
    if planned > 0:
        delta_value = built - planned
    else:
        delta_value = None

    # Get the rounded float value (1.0 for 100%)
    production_rate_value = row['Production rate Display']
    
    # 🌟 NEW: Determine the correct display string based on the value
    if production_rate_value == 1.0:
        # If the value is 1.0, show "100%" without decimals
        production_rate_display_string = "100%"
    else:
        # Otherwise, use the standard f-string formatting with one decimal place
        production_rate_display_string = f"{production_rate_value:.1%}"
    with metric_cols[0]:
        st.metric("Target", row["Planned Sleeves"])
        # 🌟 CORRECTED: Pass the rounded float to st.metric and use the f-string formatter.
        st.metric("Production Rate", production_rate_display_string)
        
    with metric_cols[1]:
        st.metric("Completed", built)
        st.metric("Pending", row["Not Produced Sleeves"]) 

    display_operators_cacheable(area_line_key)

# 🌟 Display Recent Scanned Table
def display_recent_scanned_table(df_scanned_line, process_name, count=4):
    st.markdown(f"#### {process_name}")
    
    if df_scanned_line.empty:
        st.info(f"No recent scan data found for {process_name}.")
        st.dataframe(
            pd.DataFrame(columns=['Sleeve Name', 'Time Taken']),
            use_container_width=True,
            hide_index=True
        )
        return

    df_display = df_scanned_line.tail(count).copy()
    
    df_display = df_display[['Sleeve Name', 'Time Taken']]
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )


# ⭐ EDITED: Display Dashboard for Selected Area
def display_area_kpis_only(df_area_kpi, area_name):
    line_values = df_area_kpi["Line"].unique()
    
    is_split_view = ("Building" in line_values) and ("Curing" in line_values) and area_name.startswith("Line-")

    if is_split_view:
        col_building, col_curing = st.columns([1, 1]) 
        
        df_building_kpi = df_area_kpi[df_area_kpi["Line"] == "Building"]
        df_curing_kpi = df_area_kpi[df_area_kpi["Line"] == "Curing"]

        with col_building:
            if not df_building_kpi.empty:
                display_sub_line(df_building_kpi, area_name, "Building")
            else:
                st.warning(f"No 'Building' KPI data found for {area_name}.")

        with col_curing:
            if not df_curing_kpi.empty:
                display_sub_line(df_curing_kpi, area_name, "Curing")
            else:
                st.warning(f"No 'Curing' KPI data found for {area_name}.")
        
    else:
        st.warning(f"Area **{area_name}** does not have a 'Building/Curing' split or data is missing. Displaying single line metrics.")
        
        df_single = df_area_kpi.copy() 
        
        if not df_single.empty:
            display_sub_line(df_single, area_name, df_single.iloc[0]['Line']) 
        else:
            st.error(f"No production data found for {area_name}.")


# Main App
def main():
    df_kpi = load_data() 
    df_scanned_full = load_recent_scanned_data() 
    
    selected_area = None
    area_names = df_kpi["Area"].unique().tolist() if not df_kpi.empty else []

    # Sidebar 
    with st.sidebar:

        try:
            st.image(LOGO_PATH, width=180)
        except Exception:
            st.warning("Logo not found.")

        st.markdown("---")
        st.subheader("Select Production Area")

        selected_area = option_menu(
            menu_title=None,
            options=area_names,
            icons=['map'] * len(area_names),
            default_index=0,
            styles={
                "container": {"padding": "0!important"},
                "nav-link-selected": {"background-color": "#F07D02"},
                "icon": {"color": "orange", "font-size": "18px"},
            }
        )

        st.markdown("---")

        import streamlit.components.v1 as components
        components.html(
                """
                <button id="fullscreen-btn" 
                        style="width: 30%; height: 40px; border: none; border-radius: 0.8rem; background-color: #020a1c; cursor: pointer; color: rgb(49, 51, 63); font-weight: 600;">
                    📺
                </button>
                <script>
                    const button = document.getElementById('fullscreen-btn');
                    
                    button.addEventListener('click', function() {
                        var el = window.parent.document.documentElement;
                        
                        // Toggle Fullscreen State
                        if (!document.fullscreenElement) {
                            // Enter Fullscreen
                            if (el.requestFullscreen) el.requestFullscreen();
                            else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen(); // Safari/Webkit
                        } else {
                            // Exit Fullscreen
                            if (document.exitFullscreen) document.exitFullscreen();
                        }
                    });
                </script>
                """,
                height=40, # Make the component visible to show the button
            )

        # Reset so the JS runs only once
        
    
    with st.container(): 
        
        main_content_col, recent_scans_col = st.columns([0.7, 0.3]) 
        
        
        # LEFT ZONE (TITLE, DATE/TIME, & KPIs)
        with main_content_col:
            title_col, logo_col = st.columns([0.80, 0.20]) 

            with title_col:
                if selected_area:
                     # Adjust width as needed
                    st.title(f"🏭 {selected_area} Production Overview") 
                else:
                    st.title("🏭 Production Dashboard")

            if selected_area:
                df_area_kpi = df_kpi[df_kpi["Area"] == selected_area]
                
                display_area_kpis_only(df_area_kpi, selected_area)
                
            with logo_col:
                  st.image("urbmlogo.jpg", width=250) # Keep or adjust width as needed
                  
        # RIGHT ZONE (RECENT SCANS)
        with recent_scans_col:
            
            st.markdown(
                f"""
                <div style="text-align: right; margin-top: 5px;">
                    <p style="font-size: 15px; margin: 0; line-height: 1.5; color: #aaa;">
                        <span style="color: white; font-size: 70px;">{time.strftime('%H:%M %p')}</span>
                    </p>
                    <p style="font-size: 15px; margin: 0; line-height: 1.3; color: #aaa;">
                        <span style="color: white; font-size: 25px;">{time.strftime('%d-%B-%Y')}</span>
                    </p>
                    
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown("<br><br>", unsafe_allow_html=True)

            if selected_area:
                df_scanned_area = df_scanned_full[df_scanned_full["Line Name"] == selected_area]

                df_scanned_building = df_scanned_area[df_scanned_area["Process"] == "Building"]
                df_scanned_curing = df_scanned_area[df_scanned_area["Process"] == "Curing"]
                display_recent_scanned_table(df_scanned_building, "Recently Scanned Building", count=4) 
                display_recent_scanned_table(df_scanned_curing, "Recently Scanned Curing", count=4)

        # Custom CSS
        st.markdown(
            f"""
            <style>
            
            header {{
                background-color: #010712 !important; /* Makes the top deploy bar match background */
            }}
            /* Target the container wrapping the clock. This is often the main column. */
            .block-container {{
                padding-top: 0px !important;
                padding-bottom: 0px !important;
            }}
            
            .main {{
                padding-top: 0px !important; 
                padding-right: 0px !important;
                padding-left: 0px !important;
                padding-bottom: 0px !important; 
            }}
            /* Sidebar Styling */
                section[data-testid="stSidebar"] {{
                    background-color: #010712; 
                    width: 200px !important; 
                    height: 100vh;
                }}
                section[data-testid="stSidebar"] * {{
                    color: #FFFFFF !important; /* 8. Forces all text/icons in sidebar to white */
                }}
            .stApp {{
                background-color: #010712 !important; 
            }}
            /* ADDED: Target all generated containers and element backgrounds */
                div[data-testid="stVerticalBlock"] {{
                    background-color: #010712 !important; 
                }}
                div[data-testid="stHorizontalBlock"] {{
                    background-color: #010712 !important; 
                }}
                div[data-testid="stColumn"] {{
                    background-color: #010712 !important; 
                }}
            /* Target the DataFrame container and header */
                div[data-testid="stDataFrame"] div.st-emotion-cache-1ftl41 {{ /* This is the table wrapper div */
                    background-color: #010712 !important;
                }}

                /* Target the table header row specifically (often a different shade) */
                div[data-testid="stDataFrame"] div[role="rowheader"] {{
                    background-color: #010712 !important;
                    border-color: #333333 !important; /* Keep borders visible, but dark */
                }}
                
            /* Target unselected links in the Option Menu */
                .st-emotion-cache-1cpxb1n {{ /* This class is often the nav link container */
                    background-color: #010712 !important;
                }}
            /* 2. CRITICAL: Tighten up all vertical block containers */
            .stVerticalBlock {{
                margin-top: 0px !important;
                padding-top: 0px !important;
                margin-bottom: 0px !important; /* ADDED: Removes space below the block (i.e., below the date) */
                padding-bottom: 0px !important;
            }}
            
            [data-testid="stMetricValue"] {{
                font-size: {KPI_VALUE_FONT_SIZE}px !important;
                font-weight: bold !important; 
            }}
            [data-testid="stMetricLabel"] {{
                font-size: {KPI_LABEL_FONT_SIZE}px !important; 
            }}
            /* This targets the standard Streamlit vertical block container that follows the clock.
               It is often the culprit for large vertical gaps between major sections. */
            .stVerticalBlock {{
                margin-top: 10px !important;
                padding-top: 5px !important;
            }}
            /* 3. CRITICAL: Tighten all headings */
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 10px !important;        /* EDITED: Set all top margins to 0 for maximum tightness */
                margin-bottom: 2px !important; 
                padding: 0 !important;
            }}
            /* 4. TIGHTEN: Ensure the 'Recently Scanned Building' heading (likely h3) is very tight */
            h3 {{
                margin-top: 0px !important;        /* EDITED: Ensure h3 has no top margin */
                margin-bottom: 0px !important;     /* EDITED: Ensure h3 has no bottom margin */
            }}
            
            h4 {{
                margin-top: 0px !important;
                margin-bottom: 0px !important;
            }}
            /* 5. CRITICAL: Target the paragraph containing the date/time text */
            /* The date (09-December-2025) is likely styled via st.markdown() or custom HTML. */
            .stMarkdown p {{
                margin-top: 0px !important;       /* EDITED: Changed from 2px to 0px */
                margin-bottom: 0px !important;    /* EDITED: Changed from 0px to 0px (confirming 0) */
            }}
            /* 6. Ensure the stDataFrame container is also tight */
            [data-testid="stDataFrame"] {{
                min-height: 40px !important; 
                margin-top: 0px !important;      /* ADDED: Ensures the table itself doesn't have a top margin */
                padding-top: 0px !important;
            }}
            
            .stMarkdown p {{
                margin-top: 0px !important;
                margin-bottom: 0px !important;
            }}

            .nav-link-selected {{
                background-color: #4D94FF !important;
            }}
            
            [data-testid="stVerticalBlock"] [data-testid="stMetric"] {{
                margin-bottom: 0px !important; 
                padding-bottom: 0px !important; 
            }}

            [data-testid="stVerticalBlock"] > div > [data-testid="stVerticalBlock"] {{
                gap: 0.1rem;
            }}
            
            [data-testid="stDataFrame"] {{
                min-height: 40px !important; 
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        
        st_autorefresh(interval=20 * 1000, key="production_dashboard_refresh")
    
# Run App
if __name__ == "__main__":
    main()
