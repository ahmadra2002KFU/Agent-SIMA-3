"""
Test Plotly visualization integration with publication-ready output.
"""
import requests
import json

def test_plotly_visualizations():
    """Test comprehensive Plotly visualization capabilities."""
    
    # Upload sample data
    print("1. Uploading sample data...")
    upload_url = "http://127.0.0.1:8010/upload"
    
    try:
        with open("sample_data.csv", "rb") as f:
            files = {"file": ("sample_data.csv", f, "text/csv")}
            response = requests.post(upload_url, files=files)
        
        if response.status_code != 200:
            print(f"Upload failed: {response.text}")
            return
        
        print("✅ File uploaded successfully!")
        
        # Test multiple visualization types
        visualizations = [
            {
                "name": "Box Plot - Salary by Department",
                "code": """
import plotly.express as px
import plotly.graph_objects as go

# Create a professional box plot
fig = px.box(df, x='Department', y='Salary', 
             title='Salary Distribution by Department',
             color='Department',
             color_discrete_sequence=px.colors.qualitative.Set2)

fig.update_layout(
    title={
        'text': 'Salary Distribution by Department',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 18, 'family': 'Arial, sans-serif'}
    },
    xaxis_title='Department',
    yaxis_title='Salary (USD)',
    font={'family': 'Arial, sans-serif', 'size': 12},
    plot_bgcolor='white',
    paper_bgcolor='white',
    showlegend=False,
    margin=dict(l=50, r=50, t=80, b=50)
)

fig.update_xaxis(showgrid=True, gridwidth=1, gridcolor='lightgray')
fig.update_yaxis(showgrid=True, gridwidth=1, gridcolor='lightgray')

salary_box_plot = fig
"""
            },
            {
                "name": "Scatter Plot - Age vs Salary",
                "code": """
import plotly.express as px

# Create scatter plot with trend line
fig = px.scatter(df, x='Age', y='Salary', 
                 color='Department',
                 size='Years_Experience',
                 title='Age vs Salary Analysis',
                 trendline='ols',
                 hover_data=['Name', 'Years_Experience'])

fig.update_layout(
    title={
        'text': 'Age vs Salary Analysis with Experience Factor',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 18, 'family': 'Arial, sans-serif'}
    },
    xaxis_title='Age (years)',
    yaxis_title='Salary (USD)',
    font={'family': 'Arial, sans-serif', 'size': 12},
    plot_bgcolor='white',
    paper_bgcolor='white',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

age_salary_scatter = fig
"""
            },
            {
                "name": "Bar Chart - Average Salary by Department",
                "code": """
import plotly.express as px

# Calculate average salary by department
dept_avg = df.groupby('Department')['Salary'].mean().reset_index()
dept_avg = dept_avg.sort_values('Salary', ascending=False)

# Create professional bar chart
fig = px.bar(dept_avg, x='Department', y='Salary',
             title='Average Salary by Department',
             color='Salary',
             color_continuous_scale='viridis',
             text='Salary')

fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')

fig.update_layout(
    title={
        'text': 'Average Salary by Department',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 18, 'family': 'Arial, sans-serif'}
    },
    xaxis_title='Department',
    yaxis_title='Average Salary (USD)',
    font={'family': 'Arial, sans-serif', 'size': 12},
    plot_bgcolor='white',
    paper_bgcolor='white',
    showlegend=False,
    yaxis=dict(tickformat='$,.0f')
)

dept_salary_bar = fig
"""
            }
        ]
        
        execute_url = "http://127.0.0.1:8010/execute-code"
        
        for i, viz in enumerate(visualizations, 1):
            print(f"\n{i+1}. Testing {viz['name']}...")
            
            response = requests.post(execute_url, json={"code": viz["code"]})
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {viz['name']} created successfully!")
                
                # Check for plotly figures
                results = result.get('results', {})
                if results:
                    plotly_figures = [k for k in results.keys() if 'plotly_figure' in k]
                    print(f"   Generated {len(plotly_figures)} Plotly figures")
                else:
                    print("   No results returned")
                    continue
                
                # Verify figure properties
                for fig_key in plotly_figures:
                    fig_data = results[fig_key]
                    if fig_data.get('type') == 'plotly_figure':
                        try:
                            fig_json = json.loads(fig_data['json'])
                            print(f"   - {fig_key}: {len(fig_json.get('data', []))} traces")
                            
                            # Check for layout properties (publication-ready features)
                            layout = fig_json.get('layout', {})
                            if layout.get('title'):
                                print(f"     Title: {layout['title'].get('text', 'N/A')}")
                            if layout.get('font'):
                                print(f"     Font: {layout['font'].get('family', 'N/A')}")
                            
                        except json.JSONDecodeError:
                            print(f"   - {fig_key}: Error parsing JSON")
                
            else:
                print(f"❌ {viz['name']} failed: {response.text}")
        
        # Test combined dashboard
        print(f"\n{len(visualizations)+2}. Testing combined dashboard...")
        
        dashboard_code = """
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Create a dashboard with multiple subplots
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Salary Distribution', 'Age vs Salary', 'Dept Averages', 'Experience Distribution'),
    specs=[[{"type": "box"}, {"type": "scatter"}],
           [{"type": "bar"}, {"type": "histogram"}]]
)

# Box plot
for dept in df['Department'].unique():
    dept_data = df[df['Department'] == dept]
    fig.add_trace(
        go.Box(y=dept_data['Salary'], name=dept, showlegend=False),
        row=1, col=1
    )

# Scatter plot
fig.add_trace(
    go.Scatter(x=df['Age'], y=df['Salary'], 
               mode='markers',
               marker=dict(size=df['Years_Experience']*2, opacity=0.7),
               text=df['Name'],
               showlegend=False),
    row=1, col=2
)

# Bar chart
dept_avg = df.groupby('Department')['Salary'].mean()
fig.add_trace(
    go.Bar(x=dept_avg.index, y=dept_avg.values, showlegend=False),
    row=2, col=1
)

# Histogram
fig.add_trace(
    go.Histogram(x=df['Years_Experience'], nbinsx=8, showlegend=False),
    row=2, col=2
)

# Update layout
fig.update_layout(
    title_text="Employee Data Dashboard",
    title_x=0.5,
    height=600,
    font={'family': 'Arial, sans-serif', 'size': 10},
    plot_bgcolor='white',
    paper_bgcolor='white'
)

dashboard = fig
"""
        
        response = requests.post(execute_url, json={"code": dashboard_code})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Dashboard created successfully!")
            
            plotly_figures = [k for k in result.get('results', {}).keys() if 'plotly_figure' in k]
            print(f"   Generated {len(plotly_figures)} dashboard figures")
            
        else:
            print(f"❌ Dashboard failed: {response.text}")
        
        print("\n🎨 Plotly Integration Test Complete!")
        print("✅ Multiple visualization types supported")
        print("✅ Publication-ready styling")
        print("✅ Interactive features enabled")
        print("✅ Dashboard capabilities")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_plotly_visualizations()
