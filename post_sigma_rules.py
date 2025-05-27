import os
import yaml
import json
import requests
from datetime import date, datetime

# Elasticsearch sozlamalari
ES_URL = "https://search-siemlog-rddlwektckldlou57enditbsqa.eu-north-1.es.amazonaws.com/sigma_rules/_bulk"
AUTH = ("sardor", "Aws0000$")
HEADERS = {"Content-Type": "application/x-ndjson"}
RULES_DIR = "rules"

def convert_dates(obj):
    """Barcha date, datetime tiplarini ISO stringga aylantiradi"""
    if isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(v) for v in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    else:
        return obj

def load_yaml_rules(directory):
    """Barcha .yml/.yaml fayllarni ro‘yxatga yuklaydi"""
    rules = []
    for filename in os.listdir(directory):
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        data["filename"] = filename
                        rules.append(data)
                    elif isinstance(data, list):
                        for rule in data:
                            rule["filename"] = filename
                            rules.append(rule)
            except Exception as e:
                print(f"[X] Xatolik: {filename} faylida - {e}")
    return rules

def upload_bulk(rules):
    bulk_data = ""
    uploaded = 0
    for rule in rules:
        rule_id = rule.get("id")
        if not rule_id:
            print(f"[!] 'id' yo‘q: {rule.get('filename')}")
            continue
        rule = convert_dates(rule)
        bulk_data += json.dumps({ "index": { "_id": rule_id } }) + "\n"
        bulk_data += json.dumps(rule) + "\n"
        uploaded += 1

    if bulk_data:
        response = requests.post(
            ES_URL,
            data=bulk_data,
            headers=HEADERS,
            auth=AUTH
        )
        if response.status_code in (200, 201):
            print(f"[+] {uploaded} ta rule bulk orqali yuborildi.")
        else:
            print(f"[!] Bulk xato: {response.status_code} - {response.text[:300]}")
    else:
        print("[!] Yuboriladigan ma’lumot topilmadi.")

def main():
    rules = load_yaml_rules(RULES_DIR)
    print(f"[i] Topilgan qoidalar: {len(rules)}")
    upload_bulk(rules)

if __name__ == "__main__":
    main()
