#app.py
from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
import os
import tempfile
import shutil

app = Flask(__name__, static_folder='static', static_url_path='/static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    images = request.files.getlist('images')
    prompt = request.form['prompt']

    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"Temporary directory created at: {temp_dir}")

    image_paths = []
    for image in images:
        path = os.path.join(temp_dir, image.filename)
        image.save(path)
        image_paths.append(path)
        print(f"Image saved to: {path}")

    # Prepare the files dictionary correctly
    files = {}
    for i, path in enumerate(image_paths):
        files[f'image{i}'] = (os.path.basename(path), open(path, 'rb'))

    colab_url = 'http://09d7-34-125-135-161.ngrok-free.app'
    try:
        response = requests.post(colab_url, files=files, data={'prompt': prompt})
        response.raise_for_status()
        print('Response Status Code:', response.status_code)
        print('Response Text:', response.text)
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        return jsonify({'error': f'HTTP error occurred: {str(http_err)}'}), 500
    except Exception as e:
        print(f'Other error occurred: {e}')
        return jsonify({'error': f'Failed to make API request: {str(e)}'}), 500
    finally:
        # Close file handles
        for file in files.values():
            file[1].close()

    try:
        result = response.json()
    except ValueError:
        return jsonify({'error': 'Failed to decode JSON from response'}), 500

    colab_image_url = result.get('image_url')
    if not colab_image_url:
        return jsonify({'error': 'No image URL received from Colab'}), 500

    try:
        image_response = requests.get(f"http://09d7-34-125-135-161.ngrok-free.app{colab_image_url}")
        image_response.raise_for_status()

        static_image_dir = os.path.join(app.static_folder, 'generated_images')
        os.makedirs(static_image_dir, exist_ok=True)
        generated_image_filename = 'generated_image.png'
        static_image_path = os.path.join(static_image_dir, generated_image_filename)

        with open(static_image_path, 'wb') as f:
            f.write(image_response.content)
    except requests.exceptions.RequestException as e:
        print(f'Error occurred while downloading the image: {e}')
        return jsonify({'error': f'Failed to download the image: {str(e)}'}), 500

    # Clean up temporary directory
    shutil.rmtree(temp_dir)

    return jsonify({'image_url': f'/static/generated_images/{generated_image_filename}'})


@app.route('/static/generated_images/<filename>')
def generated_image(filename):
    return send_from_directory(os.path.join(app.static_folder, 'generated_images'), filename)

if __name__ == '__main__':
    app.run(debug=True)
