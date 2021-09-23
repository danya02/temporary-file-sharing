from flask import Flask, render_template, send_file, request, g, jsonify, url_for, abort, make_response, Response
import yaml
from database import *
import os
import uuid
import hashlib
import datetime
import humanize

app = Flask(__name__)
app.config['DEBUG'] = True
@app.before_request
def fix_remote_addr():
    # This is only needed because of the hosting's proxy setup. Change based on your setup.
    request.remote_addr = request.headers.get('X-Very-Real-Ip') or request.remote_addr

@app.before_request
def load_config():
    # Load the CONFIG.yml file.
    with open('/CONFIG.yml') as o:
        g.conf = yaml.safe_load(o)

@app.route('/')
def index():
    return render_template('index.html',
            file_size=humanize.naturalsize(g.conf['max_file_size']*1024*1024, binary=True),
            storage_time=humanize.naturaldelta(datetime.timedelta(seconds=g.conf['store_for_seconds'])))

@app.route('/style.css')
def style():
    return send_file('/bootstrap.min.css')

@app.route('/bootstrap.js')
def bootstrap_js():
    return send_file('/bootstrap.js')

@app.route('/copy-icon.svg')
def copy_icon():
    return send_file('/static/copy_all_white_48dp.svg')

def error(code, text):
    response = make_response('<h1>' + text + '</h1>')
    response.headers['X-Errorpage-Title'] = f'{code} {text}'
    return response, code

@app.route('/upload', methods=['POST'])
def upload_files():
    # check that there is exactly one file in input
    if not request.files:
        return error(400, "No files provided in input")
    files = request.files.getlist('files')
    if len(files)>1:
        return error(400, "Only one file can be uploaded at once")

    # check that the file isn't blocked/is allowed
    file = files[0]
    mode_is_block = g.conf['filter_mode'].lower() == 'block'
    file_has_filtered_ext = file.filename.split('.')[-1] in g.conf['filter_extensions']
    file_has_filtered_mime = file.mimetype in g.conf['filter_mime']

    if mode_is_block:
        # if operating in block mode, reject if extension or MIME is wrong
        if file_has_filtered_ext or file_has_filtered_mime:
            return error(415, "File type not allowed")
    else:
        # if operating in allow mode, do NOT reject if extension is correct and the mimetype is either correct or missing
        if not ( (file_has_filtered_ext) and (file_has_filtered_mime or file.mimetype is None) ):
            return error(415, "File type not allowed")

    # determine file extension: check if it is one of the list of extensions with more than one dotted part
    file_ext = file.filename.split('.')[-1]
    for long_ext in g.conf['long_extensions']:
        if file.filename.endswith(long_ext):
            file_ext = long_ext

    # save file, but abort if it turns out to be too long to process
    temp_file_id = str(uuid.uuid4())
    stop_after_bytes = g.conf['max_file_size'] * 1024 * 1024
    processed_bytes = 0
    path_to_temp_file = TEMP_DIR + '/' + temp_file_id + '.' + file_ext
    hasher = hashlib.sha256()
    try:
        # if the client has told us that their file is too big, bail out early
        if file.content_length > stop_after_bytes:
            raise BufferError
        with open(path_to_temp_file, 'wb') as temp_file:
            buffer = file.read(16*1024)
            while len(buffer) != 0:
                hasher.update(buffer)
                processed_bytes += len(buffer)
                if processed_bytes > stop_after_bytes:
                    raise BufferError
                temp_file.write(buffer)
                buffer = file.read(16*1024)
    except BufferError:
        try:
            os.remove(path_to_temp_file)
        except: pass
        return error(413, "File too big")
    
    # file is now saved in temp, we need to create a database record for it and move it to storage
    sha256 = hasher.hexdigest()
    web_name = File.generate_web_name()
    if web_name is None:
        return error(500, "Gave up trying to get unique name for file")
    final_name = get_content_dir(sha256) + '/' + sha256 + '.' + file_ext
    os.rename(path_to_temp_file, final_name)
    File.create(
        file_active=True,
        file_present_in_filesystem=True,
        web_name=web_name,
        extension=file_ext,
        mime_type=file.mimetype,
        sha256=sha256,
        size=processed_bytes,
        uploader_ip=(request.remote_addr if g.conf['log_ip'] else None),
        expires_at=datetime.datetime.now() + datetime.timedelta(seconds=g.conf['store_for_seconds'])
    )
    
    # return acknowledgement of file upload
    url = url_for('serve_file', web_name=web_name, _external=True)

    # if this is the JSON code from pomf's source, then format the response as it expects
    if request.args.get('format') == 'json':
        return jsonify({'success': 'true', 'files': [{'hash': sha256, 'name': file.filename, 'url': url, 'size': processed_bytes}]})
    elif request.args.get('format') == 'text':
        return Response(url, mimetype='text/plain')
    else:
        # it can either be a web browser, which can handle the incomplete HTML, or a script, which can find the URL easier.
        return f'Your file is now live at: <a href="{url}">{url}</a>'


@app.route('/f/<web_name>')
def serve_file(web_name):
    file = File.get_or_none(web_name=web_name)

    if not file:
        return abort(404)

    if not file.file_active:
        return abort(404)

    if file.expires_at < datetime.datetime.now():
        file.file_active = False
        file.save()
        return abort(404)

    return send_file(file.get_path_to_file())

    
