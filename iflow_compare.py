import streamlit as st
import json
import requests
import zipfile
import io
import re
import html
from lxml import etree


def get_oauth_token(token_url, client_id, client_secret):
    data = {"grant_type": "client_credentials"}
    response = requests.post(token_url, data=data, auth=(client_id, client_secret))
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"OAuth token error: {response.status_code} {response.text}")


def download_and_extract_iflw(api_url, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        zip_bytes = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_bytes, "r") as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.endswith(".iflw"):
                    with zip_ref.open(file_name) as iflw_file:
                        return iflw_file.read()
        raise Exception("No .iflw file found in the zip archive.")
    else:
        raise Exception(
            f"Failed to download iFlow zip: {response.status_code} {response.text}"
        )


def remove_xml_declaration(xml_bytes):
    xml_str = xml_bytes.decode("utf-8")
    xml_str = re.sub(r"^<\?xml[^\>]+\?>\s*", "", xml_str)
    return xml_str


def pretty_path(path):
    import re

    return re.sub(r"\{[^}]+\}", "", path)


def compare_elements(e1, e2, path="/", api1_name="API 1", api2_name="API 2"):
    id1 = e1.attrib.get("id")
    id2 = e2.attrib.get("id")
    n1 = e1.attrib.get("name", "")
    n2 = e2.attrib.get("name", "")
    extra = f" (id={id1 or id2}, name={n1 or n2})" if id1 or id2 or n1 or n2 else ""
    differences = []

    if id1 and id2 and id1 == id2:
        if e1.attrib != e2.attrib:
            differences.append(
                f"{pretty_path(path)}{extra}: Attributes differ -\n  {api1_name}: {e1.attrib}\n  {api2_name}: {e2.attrib}"
            )
        text1 = (e1.text or "").strip()
        text2 = (e2.text or "").strip()
        if text1 != text2:
            differences.append(
                f"{pretty_path(path)}{extra}: Text differs -\n  {api1_name}: '{text1}'\n  {api2_name}: '{text2}'"
            )
        children1 = list(e1)
        children2 = list(e2)
        id_map1 = {
            child.attrib["id"]: child for child in children1 if "id" in child.attrib
        }
        id_map2 = {
            child.attrib["id"]: child for child in children2 if "id" in child.attrib
        }
        for cid in set(id_map1.keys()).union(id_map2.keys()):
            if cid not in id_map1:
                differences.append(
                    f"{pretty_path(path)}/{cid}: Present in {api2_name} but missing in {api1_name}"
                )
            elif cid not in id_map2:
                differences.append(
                    f"{pretty_path(path)}/{cid}: Present in {api1_name} but missing in {api2_name}"
                )
            else:
                differences.extend(
                    compare_elements(
                        id_map1[cid],
                        id_map2[cid],
                        f"{path}/{id_map1[cid].tag.split('}')[-1]}[id={cid}]",
                        api1_name,
                        api2_name,
                    )
                )
        children1_noid = [child for child in children1 if "id" not in child.attrib]
        children2_noid = [child for child in children2 if "id" not in child.attrib]
        if len(children1_noid) != len(children2_noid):
            differences.append(
                f"{pretty_path(path)}{extra}: Number of child elements without id differ - {api1_name}: {len(children1_noid)}, {api2_name}: {len(children2_noid)}"
            )
        else:
            for i, (c1, c2) in enumerate(zip(children1_noid, children2_noid)):
                child_path = f"{path}/{c1.tag.split('}')[-1]}[{i}]"
                differences.extend(
                    compare_elements(c1, c2, child_path, api1_name, api2_name)
                )
        return differences

    if id1 and not id2:
        differences.append(
            f"{pretty_path(path)}: Element with id={id1} present in {api1_name} but not in {api2_name}"
        )
    if id2 and not id1:
        differences.append(
            f"{pretty_path(path)}: Element with id={id2} present in {api2_name} but not in {api1_name}"
        )

    if e1.tag != e2.tag:
        differences.append(
            f"{pretty_path(path)}: Tag differs - {api1_name}: {e1.tag.split('}')[-1]}, {api2_name}: {e2.tag.split('}')[-1]}"
        )
    if e1.attrib != e2.attrib:
        differences.append(
            f"{pretty_path(path)}{extra}: Attributes differ -\n  {api1_name}: {e1.attrib}\n  {api2_name}: {e2.attrib}"
        )
    text1 = (e1.text or "").strip()
    text2 = (e2.text or "").strip()
    if text1 != text2:
        differences.append(
            f"{pretty_path(path)}{extra}: Text differs -\n  {api1_name}: '{text1}'\n  {api2_name}: '{text2}'"
        )
    children1 = list(e1)
    children2 = list(e2)
    if len(children1) != len(children2):
        differences.append(
            f"{pretty_path(path)}{extra}: Number of child elements differ - {api1_name}: {len(children1)}, {api2_name}: {len(children2)}"
        )
    else:
        for i, (c1, c2) in enumerate(zip(children1, children2)):
            child_path = f"{path}/{c1.tag.split('}')[-1]}[{i}]"
            differences.extend(
                compare_elements(c1, c2, child_path, api1_name, api2_name)
            )
    return differences


def run_detailed_xml_comparison(xml1_str, xml2_str, api1_name, api2_name):
    parser = etree.XMLParser(remove_blank_text=True)
    tree1 = etree.fromstring(xml1_str.encode("utf-8"), parser)
    tree2 = etree.fromstring(xml2_str.encode("utf-8"), parser)
    return compare_elements(tree1, tree2, "/", api1_name, api2_name)


def call_gemini(prompt, gemini_api_url, gemini_api_key):
    headers = {"Content-Type": "application/json", "X-goog-api-key": gemini_api_key}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(gemini_api_url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Gemini error: {response.text}"


def clean_markdown(text):
    return text.replace("**", "").replace("*", "")


def get_config_from_file(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    return config


def get_config_from_ui():
    st.header("API 1 (Source iFlow)")
    api1 = {
        "name": st.text_input("iFlow 1 Name", key="api1_name"),
        "url": st.text_input("API 1 URL", key="api1_url"),
        "oauth_token_url": st.text_input("API 1 OAuth Token URL", key="api1_token_url"),
        "client_id": st.text_input("API 1 Client ID", key="api1_client_id"),
        "client_secret": st.text_input(
            "API 1 Client Secret", type="password", key="api1_client_secret"
        ),
    }
    st.header("API 2 (Target iFlow)")
    api2 = {
        "name": st.text_input("iFlow 2 Name", key="api2_name"),
        "url": st.text_input("API 2 URL", key="api2_url"),
        "oauth_token_url": st.text_input("API 2 OAuth Token URL", key="api2_token_url"),
        "client_id": st.text_input("API 2 Client ID", key="api2_client_id"),
        "client_secret": st.text_input(
            "API 2 Client Secret", type="password", key="api2_client_secret"
        ),
    }
    st.header("Gemini API")
    gemini_api_url = st.text_input("Gemini API URL", key="gemini_api_url")
    gemini_api_key = st.text_input(
        "Gemini API Key", type="password", key="gemini_api_key"
    )
    return {
        "api1": api1,
        "api2": api2,
        "gemini_api_url": gemini_api_url,
        "gemini_api_key": gemini_api_key,
    }


st.markdown(
    """
    <div style='background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(10,110,209,0.08); padding: 1.5em; margin-bottom: 2em; text-align: center;'>
    <h1 style='color: #0a6ed1; font-size: 2.2em; font-weight: 700; margin-bottom: 0.2em;'>
    SAP Cloud Integration
    </h1>
    <h3 style='color: #0a6ed1; font-size: 1.3em; font-weight: 600; margin-bottom: 0.2em;'>
    iFlow Comparison
    </h3>
    <p style='color: #6a6d70; font-size: 1.1em; margin-top: 0.5em;'>Compare iFlows from the same or different SAP CI environments with ease</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f3f6f8; /* SAP Fiori background */
        background-image: none;
    }
    .stButton button, .stDownloadButton button {
        background-color: #0a6ed1 !important; /* SAP blue */
        color: #fff !important;
        border-radius: 4px;
        border: none;
        font-weight: 600;
        padding: 0.5em 1.5em;
        box-shadow: 0 2px 8px rgba(10,110,209,0.08);
        transition: background 0.2s;
    }
    .stButton button:hover, .stDownloadButton button:hover {
        background-color: #0854a0 !important; /* SAP blue dark */
        color: #fff !important;
    }
    .stTextInput>div>input {
        background-color: #fff;
        border: 1px solid #d3dae6;
        border-radius: 4px;
        padding: 0.5em;
    }
    .stRadio>div>label {
        font-weight: 600;
        color: #0a6ed1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
input_method = st.radio(
    "How do you want to provide input?", ("Config file", "Manual entry")
)
config = None
run_comparison = False
if input_method == "Config file":
    config_path = st.text_input("Config file path", "config_file.json")
    if st.button("Compare iFlows (Config file)"):
        try:
            config = get_config_from_file(config_path)
            st.success("Config File loaded successfully!")
            run_comparison = True
        except Exception as e:
            st.error(f"Failed to load Config File: {e}")
elif input_method == "Manual entry":
    config = get_config_from_ui()
    if all(
        [
            config["api1"]["name"],
            config["api1"]["url"],
            config["api1"]["oauth_token_url"],
            config["api1"]["client_id"],
            config["api1"]["client_secret"],
            config["api2"]["name"],
            config["api2"]["url"],
            config["api2"]["oauth_token_url"],
            config["api2"]["client_id"],
            config["api2"]["client_secret"],
            config["gemini_api_url"],
            config["gemini_api_key"],
        ]
    ):
        if st.button("Compare iFlows (Manual entry)"):
            run_comparison = True
    else:
        st.warning("Please fill in all fields to proceed.")

if run_comparison and config:
    try:
        with st.spinner("Fetching OAuth tokens and downloading iFlows..."):
            token1 = get_oauth_token(
                config["api1"]["oauth_token_url"],
                config["api1"]["client_id"],
                config["api1"]["client_secret"],
            )
            token2 = get_oauth_token(
                config["api2"]["oauth_token_url"],
                config["api2"]["client_id"],
                config["api2"]["client_secret"],
            )
            xml1_bytes = download_and_extract_iflw(config["api1"]["url"], token1)
            xml2_bytes = download_and_extract_iflw(config["api2"]["url"], token2)
            xml1 = remove_xml_declaration(xml1_bytes)
            xml2 = remove_xml_declaration(xml2_bytes)
    except Exception as e:
        st.error(f"Error during download or extraction: {e}")
        st.stop()

    with st.spinner("Comparing iFlows..."):
        api1_name = config["api1"]["name"] or "API 1"
        api2_name = config["api2"]["name"] or "API 2"
        differences = run_detailed_xml_comparison(xml1, xml2, api1_name, api2_name)
        if not differences:
            st.success("There are no differences in the iFlows")
        else:
            differences_str = "\n\n".join(differences)
            st.subheader(f"Detailed XML Differences ({api1_name} vs {api2_name})")
            st.text_area("Differences", differences_str, height=400)
            st.download_button(
                "Download raw differences",
                differences_str,
                file_name="iflow_detailed_differences.txt",
            )

            # Gemini summary section
            with st.spinner("Sending differences to Gemini for summarization..."):
                prompt = (
                    f"Below are the technical differences between two SAP CI iFlow XMLs: '{api1_name}' and '{api2_name}'.\n"
                    "List only the differences as clear bullet points. "
                    "Do not include any introductory or closing sentences. "
                    "Focus on configuration, logic, and connectivity. Ignore diagram layout or formatting changes.\n"
                    "Here are the differences:\n"
                    f"{differences_str}"
                )
                summary = call_gemini(
                    prompt, config["gemini_api_url"], config["gemini_api_key"]
                )
            summary = html.unescape(summary)
            summary = clean_markdown(summary)
            st.subheader(f"Gemini Summary of Differences ({api1_name} vs {api2_name})")
            st.text_area("Gemini Summary", summary, height=400)
