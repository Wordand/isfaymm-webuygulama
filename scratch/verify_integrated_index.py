import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ozelge_service import load_ozelge_index

def verify():
    print("Loading ozelge index...")
    data = load_ozelge_index(ROOT)
    
    items = data.get("items", [])
    count = data.get("count", 0)
    print(f"Total count reported: {count}")
    print(f"Total items in list: {len(items)}")
    
    assert len(items) == 88, f"Expected 88 items, got {len(items)}"
    
    # Check first item fields
    first = items[0]
    print("\nFirst item check:")
    print(f"  Filename: {first.get('filename')}")
    print(f"  Slug: {first.get('slug')}")
    print(f"  Code: {first.get('code')}")
    print(f"  Title: {first.get('title')}")
    print(f"  Ozelge No: {first.get('ozelge_no')}")
    print(f"  Date: {first.get('date')}")
    print(f"  Date Sort: {first.get('date_sort')}")
    print(f"  Summary: {first.get('summary')}")
    print(f"  Konu Ozeti: {first.get('konu_ozeti')}")
    print(f"  Soru Ozeti: {first.get('soru_ozeti')}")
    print(f"  Cevap Ozeti: {first.get('cevap_ozeti')}")
    print(f"  Topics: {first.get('topics')}")
    
    # Validate critical fields exist and are not empty
    required_fields = ["filename", "slug", "code", "title", "ozelge_no", "date", "date_sort", "summary", "konu_ozeti", "soru_ozeti", "cevap_ozeti", "topics"]
    for field in required_fields:
        val = first.get(field)
        assert val, f"Field '{field}' is missing or empty in first item"
        
    print("\nAll checks passed successfully! Integration is correct.")

if __name__ == "__main__":
    try:
        verify()
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)
