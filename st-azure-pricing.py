"""
Title: Azure Batch Pricing App
Author: Ali Zaidi
Version: -0.0.1
TODO:
    - [ ] provide some footnotes on needed resoureces, i.e., for ACI:
        - `az provider register -n Microsoft.ContainerInstance --subscription {{subscription id}} `
        - for azure batch:
        - `az provider register -n Microsoft.Batch --subscription {{subscription id}}`
    - allow for more than one simulator per node
"""

import pandas as pd
import streamlit as st
import os
from math import ceil
from get_azure_data import get_table, calculate_price
from PIL import Image

st.title("Azure Pricing Calculator for Azure Batch")
pd.set_option("display.float_format", lambda x: "%.3f" % x)

st.subheader(
    "[Ali Zaidi](https://github.com/akzaidi) @ [Bonsai](https://www.bons.ai/), Microsoft AI and Research"
)


@st.cache
def load_image(img):
    im = Image.open(os.path.join(img))
    return im


st.image(load_image("imgs/bonsai-logo.png"), width=70)

st.markdown(
    """_This is a simple calculator for running Azure Batch Jobs with [`cs-batch-orchestration`](https://github.com/BonsaiAI/cs-batch-orchestration)_"""
)

st.markdown(
    """
    From the left _sidebar_, please select the region in which you expect to run Azure Batch jobs. \n
    Please also input your simulator-speed, as well as the number of low-priority virtual machines and dedicated virtual machines you plan to use.
    """
)

region_selectbox = st.sidebar.selectbox(
    "Which region will you use for batch?",
    ("westus", "westus2", "eastus", "eastus2", "westeurope", "centralus"),
)

os_selectbox = st.sidebar.selectbox("Which OS will you be using?", ("windows", "linux"))

sim_speed = st.sidebar.number_input(
    "Simulator speed for a single instance (it / s)",
    value=10.0,
    min_value=0.0,
    max_value=500.0,
)

num_cores = st.sidebar.slider(
    "Number of cores needed to run a single instance of the simulator",
    min_value=int(1),
    max_value=int(32),
    value=int(2),
)

memory = st.sidebar.number_input(
    "Memory needed per container (GB)", min_value=0.25, max_value=32.0, value=1.0
)

num_low_pri = st.sidebar.number_input(
    "Number of low-priority virtual machines",
    value=int(10),
    min_value=int(0),
    max_value=int(1000),
)

num_dedicated_pri = st.sidebar.number_input(
    "Number of dedicated virtual machines",
    value=int(1),
    min_value=int(0),
    max_value=int(1000),
)


@st.cache
def load_data(region, memory: float = memory, num_cores: int = num_cores):

    # print("getting data for {}".format(region))
    # print("os: {}".format(os_selectbox))
    low_pri_df = get_table(region=region, low_pri=True, host_os=os_selectbox)
    dedicated_df = get_table(region=region, low_pri=False, host_os=os_selectbox)

    if os_selectbox == "linux":
        low_pri_df["price"] = low_pri_df["linuxPrice"]
        dedicated_df["price"] = dedicated_df["linuxPrice"]
    else:
        low_pri_df["price"] = low_pri_df["windowsPrice"]
        dedicated_df["price"] = dedicated_df["windowsPrice"]

    low_pri_df = low_pri_df[
        (low_pri_df.numberOfCores >= num_cores)
        & (low_pri_df.memoryInMB >= memory * 1024)
        & (low_pri_df.price > 0)
    ]

    dedicated_df = dedicated_df[
        (dedicated_df.numberOfCores >= num_cores)
        & (dedicated_df.memoryInMB >= memory * 1024)
        & (dedicated_df.price > 0)
    ]

    return low_pri_df, dedicated_df


low_pri_df, dedicated_df = load_data(region=region_selectbox)

# Calculate Pricing:


st.markdown(
    """
    ## Estimated Cost Per Hour:  
    Here we estimate the cost for running Azure Batch Jobs for an Hour
    """
)

desired_hz = st.slider(
    "Desired iteration speed (it / s): ", min_value=10.0, max_value=5000.0, value=100.0
)

sims_needed = ceil(desired_hz / sim_speed)

sub_section_cost = "### Hourly Cost for Running {} simulators: ".format(sims_needed)

st.markdown(sub_section_cost)

total_nodes = num_low_pri + num_dedicated_pri
if total_nodes <= sims_needed:
    needed_low_pri = sims_needed - num_dedicated_pri
    st.text(
        "WARNING: You've asked for a total of {} machines but need {} to run this many simulators".format(
            total_nodes, sims_needed
        )
    )
else:
    needed_low_pri = num_low_pri

low_pri_nodes_needed = min(sims_needed - num_dedicated_pri, num_low_pri)
desired_cost = calculate_price(low_pri_df, dedicated_df, num_low_pri, num_dedicated_pri)
actual_cost = calculate_price(
    low_pri_df, dedicated_df, needed_low_pri, num_dedicated_pri
)

st.text(
    "You asked to run {} simulators, this will cost ${} per hour".format(
        total_nodes, round(desired_cost, 2)
    )
)


# print out subsection with azure tables


st.markdown(
    """
    ## Low Priority Virtual Machines: 
    """
)
low_pri_df

st.markdown(
    """
    ## Dedicated Virtual Machines: 
    """
)

dedicated_df
