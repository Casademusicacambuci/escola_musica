import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci_2026"

DATABASE = "cambuci_v2.db"
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    # Permite acessar colunas pelo nome (ex: row['tipo']) se preferir, 
    # mas manteremos a compatibilidade com tuplas para o seu código atual
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    cursor.execute('''        
        CREATE TABLE IF NOT EXISTS professores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            especialidade TEXT
        )    
    ''')
    cursor.execute('''        
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,           
            preco REAL NOT NULL,
            estoque INTEGER NOT NULL
        )    
    ''')
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
    cursor.execute('''        
        CREATE TABLE IF NOT EXISTS usuarios (       
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )    
    ''')
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

init_db()

# --- ROTAS DE SIMULAÇÃO EXIGIDAS PELO INDEX.HTML ---
@app.route('/alternar_usuario/<perfil_alvo>')
def alternar_usuario(perfil_alvo):
    session['logged_in'] = True
    if perfil_alvo == 'caixa':
        session['usuario'] = 'Operador de Caixa'
        session['perfil'] = 'operador_caixa'
    else:
        session['usuario'] = 'Administrador'
        session['perfil'] = 'administrador'
    return redirect(url_for('index'))

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

# --- ROTA PRINCIPAL MAPEADA CORRETAMENTE ---
@app.route('/')
def index():
    if not session.get('logged_in'):
        session['logged_in'] = True
        session['usuario'] = 'Administrador'
        session['perfil'] = 'administrador'
        
    conn = get_db_connection()
    perfil = session.get('perfil', 'administrador')
    
    # 1. Filtro de Segurança / Escopo (Se for operador de caixa, pode-se limitar a ver apenas hoje se desejar)
    # Para manter simples e funcional com o HTML fornecido:
    query_financeiro = 'SELECT id, tipo, origem, descricao, valor, data FROM financeiro ORDER BY id DESC'
    
    fluxo_caixa_raw = conn.execute(query_financeiro).fetchall()
    movimentacoes = []
    for row in fluxo_caixa_raw:
        movimentacoes.append({
            'id': row[0],
            'tipo': row[1] if row[1] else 'Entrada',
            'origem': row[2] if row[2] else 'Outros',
            'descricao': row[3] if row[3] else '',
            'valor': row[4] if row[4] is not None else 0.0,
            'data': row[5] if row[5] else ''
        })
            
    # Cálculos dos cards agregados
    t_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='Entrada' OR tipo='entrada'").fetchone()
    total_entradas = t_entradas[0] if t_entradas and t_entradas[0] is not None else 0.0
        
    t_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='Saída' OR tipo='saida'").fetchone()
    total_saidas = t_saidas[0] if t_saidas and t_saidas[0] is not None else 0.0
        
    saldo_caixa = total_entradas - total_saidas  
    conn.close()
    
    # Passando os nomes EXATOS que o index.html está esperando
    return render_template('index.html',
                            nome_usuario=session.get('usuario'),
                            perfil=perfil,
                            movimentacoes=movimentacoes,
                            total_entradas=total_entradas,                     
                            total_saidas=total_saidas,                            
                            saldo_caixa=saldo_caixa)

# --- CORREÇÃO DA ROTA DE LANÇAMENTO (Alinhada com action="/lancar") ---
@app.route('/lancar', methods=['POST'])
def lancar():
    tipo = request.form.get('tipo') # Captura 'Entrada' ou 'Saída'
    origem = request.form.get('origem')
    descricao = request.form.get('descricao')
    valor = float(request.form.get('valor') or 0.0)
    data_competencia = request.form.get('data_competencia') or datetime.now().strftime('%Y-%m-%d')
        
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO financeiro (tipo, origem, descricao, valor, data)
        VALUES (?, ?, ?, ?, ?)
    ''', (tipo, origem, descricao, valor, data_competencia))
    conn.commit()  
    conn.close()
    return redirect(url_for('index'))

# --- CORREÇÃO DA ROTA DE EXCLUSÃO (Alinhada com href="/excluir/...") ---
@app.route('/excluir/<int:id>')
def excluir(id):
    # Verificação básica de segurança (opcional, baseada no HTML que esconde o botão)
    if session.get('perfil') == 'administrador':
        conn = get_db_connection()
        conn.execute('DELETE FROM financeiro WHERE id = ?', (id,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

# --- CORREÇÃO DAS ROTAS DE EXPORTAÇÃO ---
@app.route('/exportar/dia')
@app.route('/exportar/mes')
def exportar_arquivos():
    return "Função de exportação pronta para implementação futura.", 200

if __name__ == '__main__':
    app.run(debug=True)
