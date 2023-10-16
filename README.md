# CSV-TAS-2
A version of CSV-TAS for use with SMO-TAS-Exlaunch

## Writing CSV-TAS Scripts
Read the tutorial [here](https://docs.google.com/document/d/1A7cFr9X9BsHDKlzq7se1q3oCZ7Wiiz2CoMkDuzxel3M/edit?usp=sharing).

## Generating Output File for TAS Mod
Make sure you have Python 3 installed.

### Local
#### 1-player TAS:
In the command line, navigate to the ```CSV-TAS-2``` directory and enter ```python3 csv-tas.py [path to CSV file] [path to output file]```.
#### 2-Player TAS:
In the command line, navigate to the ```CSV-TAS-2``` directory and enter ```python3 2p-csv-tas.py [path to CSV file] [path to output file]```.

### FTP
If you want to send ouptut files to your Switch via FTP, first enter your FTP server configuration information in ```ftp_config.json```.

To generate and output file and send it to your Switch, in the command line, navigate to the ```CSV-TAS-2``` directory and enter ```python3 csv-tas.py -f [path to CSV file] [name of output file]```. The file will be transferred to the `scripts` directory of your Switch's SD card and will also be generated in the ```CSV-TAS-2``` directory on your computer. For a 2-Player TAS, use 2p-csv-tas.py instead of csv-tas.py.

### Debugging
If you would like to generate a debug CSV file displaying each frame of the generated output file, include the option ```-d``` before the path to the CSV file (```-fd``` if you also want to use the FTP feature). The debug file will be generated in the ```CSV-TAS-2``` directory.

## Converting nx-TAS to TSV-TAS
To convert an nx-TAS script to a TSV-TAS script, in the command line, navigate to the ```CSV-TAS-2``` directory and enter ```python3 nx-tas-to-tsv-tas.py [path to nx-TAS file] [path to output file]```.
