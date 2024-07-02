import streamlit as st
import pandas as pd
import plotly.express as px

def check_date_format(date_str, format):
    try:
        pd.to_datetime(date_str, format=format)
        return True
    except ValueError:
        return False

def filter_campaigns_by_city(campaign_names, city_name):
    filtered_campaigns = [campaign for campaign in campaign_names if city_name.lower() in campaign.lower()]
    return filtered_campaigns

def plot_and_save_pi_chart(data, column, title):
    fig = px.pie(data, names=column, title=title, hole=0.2)
    fig.update_traces(textinfo='percent+label')
    return fig

def plot_and_save_line_chart(data, x_column, y_columns, title, xlabel, ylabel):
    grouped_data = data.groupby(x_column)[y_columns].sum().reset_index()
    fig = px.line(grouped_data, x=x_column, y=y_columns, title=title, labels={x_column: xlabel, 'value': ylabel})
    return fig

# Streamlit UI
st.title('Porter Data Mapping Tool')

# Unnecessary columns to drop
columns_to_drop = ['Diposition', 'Requested At', 'Event count', 'Source', 'Source Detail', 
                   'PnM_parameter', 'Not Interested Reason', 'Not Interested Reason (Others)', 
                   'House Shifting Opportunity: Owner Name', 'First Disposition Time', 'TAT_Mins', 
                   'Material Form Filled', 'Callback Requested', 'Order Interest Form Count', 
                   'House Shifting Opportunity: ID', 'Geo Region', 'Drop Address', 'Disposition', 
                   'House Shifting Opportunity: Name', 'House Type', 'House Shifting Date', 
                   'How did you know about Porter?', 'Sessions', 'Engaged sessions']

# Upload CSV files
ga_dumb_file = st.file_uploader("Upload GA Dump CSV", type="csv")
report_file = st.file_uploader("Upload SF Report CSV", type="csv")
mapping_ref_file = st.file_uploader("Upload Mapping Reference CSV", type="csv")

if ga_dumb_file and report_file and mapping_ref_file:
    # Read CSV files
    ga_dumb = pd.read_csv(ga_dumb_file)
    report = pd.read_csv(report_file, encoding='latin-1')
    mapping_ref = pd.read_csv(mapping_ref_file)

    # Preprocess data
    ga_dumb = ga_dumb.dropna(axis='columns', how='all')
    ga_dumb = ga_dumb.dropna(axis='rows', how='all')
    report = report.dropna(axis='columns', how='all')
    report = report.dropna(axis='rows', how='all')

    # Extract mobile number and format date from 'ga_dumb' DataFrame
    if 'PnM_parameter' in ga_dumb:
        ga_dumb['Mobile'] = ga_dumb['PnM_parameter'].str.extract(r'(\d{10})')

    ga_dumb = ga_dumb.drop_duplicates(subset=['Mobile'])

    report.rename(columns={'House Shifting Opportunity: Created Date': 'Date'}, inplace=True)
    ga_dumb['Date'] = pd.to_datetime(ga_dumb['Date'].astype(str), format='%Y%m%d').dt.strftime('%d-%m-%Y')

    # Ensure 'Date' column in report DataFrame is of string type
    report['Date'] = report['Date'].astype(str)

    if check_date_format(report['Date'].iloc[0], '%d/%m/%Y'):
        report['Date'] = pd.to_datetime(report['Date'], format='%d/%m/%Y').dt.strftime('%d-%m-%Y')

    # Ensure 'Date' column in ga_dumb DataFrame is of string type
    ga_dumb['Date'] = ga_dumb['Date'].astype(str)
    report['Mobile'] = report['Mobile'].astype(str)

    # Drop unnecessary columns
    for col in columns_to_drop:
        if col in ga_dumb.columns:
            ga_dumb.drop(col, axis=1, inplace=True)

    for col in columns_to_drop:
        if col in report.columns:
            report.drop(col, axis=1, inplace=True)

    # Merge dataframes
    mapped_data_inner = ga_dumb.merge(report, on=['Mobile', 'Date'], how='inner')
    
    # Convert 'Date' column to datetime
    mapped_data_inner['Date'] = pd.to_datetime(mapped_data_inner['Date'], format='%d-%m-%Y')

    # Get unique campaign names
    campaign_names = mapped_data_inner['First user Google Ads campaign'].unique()
    Order_status = mapped_data_inner['Status'].unique()

    # Filter by cities
    my_cities = 'Mumbai|Delhi|NCR|Pune|Kolkata|Ahmedabad|Nagpur|Jaipur|Lucknow|Indore|Surat'
    mapped_data_inner = mapped_data_inner[mapped_data_inner['First user Google Ads campaign'].str.contains('Packers', case=False)]
    mapped_data_inner = mapped_data_inner[mapped_data_inner['First user Google Ads campaign'].str.contains(my_cities, case=False)]

    # Merge with mapping reference file
    mapped_data_inner = mapped_data_inner.merge(mapping_ref, left_on='First user Google Ads campaign', right_on='Campaign', how='left')
    mapped_data_inner.drop(columns=['Campaign'], inplace=True)

    # Mark Conversions
    mapped_data_inner.loc[mapped_data_inner['Status'] == 'Converted', 'SF_Conv'] = 1
    mapped_data_inner.loc[mapped_data_inner['Status'] != 'Converted', 'SF_Conv'] = 0

    # Mark Leads
    mapped_data_inner['SF_Leads'] = 1

    # Mark Inter_city Leads
    mapped_data_inner.loc[mapped_data_inner['Shifting Type'] == 'inter_city', 'Intercity_Leads'] = 1
    mapped_data_inner.loc[mapped_data_inner['Shifting Type'] != 'inter_city', 'Intercity_Leads'] = 0

    # Mark Inter_City Conversions
    mapped_data_inner.loc[(mapped_data_inner['Shifting Type'] == 'inter_city') & (mapped_data_inner['Status'] == 'Converted'), 'Intercity_Conv'] = 1
    mapped_data_inner.loc[(mapped_data_inner['Shifting Type'] != 'inter_city') | (mapped_data_inner['Status'] != 'Converted'), 'Intercity_Conv'] = 0

    # Mark Intra_City Leads
    mapped_data_inner.loc[mapped_data_inner['Shifting Type'] == 'intra_city', 'Intracity_Leads'] = 1
    mapped_data_inner.loc[mapped_data_inner['Shifting Type'] != 'intra_city', 'Intracity_Leads'] = 0

    # Mark Intra_City Conversions
    mapped_data_inner.loc[(mapped_data_inner['Shifting Type'] == 'intra_city') & (mapped_data_inner['Status'] == 'Converted'), 'Intracity_Conv'] = 1
    mapped_data_inner.loc[(mapped_data_inner['Shifting Type'] != 'intra_city') | (mapped_data_inner['Status'] != 'Converted'), 'Intracity_Conv'] = 0

    # Initialize session state variables if they don't exist
    if 'filtered_data' not in st.session_state:
        st.session_state['filtered_data'] = None

    if 'show_custom_data' not in st.session_state:
        st.session_state['show_custom_data'] = False

    if 'show_visualizations' not in st.session_state:
        st.session_state['show_visualizations'] = False

    Get_Custom_Data = st.button(label='Get Custom Data')
    Get_Full_Mapped_data = st.button(label='Get Full Mapped Data')

    if Get_Custom_Data:
        st.session_state['show_custom_data'] = True
        st.session_state['show_visualizations'] = False

    if Get_Full_Mapped_data:
        st.session_state['filtered_data'] = mapped_data_inner
        st.session_state['show_custom_data'] = False
        st.session_state['show_visualizations'] = False

    if st.session_state['show_custom_data']:
        # Streamlit form for input
        with st.form(key='filter_form'):
            city_name = st.text_input('Enter City Name', key='city_name')
            if city_name:
                filtered_campaigns = filter_campaigns_by_city(campaign_names, city_name)
                selected_campaigns = st.multiselect(
                    'Select Campaigns',
                    options=campaign_names,
                    default=filtered_campaigns,
                    key='campaigns'
                )
            else:
                selected_campaigns = st.multiselect(
                    'Select Campaigns',
                    options=campaign_names,
                    key='campaigns'
                )

            start_date = st.date_input('Start Date', key='start_date')
            end_date = st.date_input('End Date', key='end_date')
            status = st.multiselect('Select Status', Order_status, key='status')

            # Submit button
            submit_button = st.form_submit_button(label='Filter Data')

        if submit_button:
            # Filter data based on user input
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)

            filtered_data = mapped_data_inner[
                (mapped_data_inner['First user Google Ads campaign'].isin(selected_campaigns)) &
                (mapped_data_inner['Date'] >= start_date) &
                (mapped_data_inner['Date'] <= end_date)
            ]

            if status:
                filtered_data = filtered_data[filtered_data['Status'].isin(status)]

            st.write(f'Number of records: {len(filtered_data)}')
            st.dataframe(filtered_data)
            st.session_state['filtered_data'] = filtered_data
            st.session_state['show_visualizations'] = False

    if st.session_state['filtered_data'] is not None:
        st.session_state['show_visualizations'] = True

        # Download filtered data
        csv = st.session_state['filtered_data'].to_csv(index=False)
        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name='filtered_data.csv',
            mime='text/csv',
        )

    if st.session_state['show_visualizations']:
        Get_Visualizations = st.button('Get Visualizations')

        if Get_Visualizations:
            st.header("Visualizations")

            if st.session_state['filtered_data'] is not None:
                data_to_visualize = st.session_state['filtered_data']
                st.subheader("Filtered Data Visualizations")
            else:
                data_to_visualize = mapped_data_inner
                st.subheader("Full Mapped Data Visualizations")

            # Display and save visualizations
            pie_all_leads = plot_and_save_pi_chart(data_to_visualize[(data_to_visualize['Date'].dt.month == 6)], 'City', 'Distribution of Leads by City')
            st.plotly_chart(pie_all_leads)

            intercity_leads_data = data_to_visualize[data_to_visualize['Intercity_Leads'] == 1 & 
                                                    (data_to_visualize['Date'].dt.month == 6)]
            pie_intercity_leads = plot_and_save_pi_chart(intercity_leads_data, 'City', 'Distribution of Intercity Leads by City')
            st.plotly_chart(pie_intercity_leads)

            intercity_conv_data = data_to_visualize[(data_to_visualize['Intercity_Conv'] == 1) & 
                                                    (data_to_visualize['Date'].dt.month == 6)]
            pie_intercity_conv = plot_and_save_pi_chart(intercity_conv_data, 'City', 'Distribution of Intercity Conversions by City')
            st.plotly_chart(pie_intercity_conv)
                        
            line_fig = plot_and_save_line_chart(data_to_visualize[(data_to_visualize['Date'].dt.month == 6)], 'Date', ['SF_Leads', 'SF_Conv'], 
                                                'Leads and Conversions Over Time', 'Date', 'Count')
            st.plotly_chart(line_fig)
            
    if Get_Full_Mapped_data:
        # Show full mapped data
        st.dataframe(mapped_data_inner)

        # Download full mapped data
        csv = mapped_data_inner.to_csv(index=False)
        st.download_button(
            label="Download Full Mapped Data as CSV",
            data=csv,
            file_name='full_mapped_data.csv',
            mime='text/csv',
        )
