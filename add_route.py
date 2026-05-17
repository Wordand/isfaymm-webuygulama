with open('routes/main_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

marker = 'def mevzuat_degisiklikleri(): return render_template("pages/mevzuat_degisiklikleri.html")'
addition = '\n\n@bp.route("/mevzuat/kdv-tevkifat")\ndef kdv_tevkifat(): return render_template("pages/kdv_tevkifat.html")'

if 'def kdv_tevkifat' not in content:
    content = content.replace(marker, marker + addition, 1)
    with open('routes/main_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Route eklendi.')
else:
    print('Route zaten mevcut.')
