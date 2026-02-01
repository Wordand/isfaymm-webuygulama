from services.xml_service import parse_xml_file
import json
import os

def test_parsing():
    base_path = "tests"
    files = ["mock_kdv.xml", "mock_kdv_advanced.xml", "mock_kurumlar.xml", "mock_kurumlar_advanced.xml"]
    
    for f in files:
        path = os.path.join(base_path, f)
        if not os.path.exists(path):
            print(f"Skipping {f}, file not found.")
            continue
            
        print(f"\n--- Testing {f} ---")
        result = parse_xml_file(path)
        
        if "hata" in result:
            print(f"FAILED: {result['hata']}")
        else:
            print(f"SUCCESS: Type={result.get('tur')}, Unvan={result.get('unvan').encode('ascii', 'replace').decode('ascii')}")
            # print(json.dumps(result, indent=2, ensure_ascii=False)) 
            # Uncomment above to see full detail

if __name__ == "__main__":
    test_parsing()
