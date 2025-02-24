import re
import matplotlib.pyplot as plt
import argparse
import numpy as np
import glob
import os

# avoid showing plot window
import matplotlib as mpl
mpl.use('Agg')



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
    
    min_ts   =  50
    #interval = 300
    interval = 3600
    
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
                if kernel_time > interval + min_ts:
                    break
         
                #data["timestamp"].append(int(kernel_time))
                data["master_offset"].append((float(master_offset))/1000)
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

    window_size = 10
    if min_len > 500:
        window_size = 100

    #smooth the line
    smooth = np.convolve(mean, np.ones(window_size)/window_size, mode='valid')
    return (mean, smooth)

CONFIG = {
        "master_offset"   : {
            "ylabel": "Clock offset (microsecond)", 
            "yticks": [-150, -100, -50, -25, 0, 25, 50, 100, 150]
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
            plt.clf()

            # Remove margins
            plt.margins(x=0, y=0) 
            
        
            max_val = 0
            min_val = 100*1000*1000*1000
            #plt.yscale('log')  # Set Y-axis to logarithmic scale (base 10)
            for arr in obj[metric]:
                v = min(arr)
                if v < min_val:
                    min_val = v
                v = max(arr)
                if v > max_val:
                    max_val = v
                    
                plt.plot(range(0, len(arr)), arr, marker='o', color="green", markeredgewidth=0, alpha=0.5, markersize=3, linestyle='None')
            
            # a line to represent average
            y_mean, y_smooth = moving_average(obj[metric])

            plt.plot(range(0,len(y_mean)), y_mean, color="blue", alpha=0.9)
            plt.plot(range(0,len(y_smooth)), y_smooth, color="red")
            

            plt.xlabel("Timestamp (second)")
            plt.ylabel( CONFIG[metric]["ylabel"] )


            # Manually specify y-axis ticks
            if "yticks" in CONFIG[metric]:
                yticks = CONFIG[metric]["yticks"].copy() #we will modify the array
                
                yticks[0]  = int(min_val - 1)
                yticks[-1] = int(max_val + 1)
                
                ax = plt.gca()  # Get current axis
                ax.set_yticks( yticks )
            
    
            plt.tight_layout()
            plt.grid()
            plt.savefig( f"plot-{name}-{metric}.pdf", dpi=30, format='pdf', bbox_inches='tight')

def flatten( arr ):
    ret = []
    for val in arr:
        val = val[30:] # exclude the "calibration period"
        ret += val
    return ret


log_file_labels = {
    "1-switch"   : "1 TC", 
    "2-switches" : "2 TCs", 
    "5-switches" : "5 TCs", 
    "10-switches": "10 TCs", 
    "20-switches": "20 TCs"
    }
    
def box_plot_metrics(data):
    """
    Plots the master offset, frequency offset, and path delay metrics along with boxplots.
    :param data: Dictionary containing timestamps and metric values.
    """
    #plt.figure(figsize=(15, 12))
    #fig, ax = plt.subplots()
    for metric in CONFIG:
        plt.clf()
        
        #plt.yscale('log')  # Set Y-axis to logarithmic scale (base 10)

        labels = []
        arr    = []
        # each log
        for name in data:
            labels.append( log_file_labels[name] )
            val = data[name][metric]
            
            val = flatten( val )
            arr.append( val )
        # Boxplot for Master Offset (Vertical)
        box = plt.boxplot(arr, vert=True, patch_artist=True, labels=labels, boxprops=dict(color='black', facecolor='grey', alpha=0.9), medianprops=dict(color='black'),
            #Change outlier size & color
            flierprops=dict(marker='o', markersize=5, color='black', alpha=0.5))
        #plt.title("Master Offset Distribution")

        plt.ylabel( CONFIG[metric]["ylabel"] )

        # Manually specify y-axis ticks
        if "yticks" in CONFIG[metric]:
            ax = plt.gca()  # Get current axis
            ax.set_yticks( CONFIG[metric]["yticks"] )

        plt.tight_layout()
        plt.grid()
        plt.savefig( f"plot-{metric}.pdf", dpi=30, format='pdf', bbox_inches='tight')


if __name__ == "__main__":
    extension = ".json.slave.log"
    # Set up command-line argument parsing
    log_files = ["1-switch", "2-switches", "5-switches", "10-switches", "20-switches"]
    #log_files = ["1-switch"]
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
        box_plot_metrics(data)
    else:
        print("No valid data found in the log file.")
