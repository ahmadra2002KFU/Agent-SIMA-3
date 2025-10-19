import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime


df = pd.read_csv("DR0486 - Emergency Visits Report.csv")
# Convert time columns to datetime
df['Arrival time to DEM'] = pd.to_datetime(df['Arrival time to DEM'], errors='coerce')
df['DR Exam Date/Time'] = pd.to_datetime(df['DR Exam Date/Time'], errors='coerce')

# Calculate waiting time in minutes
df['Waiting_Time_Minutes'] = (df['DR Exam Date/Time'] - df['Arrival time to DEM']).dt.total_seconds() / 60

# Filter out invalid waiting times (negative or extremely large)
valid_data = df[(df['Waiting_Time_Minutes'] >= 0) & (df['Waiting_Time_Minutes'] <= 1440)]  # Max 24 hours

# Extract hour of arrival
valid_data['Arrival_Hour'] = valid_data['Arrival time to DEM'].dt.hour

# Group by arrival hour to see average waiting times
hourly_stats = valid_data.groupby('Arrival_Hour').agg({
    'Waiting_Time_Minutes': ['mean', 'median', 'count']
}).round(2)
hourly_stats.columns = ['Mean_Wait_Minutes', 'Median_Wait_Minutes', 'Patient_Count']
hourly_stats = hourly_stats.reset_index()

# Calculate correlation between arrival hour and waiting time
correlation = valid_data['Arrival_Hour'].corr(valid_data['Waiting_Time_Minutes'])

# Create visualization
fig = make_subplots(rows=2, cols=1, 
                   subplot_titles=('Average Waiting Time by Arrival Hour', 'Patient Volume by Arrival Hour'))

# Waiting time chart
fig.add_trace(go.Scatter(x=hourly_stats['Arrival_Hour'], 
                        y=hourly_stats['Mean_Wait_Minutes'],
                        mode='lines+markers',
                        name='Mean Wait Time',
                        line=dict(color='red', width=2)), row=1, col=1)

# Patient count chart
fig.add_trace(go.Bar(x=hourly_stats['Arrival_Hour'], 
                    y=hourly_stats['Patient_Count'],
                    name='Patient Count',
                    marker_color='blue'), row=2, col=1)

fig.update_xaxes(title_text="Arrival Hour (24-hour format)", row=1, col=1)
fig.update_xaxes(title_text="Arrival Hour (24-hour format)", row=2, col=1)
fig.update_yaxes(title_text="Minutes", row=1, col=1)
fig.update_yaxes(title_text="Number of Patients", row=2, col=1)

fig.update_layout(height=800, title_text="Emergency Department: Arrival Time vs Waiting Time Analysis")

# Summary statistics
result = {
    'correlation_coefficient': round(correlation, 3),
    'average_waiting_time_minutes': round(valid_data['Waiting_Time_Minutes'].mean(), 1),
    'median_waiting_time_minutes': round(valid_data['Waiting_Time_Minutes'].median(), 1),
    'total_patients_analyzed': len(valid_data),
    'hourly_breakdown': hourly_stats.to_dict('records')
}

fig.show()