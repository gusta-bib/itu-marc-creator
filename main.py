from flask import Flask, request, jsonify, send_from_directory
import re

app = Flask(__name__)

# Helper functions
def capitalize_sentence(sentence, language="tr"):
    if not sentence:
        return ""
    if language == "tr":
        turkish_upper_to_lower = {"İ": "i", "I": "ı"}
        sentence = "".join(turkish_upper_to_lower.get(char, char.lower()) for char in sentence)
    elif language == "en":
        sentence = sentence.lower()
    return sentence[0].upper() + sentence[1:]

def format_title(title, language="tr"):
    parts = [capitalize_sentence(part.strip(), language) for part in title.split(":")]
    return ": ".join(parts)

def detect_language(text):
    turkish_chars = "çğıöşüÇĞİÖŞÜ"
    english_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if any(char in turkish_chars for char in text):
        return "tr"
    elif all(char in english_chars or char.isspace() or char in ".,!?;:'\"()-" for char in text):
        return "en"
    return "tr"

def capitalize_name(name):
    turkish_upper = {"i": "İ", "ı": "I"}
    turkish_lower = {"İ": "i", "I": "ı"}
    def capitalize_word(word):
        if not word:
            return ""
        first_letter = turkish_upper.get(word[0], word[0].upper())
        rest_of_word = "".join([turkish_lower.get(char, char.lower()) for char in word[1:]])
        return first_letter + rest_of_word
    return " ".join(capitalize_word(part) for part in name.split())

def remove_titles(name):
    cleaned_name = re.sub(r'\b(Prof\.?|Doç\.?|Dr\.?)\b', '', name).strip()
    return re.sub(r'\s*\.\s*', ' ', cleaned_name)

def extract_summaries(input_text):
    summary_start = input_text.split("s.", 1)[1].strip() if "s." in input_text else ""
    summaries = summary_start.split("\n")
    turkish_summary = "\n".join([s.strip() for s in summaries if not s.startswith("In this thesis")]).strip()
    english_summary = "\n".join([s.strip() for s in summaries if s.startswith("In this thesis")]).strip()
    return turkish_summary, english_summary

def create_marc_record(thesis_info):
    title_en = thesis_info.get('title_en', '')
    title_tr = thesis_info.get('title_tr', '')

    language_245 = detect_language(title_en)
    language_246 = detect_language(title_tr)

    formatted_title_245 = format_title(title_en, language=language_245)
    formatted_title_246 = format_title(title_tr, language=language_246)
    author_name = thesis_info.get('author', '')
    advisor_name = thesis_info.get('advisor', '')
    university = thesis_info.get('university', '')
    department = thesis_info.get('department', '')
    year = thesis_info.get('year', '2024')
    turkish_summary_1 = thesis_info.get('turkish_summary_1', '')
    turkish_summary_2 = thesis_info.get('turkish_summary_2', '')
    english_summary = thesis_info.get('english_summary', '')
    ana_bilim_dali = thesis_info.get('ana_bilim_dali', '')

    author_name = capitalize_name(author_name)
    advisor_name = capitalize_name(advisor_name)
    advisor_name_no_titles = remove_titles(advisor_name)

    author_last_name = author_name.split()[-1] if author_name.split() else ""
    author_first_names = " ".join(author_name.split()[:-1]) if author_name.split() else ""
    advisor_last_name = advisor_name_no_titles.split()[-1] if advisor_name_no_titles.split() else ""
    advisor_first_names = " ".join(advisor_name_no_titles.split()[:-1]) if advisor_name_no_titles.split() else ""

    marc_record = f"""
y	007	 	 	ta
y	008	 	 	241121s{year}    tu d     bm   000 0 tur d
y	040	 	 	ITU|erda|beng
y	041	1	 	eng|btur
y	049	 	 	ITUM

a	100	1	 	{author_last_name}, {author_first_names},|eauthor
t	245	1	0	{formatted_title_245} /|c{author_name}; thesis advisor {advisor_name}
u	246	3	1	{formatted_title_246}
p	264	 	4	|c{year}.
r	300	 	 	pages ;|c30 cm
r	336	 	 	Text|2rdacontent
r	337	 	 	Unmediated|2rdamedia
r	338	 	 	Volume|2rdacarrier
n	502	 	 	Tez|b(Doktora)--|c{university},|d{year}.
n	504	 	 	Includes bibliographical references.
n	520	 	 	{turkish_summary_1}
n	520	 	 	{turkish_summary_2}
n	520	 	 	{english_summary}
d	650	 	0	Tezler, Akademik
d	650	 	0	Dissertations, Academic
d	610	2	0	{university}|vDissertations
d	610	2	0	{university}|vTezler
d	690	 	 	Tezler, Yüksek Lisans
d	690	 	 	Thesis, Master
b	700	1	 	{advisor_last_name}, {advisor_first_names},|ethesis advisor
b	710	2	 	{university}|b{ana_bilim_dali} Ana Bilim Dalı
    """
    return marc_record

def extract_thesis_info(input_text):
    thesis_info = {}
    title_match = re.search(r"^(.*?) / (.*)$", input_text.strip().split("\n")[0])
    if title_match:
        thesis_info['title_en'] = title_match.group(1).strip()
        thesis_info['title_tr'] = title_match.group(2).strip()

    author_match = re.search(r"Yazar:(.*)", input_text)
    if author_match:
        thesis_info['author'] = author_match.group(1).strip()

    advisor_match = re.search(r"Danışman:(.*)", input_text)
    if advisor_match:
        thesis_info['advisor'] = advisor_match.group(1).strip()

    location_match = re.search(r"Yer Bilgisi:(.*)", input_text)
    if location_match:
        location_info = location_match.group(1).split(" / ")
        thesis_info['university'] = location_info[0].strip()
        thesis_info['department'] = location_info[1].strip()
        thesis_info['ana_bilim_dali'] = location_info[2].strip()

    turkish_summary, english_summary = extract_summaries(input_text)
    turkish_parts = turkish_summary.split("\n", 1)
    thesis_info['turkish_summary_1'] = turkish_parts[0].strip()
    thesis_info['turkish_summary_2'] = turkish_parts[1].strip() if len(turkish_parts) > 1 else ""
    thesis_info['english_summary'] = english_summary

    year_match = re.search(r"\b(\d{4})\b", input_text)
    if year_match:
        thesis_info['year'] = year_match.group(1).strip()

    return thesis_info

# Serve the index.html file
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Define a POST endpoint
@app.route('/generate', methods=['POST'])
def generate_marc_record():
    data = request.get_json()
    input_text = data.get('input_text', '')
    if not input_text:
        return jsonify({'error': 'No input text provided'}), 400

    thesis_info = extract_thesis_info(input_text)
    marc_record = create_marc_record(thesis_info)
    return jsonify({'marc_record': marc_record})

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
