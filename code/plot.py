import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Put the paths to your 6 CSV files in this list
csv_files = [
    # 'mev.csv', 'gas_waste.csv', 'lat.csv', 
    # 'slip.csv', 'act.csv', 'exp.csv'
    'exp.csv'
]

# Define your custom non-linear scale mapping here
y_ticks_orig = [0, 50000, 500000, 5000000, 50000000]
y_ticks_mapped = [0, 1, 2, 3, 4]

for file in csv_files:
    if not os.path.exists(file):
        print(f"File {file} not found. Skipping...")
        continue
        
    # Read the CSV 
    # (add header=None if your CSV doesn't have column names in the first row)
    df = pd.read_csv(file)
    
    # Transpose the data: columns become X-axis groups, rows become side-by-side bars
    df_transposed = df.T
    
    # Create a copy of the dataframe to hold the interpolated/mapped values
    df_mapped = df_transposed.copy()
    
    # Apply np.interp to every column to map the original data to the new scale
    for col in df_mapped.columns:
        df_mapped[col] = np.interp(df_mapped[col], y_ticks_orig, y_ticks_mapped)
    
    # Create the grouped bar chart using the MAPPED data
    ax = df_mapped.plot(kind='bar', figsize=(4, 3.75), width=0.3)
    
    # Customize the graph
    plt.title(f'Expected payoff (in token B)')
    plt.xlabel('')
    plt.ylabel('Values (in token B)')
    
    # Override the Y-axis ticks and labels
    # We place ticks at the mapped locations (0, 1, 2, 3, 4) 
    # but display the original values (0, 100, 300, 1200, 1500) as the text labels
    plt.yticks(y_ticks_mapped, y_ticks_orig)
    
    # Set the legend (assuming 2 rows of data)
    plt.legend(['Continuos', 'Batched'], title='Data Rows')
    
    # Keep the X-axis labels horizontal
    plt.xticks(rotation=0) 
    
    # Adjust layout so labels don't get cut off
    plt.tight_layout()
    
    # Save the graph as a PNG image file
    output_filename = f"{os.path.splitext(file)[0]}_graph.png"
    plt.savefig(output_filename)
    
    # Close the plot to free up memory before moving to the next file
    plt.close()
    
    print(f"Saved graph for {file} as {output_filename}")

print("All graphs generated successfully!")