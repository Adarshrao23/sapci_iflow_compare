# sapci_iflow_compare

This Streamlit application allows users to connect, extract and compare two SAP Cloud Integration (CI) iFlow XML files.  
It identifies configuration and logic differences by matching elements with the same `id` and recursively comparing all elements.  
The app also integrates with Google Gemini to generate a human-readable summary of the differences.

---

## 🚀 Features

- Compare two iFlow XML files from SAP CPI environments
- Match elements by `id` and ignore order differences
- Recursively compare all XML elements (attributes, text, structure)
- Display raw technical differences in a readable format
- Generate AI-powered summary using Google Gemini
- Download raw difference report

---

## 🛠️ Setup Instructions

### Option 1: Clone the repository

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Adarshrao23/sapci_iflow_compare.git
   cd your-repo-name

### Option 2: Manual Copy
1. **Open Visual Studio Code (or your preferred editor)**
2. **Create a new file named iflow_compare.py**
3. **Copy and paste the code from this repository into iflow_compare.py**

### Install dependencies
1. ***Make sure you have Python 3.8+ installed***
2. ***Install required packages using pip:***
   ```bash
   pip3 install streamlit lxml requests
---
## ⚙️ Usage
1. ***Provide API details for both iFlows (manual entry or via config file)***
2. ***Enter your Gemini API URL and Key for AI summarization***
3. ***Run the app:***
    ```bash
    python3 -m streamlit run iflow_compare.py
---
4. ***Click "Compare iFlows" to fetch, extract, and compare the XMLs***
5. ***View technical differences and download the raw report***
6. ***See the Gemini summary for a readable, grouped overview of changes***

## 📝 Configuration
You can use a JSON config file with the following structure:
```json
{
  "api1": {
    "name": "Source iFlow Name",
    "url": "https://source-api-url",
    "oauth_token_url": "https://source-oauth-url",
    "client_id": "source-client-id",
    "client_secret": "source-client-secret"
  },
  "api2": {
    "name": "Target iFlow Name",
    "url": "https://target-api-url",
    "oauth_token_url": "https://target-oauth-url",
    "client_id": "target-client-id",
    "client_secret": "target-client-secret"
  },
  "gemini_api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
  "gemini_api_key": "your-gemini-api-key"
}
```

## 🤖 Gemini Integration
1. ***The app sends the raw difference report to Google Gemini for summarization***
2. ***The summary is displayed in a separate section for easy review***

## 📄 License
MIT License

## 🙋 Support
For issues, suggestions, or contributions, please open an issue or pull request on GitHub.

