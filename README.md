# PQCCN-strongswan
pq-strongswan wrapper for data collection and analysis. Advancing IKEv2 for the Quantum Age: Challenges in Post-Quantum Cryptography Implementation on Constrained Network

For full documentation refer to the <a target="_blank" rel="noreferrer noopener" href="https://jfluhler.github.io/PQCCN-strongswan/">Project Github Pages</a>

# Quick Setup Guide

The data-collection part of this project operates like a wrapper to the
[strongX509/pq-strongswan](https://github.com/strongX509/docker/tree/master/pq-strongswan)
docker container. However, there are some modification from the pq-strongswan base repository. 
We want to specially note that the work by [Andreas Steffen](https://github.com/strongX509) in making the pq-strongswan repo was of great help in starting this project. The core of his efforts are at the core of this project.

## Before you start

The following pre-requisites that are required to use this project.
- Docker
- Python 3

## Setup

Let's walk through building the docker container and installing required python modules.


1. Open a terminal console
2. Optional: Navigate to the pq-strongswan folder and build the image manually.Use the command: `docker build -t strongx509/pq-strongswan:latest .`
   > If the image `strongx509/pq-strongswan:latest` does not exist in the local Docker host, Docker will automatically attempt to pull it from Docker Hub. This is also reliable.
3. Install Python dependencies: `pip install numpy python-on-whales pyyaml tqdm`
   > If you are using a Python virtual environment, be sure to activate that environment before installing the modules.
   > You can also try running `pip install -r settings.txt`.
4. Run `python3 ./Orchestration.py` and manually specify the log storage script and test configuration file
   The test configuration files are located at `/data_collection/configs/*.yaml`

***You did it! The required resources are now installed!***


License: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>
