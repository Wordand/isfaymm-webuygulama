import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer

# 1. Modeli Yukle (Ilk seferde ~400MB indirme yapacaktir)
print("Akilli model yukleniyor (paraphrase-multilingual-MiniLM-L12-v2)...")
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"Model yuklenirken hata olustu: {e}")
    exit(1)

def prepare_data(file_name):
    # Proje kök dizinine göre yolu ayarla
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "static", "data", file_name)
    
    if not os.path.exists(json_path):
        print(f"Dosya bulunamadi: {json_path}")
        return []

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    flat_items = []
    
    def flatten(items):
        for item in items:
            content = item.get("content", "").strip()
            # Eğer içerik çok kısaysa veya sadece başlıklardan oluşuyorsa atlıyoruz
            if len(content) > 10:
                flat_items.append({
                    "id": item.get("uid", item.get("id")),
                    "title": item.get("title"),
                    "content": content
                })
            if item.get("sub"):
                flatten(item["sub"])
    
    flatten(data)
    return flat_items

def save_embeddings(file_name, suffix):
    print(f"\n{file_name} isleniyor...")
    items = prepare_data(file_name)
    
    if not items:
        print(f"{file_name} icin islenecek madde bulunamadi.")
        return

    # Sadece metinleri alip vektore ceviriyoruz (Baslik + Icerik)
    texts = [f"{item['title']} {item['content']}" for item in items]
    
    print(f"{len(texts)} madde vektore donusturuluyor. Bu islem biraz surebilir...")
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    
    # Kaydedilecek klasörü kontrol et
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "static", "data", "embeddings")
    os.makedirs(output_dir, exist_ok=True)
    
    # Vektorleri (numpy formatinda) ve meta verileri (json) kaydet
    np.save(os.path.join(output_dir, f"{suffix}_vectors.npy"), embeddings)
    with open(os.path.join(output_dir, f"{suffix}_meta.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=4)
        
    print(f"{suffix.upper()} icin zeka dosyalari kaydedildi.")

if __name__ == "__main__":
    # KDV ve KV icin islemleri baslat
    save_embeddings("kdv_tebligi.json", "kdv")
    save_embeddings("kv_tebligi.json", "kv")
    print("\nMevzuat artik vektör tabanli arama icin hazir.")
