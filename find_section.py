import json

# JSON dosyasını oku
with open('static/data/kdv_tebligi.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Toplam ana bölüm: {len(data)}")
print("\nAna bölümler:")
for d in data[:10]:
    print(f"{d.get('id')} - {d.get('title')}")

# III numaralı bölümü bul
def find_section(items, target_id):
    for item in items:
        uid = item.get('uid', item.get('id'))
        if uid == target_id or item.get('id') == target_id:
            return item
        if 'sub' in item and item['sub']:
            result = find_section(item['sub'], target_id)
            if result:
                return result
    return None

# III bölümünü bul
section_iii = find_section(data, 'III')
if section_iii:
    print(f"\n\nIII bölümü bulundu: {section_iii.get('title')}")
    print(f"Alt bölüm sayısı: {len(section_iii.get('sub', []))}")
    
    # B alt bölümünü bul
    section_b = find_section(section_iii.get('sub', []), 'B')
    if section_b:
        print(f"\nIII/B bölümü: {section_b.get('title')}")
        print(f"Alt bölüm sayısı: {len(section_b.get('sub', []))}")
        
        # 3 numaralı alt bölümü bul
        for sub in section_b.get('sub', []):
            print(f"  {sub.get('id')} - {sub.get('title')}")
            if sub.get('id') == '3':
                print(f"\n\n=== III/B/3 BULUNDU ===")
                print(f"Başlık: {sub.get('title')}")
                print(f"İçerik uzunluğu: {len(sub.get('content', ''))} karakter")
                print(f"\nİlk 500 karakter:")
                print(sub.get('content', '')[:500])
else:
    print("\nIII bölümü bulunamadı!")
    print("\nMevcut ID'ler:")
    for d in data:
        print(f"  {d.get('id')} / {d.get('uid')}")
