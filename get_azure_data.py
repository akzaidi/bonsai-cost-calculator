from urllib.request import Request, urlopen

import pandas as pd
from bs4 import BeautifulSoup


def get_table(
    region: str = "eastus", low_pri: bool = True, host_os: str = "linux"
) -> pd.DataFrame:
    """Retrieves a table of VM prices from https://azureprice.net/ for provided
    region, OS and priority
    
    Parameters
    ----------
    region : str, optional
        [description], by default "eastus"
    low_pri : bool, optional
        [description], by default True
    host_os : str, optional
        [description], by default "linux"
    
    Returns
    -------
    pd.DataFrame
    """

    azure_price_url = "https://azureprice.net/" + "?region=" + region

    if low_pri:
        azure_price_url += "&tier=low"
    else:
        azure_price_url += "&tier=standard"

    hdr = {"User-Agent": "Mozilla/5.0"}
    req = Request(azure_price_url, headers=hdr)
    html = urlopen(req)

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    headings = [th.get_text().strip() for th in table.find("tr").find_all("th")]
    table_body = soup.find("tbody")
    data_list = []

    rows = table_body.find_all("tr")
    for row in rows:
        data_list.append([x.get_text() for x in row.find_all("td")])
    data_df = pd.DataFrame(data_list, columns=headings)
    table_df = data_df.drop(columns=data_df.columns.to_list()[-2])

    if host_os == "linux":
        drop_os = "windows"
    else:
        drop_os = "linux"
    regex_os = "(?i)" + drop_os

    table_df = table_df[table_df.columns.drop(list(table_df.filter(regex=regex_os)))]
    table_df[["vCPUs", "Memory (GiB)"]] = table_df[["vCPUs", "Memory (GiB)"]].apply(
        pd.to_numeric
    )
    return table_df


def get_date_fetched(region: str = "eastus", low_pri: bool = True) -> str:

    azure_price_url = "https://azureprice.net/" + "?region=" + region

    if low_pri:
        azure_price_url += "&tier=low"
    else:
        azure_price_url += "&tier=standard"

    hdr = {"User-Agent": "Mozilla/5.0"}
    req = Request(azure_price_url, headers=hdr)
    html = urlopen(req)

    soup = BeautifulSoup(html, "html.parser")

    p_txt = [x.get_text() for x in soup.find_all("p")]
    time_str = [x for x in p_txt if "updated" in x][0]

    return time_str


def calculate_price(
    low_pri_df: pd.DataFrame,
    dedicated_df: pd.DataFrame,
    # num_simulators: int = 100,
    low_pri_num: int = 10,
    dedicated_num: int = 1
    # num_brains: int = 10,
) -> float:
    """Calculates the price per hour for given dedicated an low priority node combination
    
    Calculation is simply the sum of the lowest VM price for dedicated
    and low priority nodes, multiplied by the number of instances
    TODO: 
        * allow user to provide number of instances per machine
        * i.e., divide total_nodes / (num_sims_per_node)

    Parameters
    ----------
    low_pri_df : pd.DataFrame
        [description]
    dedicated_df : pd.DataFrame
        [description]
    low_pri_num : int, optional
        [description], by default 10
    dedicated_num : int, optional
        [description], by default 1#num_brains:int=10

    Returns
    -------
    float
        Total cost per hour
    """

    low_pri_cost = low_pri_df.price.min() * low_pri_num
    dedicated_cost = dedicated_df.price.min() * dedicated_num

    total_cost = low_pri_cost + dedicated_cost
    return total_cost


def get_aci_pricing():

    aci_url = "https://azure.microsoft.com/en-us/pricing/details/container-instances/"
    # aci_calculator_url = "https://azure.microsoft.com/en-us/pricing/calculator/?service=container-instances"
    html = urlopen(aci_url)
    soup = BeautifulSoup(html, "html.parser")
    body_script = soup.find("body").script
    body_script_contents = body_script.contents

    return body_script_contents


if __name__ == "__main__":

    # print(get_date_fetched())
    # print(get_table("westus").head())
    get_aci_pricing()
