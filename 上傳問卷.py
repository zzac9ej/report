from flask import Flask, request, jsonify, render_template_string
import csv
import json
from io import StringIO
import chardet
import requests
import webbrowser
from threading import Timer

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>問卷生成與上傳</title>
    <style>
        body {
            display: flex;
            flex-direction: row;
            align-items: flex-start;
            justify-content: flex-start;
        }
        #form-container {
            width: 40%;
            margin-right: 20px;
        }
        #questionnaire {
            width: 60%;
            border: 1px solid #ccc;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div id="form-container">
        <h2>問卷生成與上傳</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <label>上傳 CSV 檔案：</label>
            <input type="file" name="file" accept=".csv" />
            <button type="submit">上傳並生成問卷</button>
        </form>
        {% if error %}
        <div style="color: red; margin-top: 10px;">{{ error }}</div>
        {% endif %}
        <form action="/upload_to_server" method="post">
            <input type="hidden" name="questionnaire" value='{{ questionnaire_json }}' />
            <button type="submit">上傳問卷到伺服器</button>
        </form>
    </div>
    <div id="questionnaire">
        {% if questionnaire %}
        <h3>問卷內容：</h3>
        <pre>{{ questionnaire }}</pre>
        {% endif %}
    </div>
</body>
</html>
"""

FHIR_SERVER_URL = "https://hapi.fhir.tw/fhir/Questionnaire"

def parse_csv(file_content):
    csv_reader = csv.DictReader(StringIO(file_content))
    questions = []
    type_mapping = {
        "字串": "string",
        "多選": "choice",
        "boolean": "boolean",
        "range": "choice"  # 使用 `choice` 表示范围
    }
    for row in csv_reader:
        if row.get("linkId") and row.get("text") and row.get("type"):
            question = {
                "linkId": row["linkId"].strip(),
                "text": row["text"].strip(),
                "type": type_mapping.get(row["type"].strip(), row["type"].strip())
            }

            # 如果是选择类型，添加选项
            if question["type"] == "choice" and row.get("options"):
                question["answerOption"] = [
                    {"valueCoding": {"code": opt.strip(), "display": opt.strip()}}
                    for opt in row["options"].split(",")
                ]
            
            # 为 integer 类型添加额外信息
            if question["type"] == "integer":
                question["inputType"] = "number"  # 这是关键元数据，前端需要用到
            
            questions.append(question)
    return {
        "resourceType": "Questionnaire",
        "id": "GeneratedQuestionnaire",
        "status": "active",  # Add a default status field
        "item": questions
    }




@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE, questionnaire=None, questionnaire_json="")

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template_string(HTML_TEMPLATE, questionnaire=None, questionnaire_json="", error="No file provided.")

    file = request.files['file']
    if file.filename == '':
        return render_template_string(HTML_TEMPLATE, questionnaire=None, questionnaire_json="", error="No file selected.")

    try:
        # Automatically detect encoding
        raw_content = file.read()
        detected_encoding = chardet.detect(raw_content)['encoding']
        if not detected_encoding:
            return "Unable to detect file encoding.", 400

        file_content = raw_content.decode(detected_encoding)
        questionnaire = parse_csv(file_content)
        questionnaire_json = json.dumps(questionnaire, ensure_ascii=False, indent=2)
        return render_template_string(
            HTML_TEMPLATE,
            questionnaire=questionnaire_json,
            questionnaire_json=json.dumps(questionnaire)
        )
    except UnicodeDecodeError:
        return "File encoding error. Unable to decode the file.", 400
    except Exception as e:
        return f"Error processing file: {e}", 500

@app.route('/upload_to_server', methods=['POST'])
def upload_to_server():
    questionnaire = request.form.get("questionnaire")
    if not questionnaire:
        return "No questionnaire data provided.", 400

    try:
        questionnaire_json = json.loads(questionnaire)

        # 打印调试信息
        print("Uploading JSON:")
        print(json.dumps(questionnaire_json, indent=2, ensure_ascii=False))

        # 上传到 FHIR 服务器
        response = requests.post(
            FHIR_SERVER_URL,
            json=questionnaire_json,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        # 将服务器返回的 JSON 排版整齐
        response_json = response.json()
        formatted_response = json.dumps(response_json, indent=2, ensure_ascii=False)

        # 返回格式化后的 JSON 数据
        return f"""
        <h3>Successfully uploaded to server!</h3>
        <h4>Server Response:</h4>
        <pre style="background-color: #f4f4f4; padding: 10px; border: 1px solid #ccc;">{formatted_response}</pre>
        """
    except json.JSONDecodeError:
        return "Invalid JSON format.", 400
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err.response.text}", 500
    except Exception as e:
        return f"Error uploading to server: {e}", 500
    
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=False)
