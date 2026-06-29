import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci_2026"

# Mudamos o nome do arquivo para forçar o Render a criar um banco limpo e atualizado
DATABASE = "cambuci_v2.db"

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. TABELA DE ALUNOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            instrumento TEXT,
            data_matricula TEXT
        )
    ''')
    
    # 2. TABELA DE PROFESSORES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            especialidade TEXT
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
            origem TEXT NOT NULL,
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
            tipo_agenda TEXT NOT NULL,
            cliente_aluno_nome TEXT NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            horario_termino TEXT,
            valor_total REAL DEFAULT 0.0,
            status TEXT NOT NULL,
            observacoes TEXT
        )
    ''')
    
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('admin', 'admin123', 'administrador')")
    conn.commit()
    conn.close()

# Inicializa o banco de dados novo
init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT usuario, senha, perfil FROM usuarios WHERE usuario = ? AND senha = ?', (usuario, senha)).fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['usuario'] = user[0]
            session['perfil'] = user[2]
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
    # Ignora validação rígida de sessão se estiver acessando diretamente
    if not session.get('logged_in'):
        session['logged_in'] = True
        session['usuario'] = 'admin'
        session['perfil'] = 'administrador'
    
    conn = get_db_connection()
    
    # Conversões garantidas para evitar quebras no HTML
    alunos = [tuple(row) for row in conn.execute('SELECT id, nome, email, telefone, instrumento, data_matricula FROM alunos ORDER BY nome ASC').fetchall()]
    professores = [tuple(row) for row in conn.execute('SELECT id, nome, email, telefone, especialidade FROM professores ORDER BY nome ASC').fetchall()]
    produtos = [tuple(row) for row in conn.execute('SELECT id, nome, categoria, preco, estoque FROM produtos').fetchall()]
    
    # Tratamento para evitar falhas se algum campo de texto vier nulo
    fluxo_caixa_raw = conn.execute('SELECT id, tipo, origem, descricao, valor, data FROM financeiro ORDER BY id DESC').fetchall()
    fluxo_caixa = []
    for row in fluxo_caixa_raw:
        fluxo_caixa.append((
            row[0],
            row[1] if row[1] else 'entrada',
            row[2] if row[2] else 'outros',
            row[3] if row[3] else '',
            row[4] if row[4] is not None else 0.0,
            row[5] if row[5] else ''
        ))
        
    agendamentos_raw = conn.execute('SELECT id, tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, status, observacoes FROM agenda ORDER BY data ASC, horario ASC').fetchall()
    agendamentos = []
    for row in agendamentos_raw:
        agendamentos.append((
            row[0],
            row[1] if row[1] else 'ensaio',
            row[2] if row[2] else '',
            row[3] if row[3] else '',
            row[4] if row[4] else '',
            row[5] if row[5] else '',
            row[6] if row[6] is not None else 0.0,
            row[7] if row[7] else 'Agendado',
            row[8] if row[8] else ''
        ))
    
    # Operações agregadas de caixa resilientes a nulos
    t_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='entrada'").fetchone()
    total_entradas = t_entradas[0] if t_entradas and t_entradas[0] is not None else 0.0
    
    t_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='saida'").fetchone()
    total_saidas = t_saidas[0] if t_saidas and t_saidas[0] is not None else 0.0
    
    saldo_atual = total_entradas - total_saidas
    conn.close()
    
    return render_template('index.html', 
                           alunos=alunos, 
                           professores=professores, 
                           produtos=produtos, 
                           fluxo_caixa=fluxo_caixa, 
                           agendamentos=agendamentos, 
                           total_entradas=total_entradas, 
                           total_saidas=total_saidas, 
                           saldo_atual=saldo_atual)

@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    instrumento = request.form.get('instrumento')
    data_matricula = request.form.get('data_matricula') or datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO alunos (nome, email, telefone, instrumento, data_matricula) VALUES (?, ?, ?, ?, ?)', 
                 (nome, email, telefone, instrumento, data_matricula))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_professor', methods=['POST'])
def cadastrar_professor():
    nome = request.form.get('nome')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    especialidade = request.form.get('especialidade')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO professores (nome, email, telefone, especialidade) VALUES (?, ?, ?, ?)', 
                 (nome, email, telefone, especialidade))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/agendar_studio', methods=['POST'])
def agendar_studio():
    tipo_agenda = request.form.get('tipo_agenda')
    cliente_aluno_nome = request.form.get('cliente_aluno_nome')
    data = request.form.get('data')
    status = request.form.get('status')
    horario = request.form.get('horario')
    horario_termino = request.form.get('horario_termino')
    valor_total = float(request.form.get('valor_total') or 0.0)
    observacoes = request.form.get('observacoes') or ""
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO agenda (tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, status, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tipo_agenda, cliente_aluno_nome, data, horario, horario_termino, valor_total, status, observacoes))
    
    if 'pago' in status.lower() and valor_total > 0:
        descricao_financeiro = f"Faturamento - Estúdio {tipo_agenda.capitalize()} | Cli: {cliente_aluno_nome}"
        conn.execute('''
            INSERT INTO financeiro (tipo, origem, descricao, valor, data)
            VALUES (?, ?, ?, ?, ?)
        ''', ('entrada', 'outros', descricao_financeiro, valor_total, datetime.now().strftime('%Y-%m-%d %H:%M')))
        
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/atualizar_status_studio/<int:id>', methods=['POST'])
def atualizar_status_studio(id):
    novo_status = request.form.get('novo_status')
    observacoes = request.form.get('observacoes') or ""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    compromisso = cursor.execute('SELECT tipo_agenda, cliente_aluno_nome, valor_total, status FROM agenda WHERE id = ?', (id,)).fetchone()
    
    if compromisso:
        conn.execute('UPDATE agenda SET status=?, observacoes=? WHERE id=?', (novo_status, observacoes, id))
        
        if novo_status == 'Agendamento pago' and compromisso[3] != 'Agendamento pago' and compromisso[2] > 0:
            descricao_financeiro = f"Faturamento (Concluído) - {compromisso[0].capitalize()} | Cli: {compromisso[1]}"
            conn.execute('''
                INSERT INTO financeiro (tipo, origem, descricao, valor, data)
                VALUES (?, ?, ?, ?, ?)
            ''', ('entrada', 'outros', descricao_financeiro, compromisso[2], datetime.now().strftime('%Y-%m-%d %H:%M')))
            
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_financeiro', methods=['POST'])
def cadastrar_financeiro():
    tipo = request.form.get('tipo')
    origem = request.form.get('origem')
    descricao = request.form.get('descricao')
    valor = float(request.form.get('valor') or 0.0)
    data_lancamento = request.form.get('data_lancamento') or datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO financeiro (tipo, origem, descricao, valor, data)
        VALUES (?, ?, ?, ?, ?)
    ''', (tipo, origem, descricao, valor, data_lancamento))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/remover_financeiro/<int:id>', methods=['POST'])
def remover_financeiro(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM financeiro WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/inverter_tipo_financeiro/<int:id>', methods=['POST'])
def inverter_tipo_financeiro(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    item = cursor.execute('SELECT tipo FROM financeiro WHERE id = ?', (id,)).fetchone()
    if item:
        novo_tipo = 'saida' if item[0] == 'entrada' else 'entrada'
        conn.execute('UPDATE financeiro SET tipo = ? WHERE id = ?', (novo_tipo, id))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/exportar_caixa_dia')
@app.route('/exportar_fechamento_mes')
def exportar_dummy():
    return "Função de exportação pronta para implementação futura.", 200

if __name__ == '__main__':
    app.run(debug=True)
