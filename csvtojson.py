from flask import Flask, request, jsonify, render_template_string
import csv
import json
from io import StringIO
import chardet
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

def parse_csv(file_content):
    csv_reader = csv.DictReader(StringIO(file_content))
    questions = []
    for row in csv_reader:
        if row.get("linkId") and row.get("text") and row.get("type"):
            question = {
                "linkId": row["linkId"].strip(),
                "text": row["text"].strip(),
                "type": row["type"].strip()
            }

            # Handle options for choice or multiple types
            if question["type"] in ["choice", "multiple"] and row.get("options"):
                question["option"] = [option.strip() for option in row["options"].split(",")]

            questions.append(question)
    return {
        "resourceType": "Questionnaire",
        "id": "GeneratedQuestionnaire",
        "item": questions
    }

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE, questionnaire=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    try:
        # Automatically detect encoding
        raw_content = file.read()
        detected_encoding = chardet.detect(raw_content)['encoding']
        if not detected_encoding:
            return "Unable to detect file encoding.", 400

        file_content = raw_content.decode(detected_encoding)
        questionnaire = parse_csv(file_content)
        return render_template_string(HTML_TEMPLATE, questionnaire=json.dumps(questionnaire, ensure_ascii=False, indent=2))
    except UnicodeDecodeError:
        return "File encoding error. Unable to decode the file.", 400
    except Exception as e:
        return f"Error processing file: {e}", 500

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=False)
