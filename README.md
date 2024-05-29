# Specialized-chart-for-manual-and-algorithmic-traders
Trend-Following Algorithm: Python app using TA indicators for market trend analysis. Features live &amp; historical data, GUI with Tkinter, and DTW for trend similarity detection.
# Trend-Following Algorithm

This repository contains a Python application implementing a trend-following algorithm with Dynamic Time Warping (DTW) similarity detection.

## Description

The application fetches market data, applies a trend-following algorithm to identify market trends, and uses DTW to find the most similar historical trends. The results are displayed in a graphical user interface (GUI) built with Tkinter.

## Features

- Fetches historical and live market data.
- Applies a trend-following algorithm using technical indicators.
- Identifies the top 3 most similar historical trends using DTW.
- Displays the results in a user-friendly GUI.

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/your-username/trend-following-algorithm.git

2.	Navigate to the project directory:

	cd trend-following-algorithm
	
3.	Install the required dependencies:

	pip install -r requirements.txt

Run the application:

python script_name.py


- Enter the asset symbol and click “Show Trends” to fetch and analyze market data.
Dependencies

	•	pandas
	•	numpy
	•	talib
	•	tkinter
	•	ibapi
	•	dexscreener
	•	dtw
	•	tradingview_ta
	•	tradingview_widget
License

This project is licensed under the MIT License - see the LICENSE file for details.
