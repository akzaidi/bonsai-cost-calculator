import pandas as pd
from bs4 import BeautifulSoup
from urllib.request import urlopen
import json
import time
import requests

columns_to_show = [
    "name",
    "numberOfCores",
    # "osDiskSizeInMB",
    # "resourceDiskSizeInMB",
    # "maxDataDiskCount",
    "memoryInMB",
    "linuxPrice",
    "windowsPrice",
    "regionId",
    "pricePerMemoryLinux",
    "pricePerMemoryWindows",
    "pricePerCoreLinux",
    "pricePerCoreWindows",
    "bestPriceRegion",
]


def get_table(region: str = "eastus", low_pri: bool = True, host_os: str = "linux"):

    azure_price_url = (
        "https://azureprice.net/"
        + "?region="
        + region
        + "&?priority="
        + str(low_pri).lower()
    )
    print(azure_price_url)

    html = urlopen(azure_price_url)
    soup = BeautifulSoup(html, "html.parser")
    body_script = soup.find("body").script
    body_script_contents = body_script.contents

    table_str = str(body_script_contents)
    b = table_str[17:-11]

    if host_os == "linux":
        drop_os = "windows"
    else:
        drop_os = "linux"
    regex_os = "(?i)" + drop_os

    table_df = pd.DataFrame(json.loads(b))
    table_df = table_df[columns_to_show]
    table_df = table_df[table_df.columns.drop(list(table_df.filter(regex=regex_os)))]
    return table_df


def calculate_price(
    low_pri_df: pd.DataFrame,
    dedicated_df: pd.DataFrame,
    num_simulators: int = 100,
    low_pri_num: int = 10,
    dedicated_num: int = 1
    # num_brains: int = 10,
):

    low_pri_cost = low_pri_df.price.min() * num_simulators * low_pri_num
    dedicated_cost = dedicated_df.price.min() * num_simulators * dedicated_num

    total_cost = low_pri_cost + dedicated_cost
    return total_cost


if __name__ == "__main__":

    print(get_table("westus").head())
    # pass
