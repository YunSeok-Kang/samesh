## ROOT_DIR = "../../outputs/mesh_segmentation_output/CustomDataset"  # 수정: 실제 루트 경로
from flask import Flask, request, render_template_string, send_from_directory, jsonify
import os
import json
from math import ceil

app = Flask(__name__)

# Configuration: root directory containing depth1 folders
ROOT_DIR = "../../outputs/mesh_segmentation_output/CustomDataset"  # 수정: 실제 루트 경로
PER_PAGE = 20  # 한 페이지에 표시할 mesh_id 수

# Helper: load/save status JSON per group
def status_path(group):
    return os.path.join(ROOT_DIR, f"{group}_status.json")

def load_status(group):
    path = status_path(group)
    if os.path.exists(path):
        try:
            return json.load(open(path, 'r', encoding='utf-8'))
        except:
            return {}
    return {}

def save_status(group, status):
    with open(status_path(group), 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

# Main viewer template with preformatted captions
TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mesh Viewer</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    pre { white-space: pre-wrap; word-wrap: break-word; }
    table.table td img { height: 250px; }  /* 이미지 높이 확장 */
  </style>
</head>
<body class="p-4">
  <h1>Mesh Results for {{ group }}</h1>
  <p>Total meshes: {{ total }} | Render OK: {{ render_ok }} | Not OK: {{ render_fail_count }} | Empty: {{ empty_count }}</p>
  <div class="mb-3">
    <a href="/status?group={{ group }}" class="btn btn-sm btn-primary">View Status</a>
    <a href="/render_fail?group={{ group }}" class="btn btn-sm btn-danger">Failed Renders</a>
  </div>

  <form method="get" class="mb-3">
    <input type="hidden" name="group" value="{{ group }}">
    <label for="suffixSelect" class="form-label">Caption Suffix:</label>
    <select id="suffixSelect" name="caption_suffix" class="form-select" onchange="this.form.submit()">
      <option value="all" {% if caption_suffix=='all' %}selected{% endif %}>All</option>
      {% for s in available_suffixes %}
        <option value="{{ s }}" {% if caption_suffix==s %}selected{% endif %}>{{ s }}</option>
      {% endfor %}
    </select>
  </form>

  <table class="table table-striped">
    <th>Render OK</th>
    <th>Mesh ID</th>
    <th>Matte</th>
    <th>Segmented</th>
    <th>Renders</th>                            <!-- 여기 추가 -->
    <th>Captions & Quality Check</th>
    <tbody>
    {% for item in items %}
      <tr>
        <td><input type="checkbox" class="status-check" data-mesh="{{ item.mesh_id }}" data-type="render" {% if status.get(item.mesh_id,{}).get('render') %}checked{% endif %}></td>
        <td>{{ item.mesh_id }}</td>
        <td>{% if item.matte %}<img src="/{{ group }}/{{ item.mesh_id }}/matte_collage_2048x2048.png" height="80">{% else %}&ndash;{% endif %}</td>
        <td>{% if item.segmented %}<img src="/{{ group }}/{{ item.mesh_id }}/segmented_collage_2048x2048.png" height="80">{% else %}&ndash;{% endif %}</td>
        <td>
            {% for r in item.renders %}
            <div class="mb-2" style="text-align:center">
                <img src="{{ r.url }}" height="80"><br>
                <small>label{{ r.label }}</small>
            </div>
            {% endfor %}
            {% if not item.renders %}&ndash;{% endif %}
        </td>
        <td>
          {% for cap in item.captions %}
            <div class="mb-3">
              <div class="form-check">
                <input class="form-check-input status-check-caption" type="checkbox" id="chk_{{ item.mesh_id }}_{{ cap.suffix }}" data-mesh="{{ item.mesh_id }}" data-suffix="{{ cap.suffix }}" data-type="caption" {% if status.get(item.mesh_id,{}).get('captions',{}).get(cap.suffix) %}checked{% endif %}>
                <label class="form-check-label" for="chk_{{ item.mesh_id }}_{{ cap.suffix }}"><strong>{{ cap.suffix }}</strong></label>
              </div>
              <pre class="bg-light p-2 rounded">{{ cap.text }}</pre>
            </div>
          {% endfor %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <nav>
    <ul class="pagination">
      {% for p in range(1, pages+1) %}
        <li class="page-item {% if p==page %}active{% endif %}"><a class="page-link" href="?group={{ group }}&caption_suffix={{ caption_suffix }}&page={{ p }}">{{ p }}</a></li>
      {% endfor %}
    </ul>
  </nav>

  <script>
    function sendStatus(mesh, type, suffix, checked) {
      fetch('/update_check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group: '{{ group }}', mesh_id: mesh, check_type: type, suffix: suffix, checked: checked })
      });
    }
    document.querySelectorAll('.status-check').forEach(cb => cb.addEventListener('change', () => sendStatus(cb.dataset.mesh, cb.dataset.type, '', cb.checked)));
    document.querySelectorAll('.status-check-caption').forEach(cb => cb.addEventListener('change', () => sendStatus(cb.dataset.mesh, cb.dataset.type, cb.dataset.suffix, cb.checked)));
  </script>
</body>
</html>
'''

# Template for failed renders view
FAIL_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Failed Renders for {{ group }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <h1>Failed Renders for {{ group }}</h1>
  <p>Total meshes: {{ total }} | Failed renders: {{ failed_count }}</p>
  <a href="/?group={{ group }}" class="btn btn-sm btn-secondary mb-3">Back</a>
  <ul class="list-group">
    {% for mesh in failed %}
      <li class="list-group-item list-group-item-danger">{{ mesh }}</li>
    {% endfor %}
  </ul>
</body>
</html>
'''

@app.route('/')
def index():
    group = request.args.get('group')
    if not group:
        groups = [d for d in os.listdir(ROOT_DIR) if os.path.isdir(os.path.join(ROOT_DIR, d))]
        return render_template_string('<h1>Select a group</h1><ul>{% for g in groups %}<li><a href="?group={{ g }}">{{ g }}</a></li>{% endfor %}</ul>', groups=groups)

    caption_suffix = request.args.get('caption_suffix', 'all')
    base = os.path.join(ROOT_DIR, group)
    mesh_ids = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    total = len(mesh_ids)
    status = load_status(group)

    items = []
    render_ok = 0
    all_suffixes = set()
    for mesh_id in mesh_ids:
        path = os.path.join(base, mesh_id)
        matte = os.path.exists(os.path.join(path, 'matte_collage_2048x2048.png'))
        segmented = os.path.exists(os.path.join(path, 'segmented_collage_2048x2048.png'))
        # ─── 새로 추가: renders 하위에서 label 이미지 수집 ───
        renders = []
        renders_dir = os.path.join(path, 'renders')
        if os.path.isdir(renders_dir):
            import re
            for fname in os.listdir(renders_dir):
                m = re.match(rf"{re.escape(mesh_id)}_label_(\d+)_collage_2048x2048\.png", fname)
                if m:
                    renders.append({
                        'label': m.group(1),
                        'url': f"/{group}/{mesh_id}/renders/{fname}"
                    })
        # ────────────────────────────────────────────────
        files = os.listdir(path)
        has_gemma = 'caption_gemma.txt' in files
        captions = []
        for fname in files:
            if fname == 'caption.txt':
                if has_gemma: continue
                suffix = 'gemma'
            elif fname.startswith('caption_') and fname.endswith('.txt'):
                suffix = fname[len('caption_'):-4]
            else:
                continue
            all_suffixes.add(suffix)
            if caption_suffix in ('all', suffix):
                try: text = open(os.path.join(path, fname), 'r', encoding='utf-8').read().strip()
                except: text = ''
                captions.append({'suffix': suffix, 'text': text})
        if status.get(mesh_id, {}).get('render'):
            render_ok += 1
        # items.append({'mesh_id': mesh_id, 'matte': matte, 'segmented': segmented, 'captions': captions})
        items.append({
            'mesh_id': mesh_id,
            'matte': matte,
            'segmented': segmented,
            'renders': renders,       # ← 이 항목 추가
            'captions': captions
        })

    render_fail_count = total - render_ok
    # 빈 디렉토리 개수 계산 (파일 없음)
    empty_count = sum(1 for mid in mesh_ids if not os.listdir(os.path.join(base, mid)))
    page = int(request.args.get('page', 1))
    pages = ceil(total / PER_PAGE)
    return render_template_string(TEMPLATE, group=group, total=total, render_ok=render_ok,
                                  render_fail_count=render_fail_count, empty_count=empty_count, items=items[(page-1)*PER_PAGE:page*PER_PAGE],
                                  pages=pages, page=page, available_suffixes=sorted(all_suffixes),
                                  caption_suffix=caption_suffix, status=status)

@app.route('/render_fail')
def render_fail_view():
    group = request.args.get('group')
    status = load_status(group)
    base = os.path.join(ROOT_DIR, group)
    mesh_ids = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
    failed = [m for m in mesh_ids if not status.get(m, {}).get('render')]
    total = len(mesh_ids)
    failed_count = len(failed)
    return render_template_string(FAIL_TEMPLATE, group=group, total=total, failed=failed, failed_count=failed_count)

@app.route('/status')
def status_view():
    group = request.args.get('group')
    status = load_status(group)
    return render_template_string(STATUS_TEMPLATE, group=group, status=status)

@app.route('/update_check', methods=['POST'])
def update_check():
    data = request.get_json()
    group = data['group']
    mesh_id = data['mesh_id']
    ctype = data['check_type']
    suffix = data.get('suffix')
    checked = data['checked']
    status = load_status(group)
    if mesh_id not in status:
        status[mesh_id] = {'render': False, 'captions': {}}
    if ctype == 'render':
        status[mesh_id]['render'] = checked
    else:
        status[mesh_id]['captions'][suffix] = checked
    save_status(group, status)
    return jsonify(success=True)

# Full status template
STATUS_TEMPLATE = '''
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Status for {{ group }}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body class="p-4">
  <h1>Status for {{ group }}</h1>
  <a href="/?group={{ group }}" class="btn btn-sm btn-secondary mb-3">Back</a>
  <table class="table table-bordered"><thead><tr><th>Mesh ID</th><th>Render OK</th><th>Captions</th></tr></thead><tbody>
  {% for mesh, st in status.items() %}
    <tr><td>{{ mesh }}</td><td>{{ '✅' if st.get('render') else '❌' }}</td><td>{% for s,ok in st.get('captions',{}).items() %}{{ s }}:{{ '✅' if ok else '❌' }}<br>{% endfor %}</td></tr>
  {% endfor %}</tbody></table></body></html>
'''  

# renders 하위 파일 전용
@app.route('/<group>/<mesh_id>/renders/<filename>')
def serve_renders(group, mesh_id, filename):
    directory = os.path.join(ROOT_DIR, group, mesh_id, 'renders')
    return send_from_directory(directory, filename)

@app.route('/<group>/<mesh_id>/<filename>')
def serve_file(group, mesh_id, filename):
    directory = os.path.join(ROOT_DIR, group, mesh_id)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


