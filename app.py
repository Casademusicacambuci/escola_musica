import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci_2026"
DATABASE = "cambuci.db"

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Mantém as tabelas anteriores e adiciona por segurança
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, rg TEXT, cpf TEXT, 
            endereco TEXT, comprovante_anexo TEXT, telefone TEXT, curso TEXT, data_matricula TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, rg TEXT, cpf TEXT, 
            endereco TEXT, comprovante_anexo TEXT, telefone TEXT, curso TEXT
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, categoria TEXT NOT NULL, preco REAL NOT NULL, estoque INTEGER NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, categoria_fluxo TEXT NOT NULL, descricao TEXT NOT NULL, valor REAL NOT NULL, data TEXT NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL)')
    
    # NOVA TABELA: Agenda Integrada (Aulas e Estúdios)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_agendamento TEXT NOT NULL, -- 'Aula' ou 'Estúdio'
            nome_responsavel TEXT NOT NULL, -- Nome do Aluno ou Cliente do Estúdio
            profissional TEXT,          -- Nome do Professor (se for Aula)
            data_hora TEXT NOT NULL,       -- Data e Horário combinados
            status TEXT NOT NULL           -- 'Agendado' ou 'Concluído'
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('admin', 'admin123', 'administrador')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('caixa', 'caixa123', 'caixa')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('secretaria', 'sec123', 'secretaria')")
    
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE usuario = ? AND senha = ?', (usuario, senha)).fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['usuario'] = user['usuario']
            session['perfil'] = user['perfil']
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    alunos = conn.execute('SELECT * FROM alunos').fetchall()
    professores = conn.execute('SELECT * FROM professores').fetchall()
    produtos = conn.execute('SELECT * FROM produtos').fetchall()
    movimentacoes = conn.execute('SELECT * FROM financeiro ORDER BY id DESC').fetchall()
    
    # Puxa os compromissos agendados por ordem de data
    compromissos = conn.execute('SELECT * FROM agenda ORDER BY data_hora ASC').fetchall()
    
    total_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='entrada'").fetchone()[0] or 0.0
    total_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='saida'").fetchone()[0] or 0.0
    saldo_caixa = total_entradas - total_saidas
    conn.close()
    
    return render_template('index.html', alunos=alunos, professores=professores, produtos=produtos, movimentacoes=movimentacoes, compromissos=compromissos, total_entradas=total_entradas, total_saidas=total_saidas, saldo_caixa=saldo_caixa)

@app.route('/agendar', methods=['POST'])
def agendar():
    tipo = request.form.get('tipo_agendamento')
    nome = request.form.get('nome_responsavel')
    profissional = request.form.get('profissional') or "N/A"
    data_hora = request.form.get('data_hora')
    
    # Trata formatação da data vinda do navegador para exibição amigável
    if data_hora:
        dt = datetime.strptime(data_hora, '%Y-%m-%dT%H:%M')
        data_hora_formatada = dt.strftime('%d/%m/%Y %H:%M')
    else:
        data_hora_formatada = datetime.now().strftime('%d/%m/%Y %H:%M')

    conn = get_db_connection()
    conn.execute('INSERT INTO agenda (tipo_agendamento, nome_responsavel, profissional, data_hora, status) VALUES (?, ?, ?, ?, ?)',
                 (tipo, nome, profissional, data_hora_formatada, 'Agendado'))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/concluir_agenda/<int:id>')
def concluir_agenda(id):
    conn = get_db_connection()
    conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome = request.form.get('nome')
    rg = request.form.get('rg')
    cpf = request.form.get('cpf')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    curso = request.form.get('curso')
    
    filename = ""
    file = request.files.get('comprovante')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"aluno_{cpf}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db_connection()
    conn.execute('INSERT INTO alunos (nome, rg, cpf, endereco, comprovante_anexo, telefone, curso, data_matricula) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                 (nome, rg, cpf, endereco, filename, telefone, curso, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_professor', methods=['POST'])
def cadastrar_professor():
    nome = request.form.get('nome')
    rg = request.form.get('rg')
    cpf = request.form.get('cpf')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    curso = request.form.get('curso')
    
    filename = ""
    file = request.files.get('comprovante')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"prof_{cpf}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db_connection()
    conn.execute('INSERT INTO profesores (nome, rg, cpf, endereco, comprovante_anexo, telefone, curso) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (nome, rg, cpf, endereco, filename, telefone, curso))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/registrar_financeiro', methods=['POST'])
def registrar_financeiro():
    tipo, categoria, descricao, valor = request.form.get('tipo'), request.form.get('categoria_fluxo'), request.form.get('descricao'), float(request.form.get('valor') or 0)
    conn = get_db_connection()
    conn.execute('INSERT INTO financeiro (tipo, categoria_fluxo, descricao, valor, data) VALUES (?, ?, ?, ?, ?)', (tipo, categoria, descricao, valor, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_produto', methods=['POST'])
def cadastrar_produto():
    nome, categoria, preco, estoque = request.form.get('nome'), request.form.get('categoria'), float(request.form.get('preco') or 0), int(request.form.get('estoque') or 0)
    conn = get_db_connection()
    conn.execute('INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (?, ?, ?, ?)', (nome, categoria, preco, estoque))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
