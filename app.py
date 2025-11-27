from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ------------------------------------------------------------
# 🔧 Inicialização do Banco de Dados
# ------------------------------------------------------------
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        tipo TEXT NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS anúncios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER,
        título TEXT NOT NULL,
        descrição TEXT NOT NULL,
        localização TEXT NOT NULL,
        preço REAL NOT NULL,
        tipo TEXT NOT NULL,
        país TEXT,
        endereço TEXT,
        bairro TEXT,
        cidade TEXT,
        estado TEXT,
        cep TEXT,
        cnpj TEXT,
        imagem_path TEXT,
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
    )''')
    conn.commit()
    conn.close()

init_db()

# ------------------------------------------------------------
# 🏠 Página Inicial
# ------------------------------------------------------------
@app.route('/')
def home():
    return render_template('Página_Inicial.html')

# ------------------------------------------------------------
# 🔐 Login
# ------------------------------------------------------------
@app.route('/login')
def login_page():
    return render_template('Página_de_Login.html', mensagem="", login_data={}, register_data={})

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    senha = request.form['senha']
    session.pop('empresa', None)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM empresas WHERE email = ?", (email,))
    empresa = cursor.fetchone()
    conn.close()

    if empresa and check_password_hash(empresa[3], senha):
        session['empresa'] = {'id': empresa[0], 'nome': empresa[1], 'tipo': empresa[4]}
        return redirect(url_for('dashboard'))
    else:
        return render_template('Página_de_Login.html', mensagem="Email ou senha incorretos.", login_data={}, register_data={})

# ------------------------------------------------------------
# 🧾 Cadastro
# ------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        confirm_email = request.form['confirm_email']
        senha = request.form['senha']
        confirm_senha = request.form['confirm_senha']
        tipo = request.form['tipo']

        register_data = {'nome': nome, 'email': email, 'confirm_email': confirm_email, 'tipo': tipo}

        if len(senha) < 8:
            return render_template('Cadastro_de_Conta.html', mensagem="A senha deve ter pelo menos 8 caracteres.", register_data=register_data)
        if email != confirm_email:
            return render_template('Cadastro_de_Conta.html', mensagem="Os emails não coincidem.", register_data=register_data)
        if senha != confirm_senha:
            return render_template('Cadastro_de_Conta.html', mensagem="As senhas não coincidem.", register_data=register_data)

        senha = generate_password_hash(senha)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO empresas (nome, email, senha, tipo) VALUES (?, ?, ?, ?)", (nome, email, senha, tipo))
            conn.commit()
            return render_template('Página_de_Login.html', mensagem="Conta criada com sucesso! Faça login.")
        except sqlite3.IntegrityError:
            return render_template('Cadastro_de_Conta.html', mensagem="Email já cadastrado.", register_data=register_data)
        finally:
            conn.close()

    return render_template('Cadastro_de_Conta.html', mensagem="", register_data={})

# ------------------------------------------------------------
# 📋 Dashboard com Filtros
# ------------------------------------------------------------
@app.route('/dashboard')
def dashboard():
    if 'empresa' in session:
        q = request.args.get('q', '').strip()
        cidade = request.args.get('cidade', '').strip()
        preco_min = request.args.get('preco_min', '').strip()
        preco_max = request.args.get('preco_max', '').strip()

        query = "SELECT * FROM anúncios WHERE 1=1"
        params = []

        if q:
            query += " AND (título LIKE ? OR descrição LIKE ?)"
            params.extend([f"%{q}%", f"%{q}%"])
        if cidade:
            query += " AND cidade LIKE ?"
            params.append(f"%{cidade}%")
        if preco_min:
            query += " AND preço >= ?"
            params.append(preco_min)
        if preco_max:
            query += " AND preço <= ?"
            params.append(preco_max)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(query, params)
        anuncios = cursor.fetchall()
        conn.close()

        return render_template('dashboard.html', empresa=session['empresa'], anuncios=anuncios)

    return redirect(url_for('login_page'))

# ------------------------------------------------------------
# 🏢 Página de Perfil da Empresa
# ------------------------------------------------------------
@app.route('/perfil')
def perfil():
    if 'empresa' not in session:
        return redirect(url_for('login_page'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM anúncios WHERE empresa_id = ?", (session['empresa']['id'],))
    anuncios = cursor.fetchall()
    conn.close()

    empresa = session['empresa']
    total_anuncios = len(anuncios)

    return render_template('perfil.html', empresa=empresa, anuncios=anuncios, total_anuncios=total_anuncios)

# ------------------------------------------------------------
# 🏗️ Criação de Anúncios
# ------------------------------------------------------------
@app.route('/criar_anuncio', methods=['GET', 'POST'])
def criar_anuncio():
    if 'empresa' in session and session['empresa']['tipo'] == "Armazém":
        return render_template('criar_anuncio.html')
    return redirect(url_for('login_page'))

@app.route('/criar_anuncio_etapa2', methods=['POST'])
def criar_anuncio_etapa2():
    titulo = request.form['titulo']
    descricao = request.form['descricao']
    preco = request.form['preco']
    tipo = request.form['tipo']
    session['anuncio'] = {'titulo': titulo, 'descricao': descricao, 'preco': preco, 'tipo': tipo}
    return render_template('criar_anuncio_2.html')

@app.route('/finalizar_anuncio', methods=['POST'])
def finalizar_anuncio():
    if 'empresa' not in session:
        return redirect(url_for('login_page'))

    pais = request.form['pais']
    endereco = request.form['endereco']
    bairro = request.form['bairro']
    cidade = request.form['cidade']
    estado = request.form['estado']
    cep = request.form['cep']
    cnpj = request.form['cnpj']

    imagens = request.files.getlist('imagens')
    imagem_principal = None
    upload_folder = os.path.join('static', 'imagens')
    os.makedirs(upload_folder, exist_ok=True)

    for i, imagem in enumerate(imagens[:3]):
        if imagem and imagem.filename:
            filename = secure_filename(imagem.filename)
            caminho = os.path.join(upload_folder, filename)
            imagem.save(caminho)
            if i == 0:
                imagem_principal = filename

    anuncio_data = session.get('anuncio', {})
    anuncio_data.update({
        'pais': pais,
        'endereco': endereco,
        'bairro': bairro,
        'cidade': cidade,
        'estado': estado,
        'cep': cep,
        'cnpj': cnpj,
        'imagem_path': imagem_principal,
        'localizacao': f"{endereco}, {bairro}, {cidade} - {estado}, {cep}, {pais}"
    })

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(""" 
        INSERT INTO anúncios (empresa_id, título, descrição, localização, preço, tipo, 
            país, endereço, bairro, cidade, estado, cep, cnpj, imagem_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session['empresa']['id'], anuncio_data['titulo'], anuncio_data['descricao'], anuncio_data['localizacao'],
          anuncio_data['preco'], anuncio_data['tipo'], anuncio_data['pais'], anuncio_data['endereco'],
          anuncio_data['bairro'], anuncio_data['cidade'], anuncio_data['estado'], anuncio_data['cep'],
          anuncio_data['cnpj'], anuncio_data['imagem_path']))
    conn.commit()
    conn.close()

    session.pop('anuncio', None)
    return redirect(url_for('dashboard'))

# ------------------------------------------------------------
# 🏢 Detalhes do Anúncio
# ------------------------------------------------------------
@app.route('/anuncio/<int:id>')
def anuncio_detalhado(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM anúncios WHERE id = ?", (id,))
    anuncio = cursor.fetchone()
    conn.close()

    if not anuncio:
        return "Anúncio não encontrado", 404

    return render_template('detalhe_anuncio.html', anuncio=anuncio)

# ------------------------------------------------------------
# 🚪 Logout
# ------------------------------------------------------------
@app.route('/logout')
def logout():
    session.pop('empresa', None)
    return redirect(url_for('home'))

# ------------------------------------------------------------
# 🚀 Inicialização
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
