from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from dotenv import load_dotenv
import psycopg2
import os
load_dotenv()  # This loads the .env file
print("DB URL:", os.getenv("DATABASE_URL"))
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Database setup ---
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    image_filename TEXT,
                    category TEXT,
                    prep_time INTEGER,
                    cook_time INTEGER,
                    ingredients TEXT,
                    instructions TEXT
                )
            ''')
            conn.commit()


def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise
# --- Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/admin/recipes')
def admin_recipes():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM recipes")
            recipes = cur.fetchall()
    return render_template('admin-recipes.html', recipes=recipes)

@app.route('/admin/delete/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
            conn.commit()
    return redirect(url_for('admin_recipes'))

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add-recipe.html')
def show_add_form():
    return render_template('add-recipe.html')

@app.route('/recipes', methods=['GET'])
def get_recipes():
    q = request.args.get('q', '').lower()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM recipes")
            recipes = cur.fetchall()
    filtered = [
        {
            'id': r[0],  # PostgreSQL returns tuples, not dicts
            'title': r[1],
            'description': r[2],
            'image': f"/static/uploads/{r[3]}" if r[3] else '',
            'category': r[4]
        }
        for r in recipes if q in r[1].lower() or q in (r[2] or '').lower()
    ]
    return jsonify({'recipes': filtered})

@app.route('/recipes', methods=['POST'])
def add_recipe():
    title = request.form.get('title')
    description = request.form.get('description')
    category = request.form.get('category')
    prep_time = request.form.get('prep_time', type=int)
    cook_time = request.form.get('cook_time', type=int)
    
    ingredients_list = request.form.getlist('ingredients[]')
    instructions_list = request.form.getlist('instructions[]')
    
    ingredients = '\n'.join(ingredients_list)
    instructions = '\n'.join(instructions_list)
    
    image = request.files.get('image')
    filename = ''
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO recipes (title, description, image_filename, category, prep_time, cook_time, ingredients, instructions)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (title, description, filename, category, prep_time, cook_time, ingredients, instructions))
            conn.commit()
    
    return redirect(url_for('thank_you'))

@app.route('/thank-you')
def thank_you():
    return render_template('thank-you.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))