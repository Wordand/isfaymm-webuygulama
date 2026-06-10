from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ozelge_service import build_ozelge_index


if __name__ == "__main__":
    data = build_ozelge_index(ROOT)
    print(f"{data['count']} ozelge indekslendi.")
    print(f"Indeks: {ROOT / 'static' / 'data' / 'ozelgeler_index.json'}")
