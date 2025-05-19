import re
import matplotlib.pyplot as plt
import argparse
import numpy as np
import glob
import os

# avoid showing plot window
import matplotlib as mpl
from matplotlib.gridspec import GridSpec

mpl.use('Agg')

# config for 5 minutes
INTERVAL=200    # interval of drawing
WINDOW_SIZE=0  # window size to calculate avg to smoth

# 10 minutes
INTERVAL=600    # interval of drawing
WINDOW_SIZE=10  # window size to calculate avg to smoth

def parse_ptp_log(log_file):
    """
    Parses the PTP slave clock log file to extract master offset, frequency offset, and path delay.
    :param log_file: Path to the log file.
    :return: Dictionary with lists of metrics and timestamps.
    """
    # log of ptp slave is different depending "free_running" parameter
    # when free_running = 1, the output is as below
    pattern = '^(.*)ptp4l\[(.+)\]: master offset\s+(-?[0-9]+) s([012]) freq\s+([+-]\d+) path delay\s+(-?\d+)$'
    test_string = 'ptp4l[214733.206]: master offset     -28767 s0 freq  -25546 path delay    130743'

    ## this output is used when free_running = 0
    # pattern = '^(.*)ptp4l\[(.+)\]: rms\s+(-?[0-9]+) max (\d+) freq\s+([+-]\d+) .* delay\s+(-?\d+) .*$'
    # test_string = 'ptp4l[3235037.837]: rms 324564 max 326176 freq -8602326 +/-  77 delay 334763 +/-   0'
    
    data = {
        #"timestamp": [],
        "master_offset": [],
        "frequency_offset": [],
        "path_delay": []
    }
    
    # Regular expressions to match the fields
    log_pattern = re.compile(
        pattern,
        re.IGNORECASE
    )
    
    min_ts   =  0
    
    first_time = 0
    with open(log_file, "r") as file:
        for line in file:
            res = log_pattern.search(line)
            if res:
                time_and_host  = res.group(1)
                kernel_time    = res.group(2)
                master_offset  = res.group(3)
                state          = res.group(4)
                freq           = res.group(5)
                path_delay     = res.group(6)

                #shift X to the first value
                if first_time == 0:
                    first_time = float(kernel_time)
                kernel_time = float(kernel_time) - first_time
                
                # ensure that we plot only in period of [min_ts, interval+min_ts]
                if kernel_time < min_ts:
                    continue
                #kernel_time -= min_ts
                if kernel_time > INTERVAL + min_ts:
                    break
         
                master_offset = float(master_offset)
                # get absolute value
                master_offset = abs(master_offset)

                #data["timestamp"].append(int(kernel_time))
                data["master_offset"].append(master_offset/1000)
                data["frequency_offset"].append(float(freq))
                data["path_delay"].append(float(path_delay)/1000)
    
    return data


def annotate_boxplot(ax, data):
    """
    Annotates a boxplot with statistical values (mean, median, Q1, Q3).
    :param ax: Matplotlib Axes object.
    :param data: List of values for the boxplot.
    """
    stats = {
        "mean": np.mean(data),
        "median": np.median(data),
        "q1": np.percentile(data, 25),
        "q3": np.percentile(data, 75)
    }
    ax.legend([f"Mean: {stats['mean']:.2f}\n"
                f"Median: {stats['median']:.2f}\n"
                f"Q1: {stats['q1']:.2f}\n"
                f"Q3: {stats['q3']:.2f}"], loc="upper right", fontsize=10)

def moving_average(y_2d):
    #homogenous row size
    min_len = 10000
    for arr in y_2d:
        if min_len > len(arr):
            min_len = len(arr)

    new_y_2d = []
    for arr in y_2d:
        new_y_2d.append( arr[:min_len])

    #get a average row
    mean = np.mean(new_y_2d, axis=0)

    #smooth the line
    if WINDOW_SIZE > 0:
        smooth = np.convolve(mean, np.ones(WINDOW_SIZE)/WINDOW_SIZE, mode='valid')
    else:
        smooth = []
    return (mean, smooth)

CONFIG = {
        "master_offset"   : {
            "ylabel": "Clock offset (microsecond)", 
            #"yticks": [-150, -100, -50, -25, 0, 25, 50, 100, 150, 200,300]
            "yticks": [0, 25, 50, 100, 150, 200,300]
        },
        "frequency_offset": {
            "ylabel": "Frequency offset", 
        },
        "path_delay"      : {
            "ylabel": "Path delay (microsecond)",
            "yticks": [300, 350, 375, 400, 425, 450, 500]
        }
}

def line_plot_metrics(data):
    """
    :param data: Dictionary containing timestamps and metric values.
    """
    #plt.figure(figsize=(15, 12))
    #fig, ax = plt.subplots()
    
    for name in data:
        obj = data[name]
        
        for metric in obj:
            # draw only master offset
            #if metric != "master_offset":
            #    continue
            
            plt.clf()

            # Remove margins
            #plt.margins(x=0, y=0) 
            # Set global font size
            plt.rcParams.update({'font.size': 16})  # Adjust the font size

            # Create a figure
            fig = plt.figure(figsize=(12, 4), layout="constrained")
            # Define the grid layout: 1 row, 2 cols with with ratios 1:4:1
            gs = GridSpec(1, 3, figure=fig, width_ratios=[1,4,1] )

            # 1. draw lines
            line_plot = fig.add_subplot(gs[1])
            line_plot.margins(x=0, y=0) 

            flatten_arr = []
            #plt.yscale('log')  # Set Y-axis to logarithmic scale (base 10)
            for arr in obj[metric]:
                flatten_arr += arr
                line_plot.plot(range(0, len(arr)), arr, marker='o', color="green", markeredgewidth=0, alpha=1, markersize=3, linestyle='None')
            
            # a line to represent average
            y_mean, y_smooth = moving_average(obj[metric])

            line_plot.plot(range(0,len(y_mean)), y_mean, color="red", alpha=0.9)
            if WINDOW_SIZE > 0:
                line_plot.plot(range(0,len(y_smooth)), y_smooth, color="blue", linewidth=2)
            

            line_plot.set_xlabel("Timestamp (second)")

            # Manually specify y-axis ticks
            if "yticks" in CONFIG[metric]:
                yticks = CONFIG[metric]["yticks"].copy() #we will modify the array
                
                
                #ax = plt.gca()  # Get current axis
                line_plot.set_yticks( yticks )
            line_plot.set_yticklabels([]) #hide ytick labels
            line_plot.grid(True)#, color='black')
            
            # 2. draw box
            box_plot = fig.add_subplot(gs[0])
            box_plot.margins(x=0, y=0) 
            box_plot.boxplot(flatten_arr, vert=True, patch_artist=True, 
                widths=0.6,
                #labels=[""],
                boxprops=dict(color='black', facecolor='grey', alpha=0.9), 
                medianprops=dict(color='black'),
                #Change outlier size & color
                flierprops=dict(marker='o', markersize=5, color='black', alpha=0.5))

            box_plot.grid()
            box_plot.set_ylabel( CONFIG[metric]["ylabel"] )
            box_plot.set_yticks( yticks )
            #box_plot.set_yticklabels([]) #hide ytick labels
            box_plot.set_xticklabels([]) #hide ytick labels
        
            
            # 3. draw detail
            line_2_plot = fig.add_subplot(gs[2])
            line_2_plot.margins(x=0, y=0) 
            avg_data = []
            for arr in obj[metric]:
                arr = arr[0:51] # show only first X records
                avg_data.append( arr )
                line_2_plot.plot(range(0, len(arr)), arr, marker='o', color="green", markeredgewidth=0, alpha=1, markersize=3, linestyle='None')

            # a line to represent average
            y_mean, y_smooth = moving_average(avg_data)
            line_2_plot.plot(range(0,len(y_mean)), y_mean, color="red", alpha=0.9, linewidth=2)
            


            # Manually specify y-axis ticks
            if "yticks" in CONFIG[metric]:
                yticks = CONFIG[metric]["yticks"].copy() #we will modify the array
                
                #ax = plt.gca()  # Get current axis
                line_2_plot.set_yticks( yticks )
            line_2_plot.set_yticklabels([]) #hide ytick labels 
            line_2_plot.grid(True)#, color='black')
             

            plt.savefig( f"plot-{name}-{metric}-{INTERVAL}-detail.pdf", dpi=30, format='pdf', bbox_inches='tight')


if __name__ == "__main__":
    extension = ".json.slave.log"
    # Set up command-line argument parsing
    log_files = ["1-switch", "2-switches", "5-switches", "10-switches", "20-switches"]
    #log_files = ["20-switches"]
    print(log_files)
    data = dict()
    
    for name in log_files:
        data[name] = {}

        #for i in range(0, 10):
        for i in range(1, 21):
        #for i in range(1, 3):
            log_file = f"./topos-{i}/{name}{extension}"

            if not os.path.exists( log_file ):
                continue

            print(f"parsing {log_file}")

            # Parse the log file
            obj = parse_ptp_log(log_file)
            for metric in obj:
                if metric not in data[name]:
                    data[name][metric] = []
                arr = obj[metric]
                if len(arr):
                    data[name][metric].append( arr )

    # Plot the metrics
    if len(data):
        line_plot_metrics(data)
        #box_plot_metrics(data)
    else:
        print("No valid data found in the log file.")
