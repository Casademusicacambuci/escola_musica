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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. TABELA DE ALUNOS (Histórico Permanente)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            rg TEXT,
            cpf TEXT,
            endereco TEXT,
            comprovante_anexo TEXT,
            telefone TEXT,
            curso TEXT,
            data_matricula TEXT,
            status TEXT DEFAULT 'Ativo'
        )
    ''')
    
    # 2. TABELA DE PROFESSORES (Histórico Permanente)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            rg TEXT,
            cpf TEXT,
            endereco TEXT,
            telefone TEXT,
            especialidade TEXT,
            data_cadastro TEXT,
            status TEXT DEFAULT 'Ativo'
        )
    ''')
    
    # 3. TABELA DE PRODUTOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,
            preco REAL NOT NULL,
            estoque INTEGER NOT NULL
        )
    ''')
    
    # 4. TABELA FINANCEIRO
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            categoria_fluxo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data TEXT NOT NULL
        )
    ''')
    
    # 5. TABELA DE USUÁRIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    ''')
    
    # 6. AGENDA DOS ESTÚDIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_agendamento TEXT NOT NULL,
            nome_responsavel TEXT NOT NULL,
            rg TEXT,
            cpf TEXT,
            endereco TEXT,
            comprovante_anexo TEXT,
            telefone TEXT,
            data_compromisso TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            valor_reserva REAL DEFAULT 0.0,
            status TEXT NOT NULL,
            status_servico TEXT DEFAULT 'Pendente',
            tecnico TEXT,
            observacoes TEXT
        )
    ''')
    
    # 7. AGENDA DE AULAS DA SECRETARIA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agenda_aulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER,
            professor_id INTEGER,
            materia TEXT NOT NULL,
            sala TEXT,
            data_aula TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            status_aula TEXT DEFAULT 'Agendada',
            observacoes TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id),
            FOREIGN KEY (professor_id) REFERENCES professores(id)
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('admin', 'admin123', 'administrador')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('caixa', 'caixa123', 'caixa')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('secretaria', 'sec123', 'secretaria')")
    conn.commit()
    conn.close()

init_db()

def atualizar_estrutura_banco():
    conn = get_db_connection()
    try:
        conn.execute('ALTER TABLE alunos ADD COLUMN status TEXT DEFAULT "Ativo"')
        conn.commit()
    except:
        pass
    conn.close()

atualizar_estrutura_banco()

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
            flash('Usuario ou senha incorretos!', 'danger')
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
    
    alunos = conn.execute('SELECT * FROM alunos ORDER BY nome ASC').fetchall()
    professores = conn.execute('SELECT * FROM professores ORDER BY nome ASC').fetchall()
    produtos = conn.execute('SELECT * FROM produtos').fetchall()
    
    # CORREÇÃO: Alinhado perfeitamente com as chamadas do index.html
    fluxo_caixa = conn.execute('SELECT * FROM financeiro ORDER BY id DESC').fetchall()
    agendamentos = conn.execute('SELECT * FROM agenda ORDER BY data_compromisso ASC, hora_inicio ASC').fetchall()
    
    aulas = conn.execute('''
        SELECT a.id, al.nome as nome_aluno, pr.nome as nome_professor, a.materia, a.sala, a.data_aula, a.hora_inicio, a.hora_fim, a.status_aula, a.observacoes
        FROM agenda_aulas a
        LEFT JOIN alunos al ON a.aluno_id = al.id
        LEFT JOIN professores pr ON a.professor_id = pr.id
        ORDER BY a.data_aula ASC, a.hora_inicio ASC
    ''').fetchall()
    
    total_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='entrada'").fetchone()[0] or 0.0
    total_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='saida'").fetchone()[0] or 0.0
    saldo_atual = total_entradas - total_saidas
    conn.close()
    
    return render_template('index.html', 
                           alunos=alunos, 
                           professores=professores, 
                           aulas=aulas, 
                           produtos=produtos, 
                           fluxo_caixa=fluxo_caixa, 
                           agendamentos=agendamentos, 
                           total_entradas=total_entradas, 
                           total_saidas=total_saidas, 
                           saldo_atual=saldo_atual)

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
    # CORREÇÃO: Alterado de 'address' para 'endereco' para bater com a criação da tabela
    conn.execute('INSERT INTO alunos (nome, rg, cpf, endereco, comprovante_anexo, telefone, curso, data_matricula, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, "Ativo")', (nome, rg, cpf, endereco, filename, telefone, curso, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    flash('Aluno cadastrado com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/cadastrar_professor', methods=['POST'])
def cadastrar_professor():
    nome = request.form.get('nome')
    rg = request.form.get('rg')
    cpf = request.form.get('cpf')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    especialidade = request.form.get('especialidade')
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO professores (nome, rg, cpf, endereco, telefone, especialidade, data_cadastro, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, "Ativo")
    ''', (nome, rg, cpf, endereco, telefone, especialidade, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    flash('Professor registrado com sucesso no banco histórico!', 'success')
    return redirect(url_for('index'))

@app.route('/agendar_aula', methods=['POST'])
def agendar_aula():
    aluno_id = request.form.get('aluno_id')
    professor_id = request.form.get('professor_id')
    materia = request.form.get('materia')
    sala = request.form.get('sala')
    data_aula = request.form.get('data_aula')
    hora_inicio = request.form.get('hora_inicio')
    hora_fim = request.form.get('hora_fim')
    observacoes = request.form.get('observacoes')
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO agenda_aulas (aluno_id, professor_id, materia, sala, data_aula, hora_inicio, hora_fim, status_aula, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Agendada', ?)
    ''', (aluno_id, professor_id, materia, sala, data_aula, hora_inicio, hora_fim, observacoes))
    conn.commit()
    conn.close()
    flash('Aula agendada com sucesso na Secretaria!', 'success')
    return redirect(url_for('index'))

@app.route('/excluir_aula/<int:id>', methods=['POST'])
def excluir_aula(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM agenda_aulas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Aula removida da agenda com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/agendar', methods=['POST'])
def agendar():
    tipo = request.form.get('tipo_agendamento')
    nome = request.form.get('nome_responsavel')
    rg = request.form.get('rg')
    cpf = request.form.get('cpf')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    data_compromisso = request.form.get('data_compromisso')
    hora_inicio = request.form.get('hora_inicio')
    hora_fim = request.form.get('hora_fim')
    valor_reserva = float(request.form.get('valor_reserva') or 0.0)
    status = request.form.get('status')
    tecnico = request.form.get('tecnico') or "Nao designado"
    observacoes = request.form.get('observacoes')
    
    conn = get_db_connection()
    filename = ""
    file = request.files.get('comprovante')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"agenda_{cpf if cpf else 'cliente'}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn.execute('''
        INSERT INTO agenda (tipo_agendamento, nome_responsavel, rg, cpf, endereco, comprovante_anexo, telefone, data_compromisso, hora_inicio, hora_fim, valor_reserva, status, status_servico, tecnico, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,
