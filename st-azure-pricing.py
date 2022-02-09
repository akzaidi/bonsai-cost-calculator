"""
Title: Azure Batch Pricing App
Author: Ali Zaidi
Version: -0.0.1
TODO:
    - [ ] provide some footnotes on needed resources, i.e., for ACI:
        - `az provider register -n Microsoft.ContainerInstance --subscription {{subscription id}} `
        - for azure batch:
        - `az provider register -n Microsoft.Batch --subscription {{subscription id}}`
    - allow for more than one simulator per node
    - additional metadata:
        - SKU summary
        - pool summary
    - add ACR pricing
    - [x] ensure same SKU is used for both dedicated and low_pri
    - [x] any chance to include discounts based on Azure commitment levels [probably a different API altogether] `wontdo` - non-general mechanics
    - [x] from price per hour, let's get to price per eap:
        - cost_per_hour * num_hours_eap 
        - num_hours_eap = num_brains / (num_episodes)
        - num_iterations_per_episode
    - [x] how to distribute:
        - @Aydan: pyinstaller -> executable -> share -> profit?
QUESTIONS:
    - @Aydan: how to calculate cost for the entire project
    - @Nick: backfit from dollar amount -> number of iterations / number of brains
    - @Aydan: go from # brains / # concepts 
    - @Nick: export to CSV
    - @Matt: any provisions for redundancy / resiliency?
"""

import base64
import os
from math import floor
from typing import Tuple

import pandas as pd
import streamlit as st
from PIL import Image

from get_azure_data import get_table, get_date_fetched

st.set_page_config(layout="wide")


st.title("ACT Now! Estimated Azure Costing Tool for Bonsai Experiments")
pd.set_option("display.float_format", lambda x: "%.3f" % x)


@st.cache
def load_image(img):
    im = Image.open(os.path.join(img))
    return im


st.image(load_image("imgs/bonsai-logo.png"), width=70)

st.markdown(
    """_This is a simple calculator for the cost of running Azure Batch Jobs with [`bonsai-batch`](https://github.com/microsoft/bonsai-batch)._ It relies on the public pricing information available on [azureprice.net](https://azureprice.net/)."""
)

st.markdown(
    """
    From the left _sidebar_, please select the region in which you expect to run Azure Batch jobs. \n
    Please also input your simulator-speed, as well as the number of low-priority virtual machines and dedicated virtual machines you plan to use.
    """
)


region_selectbox = st.sidebar.selectbox(
    "Which region will you use for batch?",
    (
        "westus",
        "westus2",
        "eastus",
        "eastus2",
        "westeurope",
        "southcentralus",
        "centralus",
    ),
)

os_selectbox = st.sidebar.selectbox("Which OS will you be using?", ("windows", "linux"))

sim_speed = st.sidebar.number_input(
    "Simulator speed for a single instance (it / s)",
    value=1.000,
    min_value=0.000,
    max_value=500.000,
    format="%.4f",
)

num_cores = st.sidebar.slider(
    "Number of cores needed to run a single instance of the simulator",
    min_value=int(1),
    max_value=int(32),
    value=int(2),
)

gpu_needed = st.sidebar.selectbox(
    "Type of GPU needed for simulations",
    options=["None", "NC-series", "NV-series", "Either"],
    index=0,
)

memory = st.sidebar.number_input(
    "Memory needed per container (GB)",
    min_value=0.50,
    max_value=32.0,
    value=1.0,
    step=0.5,
)

desired_iterations = st.sidebar.number_input(
    "Desired #iterations per experiment",
    value=int(100000),
    min_value=int(1000),
    max_value=int(100000000),
    step=1000,
)


@st.cache(allow_output_mutation=True)
def load_data(
    region: str,
    memory: float = memory,
    num_cores: int = num_cores,
    gpu_needed: str = gpu_needed,
) -> Tuple[pd.Series, pd.Series]:

    # print("getting data for {}".format(region))
    # print("os: {}".format(os_selectbox))
    low_pri_df = get_table(region=region, low_pri=True, host_os=os_selectbox)
    dedicated_df = get_table(region=region, low_pri=False, host_os=os_selectbox)

    if gpu_needed == "NC-series":
        low_pri_df = low_pri_df[low_pri_df["VM Name"].str.contains("NC")]
        dedicated_df = dedicated_df[dedicated_df["VM Name"].str.contains("NC")]
        if low_pri_df.shape[0] == 0:
            raise ValueError(
                f"No NC-series VMs available in {region}. Please try westus2, southcentral, or eastus"
            )
    elif gpu_needed == "NV-series":
        low_pri_df = low_pri_df[low_pri_df["VM Name"].str.contains("NV")]
        dedicated_df = dedicated_df[dedicated_df["VM Name"].str.contains("NV")]
        if low_pri_df.shape[0] == 0:
            raise ValueError(
                f"No NV-series VMs available in {region}. Please try westus2, southcentral, or eastus"
            )

    if os_selectbox == "linux":
        low_pri_df["Price"] = low_pri_df["Linux Cost"].astype(float)
        dedicated_df["Price"] = dedicated_df["Linux Cost"].astype(float)
    else:
        low_pri_df["Price"] = low_pri_df["Windows Cost"].astype(float)
        dedicated_df["Price"] = dedicated_df["Windows Cost"].astype(float)

    low_pri_df = low_pri_df[
        (low_pri_df.vCPUs.astype("float") >= num_cores)
        & (low_pri_df["Memory (GiB)"].astype("float") >= memory)
        & (low_pri_df.Price.astype("float") > 0)
    ]

    dedicated_df = dedicated_df[
        (dedicated_df.vCPUs.astype("float") >= num_cores)
        & (dedicated_df["Memory (GiB)"].astype("float") >= memory)
        & (dedicated_df.Price.astype("float") > 0)
    ]

    return low_pri_df, dedicated_df


low_pri_df, dedicated_df = load_data(region=region_selectbox)

# cheapest_vms = low_pri_df.

# Calculate Pricing:

st.markdown(
    """
    ## Estimated Cost Per Experiment:  
    """
)

# expected time to reach desired iterations at single sim speed:
time_one_sim = desired_iterations / sim_speed


def get_time_to_reach(sim_time, sim_pad: bool = True):

    hours_time = sim_time / (60 * 60)

    if hours_time > 24:
        formatted_time = hours_time / 24
        units = "days"
    elif (hours_time < 1) and (hours_time >= (1 / 60)):
        formatted_time = hours_time * 60
        units = "minutes"
    elif hours_time < 1 / 60:
        formatted_time = sim_time
        units = "seconds"
    else:
        formatted_time = hours_time
        units = "hours"

    if sim_pad:
        padding = "sim-"
    else:
        padding = ""

    return f"{formatted_time:,.2f} {padding}{units}"


st.markdown(
    f"* In order to reach {desired_iterations:,} iterations, you'll need **{get_time_to_reach(time_one_sim)}** to complete training."
)

desired_nodes = st.slider(
    "Max number of instances for training", min_value=10, max_value=750, value=50
)


time_scaled_seconds = time_one_sim / desired_nodes
time_scaled_hours = time_scaled_seconds / (60 * 60)

st.markdown(
    f"* With {desired_nodes} running simulators, your time to {desired_iterations:,} iterations is **{get_time_to_reach(time_scaled_seconds, False)}**."
)


st.markdown("### Selecting VM SKU:")

st.markdown(
    "Let's also select a ratio for low priority virtual machines to dedicated virtual machines. Low-priority virtual machines are significantly discounted from dedicated virtual machines (often a third or fourth of the price) but can be pre-empted during peak demand."
)

low_pri_perc = st.slider(
    "Low priority virtual machines to dedicated virtual machines ratio",
    min_value=0.0,
    max_value=1.0,
    value=0.1,
)

low_pri_nodes = floor(low_pri_perc * desired_nodes)
dedicated_nodes = desired_nodes - low_pri_nodes

st.markdown(
    f"You've selected to run {low_pri_nodes} low-priority nodes and {dedicated_nodes} dedicated nodes."
)


def filter_df(input_df):

    output_df = input_df
    # output_df["memory"] = output_df["Memory (GiB)"]
    # output_df = output_df.query(f"vCPUs >= {num_cores} and Memory (GiB) >= {memory}")
    output_df = output_df[
        (output_df["vCPUs"] >= num_cores) & (output_df["Memory (GiB)"] >= memory)
    ]
    output_df = output_df.sort_values("Price", ascending=True)

    return output_df


def join_df(df1, df2):

    df2 = df2[["VM Name", "Price"]]
    joined_df = df1.merge(
        df2, on="VM Name", how="left", suffixes=[" (Low Pri)", " (Dedicated)"]
    )
    return joined_df


low_pri2_df = filter_df(low_pri_df)
ded2_df = filter_df(dedicated_df)
joined_df = join_df(low_pri2_df, ded2_df)

best_sku = joined_df["VM Name"][0]
low_price = joined_df["Price (Low Pri)"][0]
ded_price = joined_df["Price (Dedicated)"][0]
best_loc = joined_df["Best price region / Diff"][0].split(" / ")
total_cost = (low_price * time_scaled_hours * low_pri_nodes) + (
    ded_price * time_scaled_hours * dedicated_nodes
)

st.markdown(
    f"In {region_selectbox}, the best price for a {num_cores}-core machine with {memory} GB RAM is a **{best_sku}** VM which costs ${low_price}/hour for one low-priority VM and ${ded_price}/hour for one dedicated VM. Your cost will be **{best_loc[1]}** lower if you instead use __{best_loc[0]}__."
)

date_fetched = get_date_fetched()
st.markdown(
    f"""
## Total Cost Projection:
Your total cost in {region_selectbox} is **${total_cost:,.2f}**.
\n**Note**: {date_fetched}.
"""
)

st.dataframe(
    joined_df[
        [
            "VM Name",
            "Price (Low Pri)",
            "Price (Dedicated)",
            "vCPUs",
            "Memory (GiB)",
            "Best price region / Diff",
        ]
    ].style.set_precision(2)
)


def download_link(object_to_download, download_filename, download_link_text):
    """
    Generates a link to download the given object_to_download.

    object_to_download (str, pd.DataFrame):  The object to be downloaded.
    download_filename (str): filename and extension of file. e.g. mydata.csv, some_txt_output.txt
    download_link_text (str): Text to display for download link.

    Examples:
    download_link(YOUR_DF, 'YOUR_DF.csv', 'Click here to download data!')
    download_link(YOUR_STRING, 'YOUR_STRING.txt', 'Click here to download your text!')

    """
    if isinstance(object_to_download, pd.DataFrame):
        object_to_download = object_to_download.to_csv(index=False)

    # some strings <-> bytes conversions necessary here
    b64 = base64.b64encode(object_to_download.encode()).decode()

    return f'<a href="data:file/txt;base64,{b64}" download="{download_filename}">{download_link_text}</a>'


st.markdown("## Download Cost Summary")
df = pd.DataFrame(
    {
        "Region": region_selectbox,
        "Best Region": best_loc[0],
        "Price Diff %": best_loc[1],
        "SKU": best_sku,
        "Price (Low Pri)": low_price,
        "Price (Dedicated)": ded_price,
        "Desired VMs": desired_nodes,
        "Desired Iterations": desired_iterations,
        "Total Cost ($)": total_cost,
    },
    index=[0],
)

# Examples

st.write(df)

if st.button("Download Dataframe as CSV"):
    tmp_download_link = download_link(
        df, "cost.csv", "Click here to download your data!"
    )
    st.markdown(tmp_download_link, unsafe_allow_html=True)

