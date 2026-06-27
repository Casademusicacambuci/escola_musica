import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci_2026"
DATABASE = "cambuci.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Criando todas as tabelas necessárias do zero
    cursor.execute('CREATE TABLE IF NOT EXISTS alunos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, instrumento TEXT NOT NULL, telefone TEXT, data_matricula TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS professores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, especialidade TEXT NOT NULL, telefone TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, categoria TEXT NOT NULL, preco REAL NOT NULL, estoque INTEGER NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, categoria_fluxo TEXT NOT NULL, descricao TEXT NOT NULL, valor REAL NOT NULL, data TEXT NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL)')
    
    # Inserindo os logins padrões
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('admin', 'admin123', 'administrador')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('caixa', 'caixa123', 'caixa')")
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('secretaria', 'sec123', 'secretaria')")
    
    conn.commit()
    conn.close()

# Força a inicialização limpa do banco de dados
if not os.path.exists(DATABASE):
    init_db()
else:
    # Caso o arquivo já exista, garante que todas as novas tabelas sejam criadas por segurança
    init_db()

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
    
    # Busca segura dos dados para evitar quebras de página se as tabelas estiverem vazias
    try:
        alunos = conn.execute('SELECT * FROM alunos').fetchall()
    except:
        alunos = []
        
    try:
        professores = conn.execute('SELECT * FROM professores').fetchall()
    except:
        professores = []
        
    try:
        produtos = conn.execute('SELECT * FROM produtos').fetchall()
    except:
        produtos = []
        
    try:
        movimentacoes = conn.execute('SELECT * FROM financeiro ORDER BY id DESC').fetchall()
        total_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='entrada'").fetchone()[0] or 0.0
        total_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='saida'").fetchone()[0] or 0.0
    except:
        movimentacoes = []
        total_entradas = 0.0
        total_saidas = 0.0
        
    saldo_caixa = total_entradas - total_saidas
    conn.close()
    
    return render_template('index.html', alunos=alunos, professores=professores, produtos=produtos, movimentacoes=movimentacoes, total_entradas=total_entradas, total_saidas=total_saidas, saldo_caixa=saldo_caixa)

@app.route('/registrar_financeiro', methods=['POST'])
def registrar_financeiro():
    tipo = request.form.get('tipo')
    categoria = request.form.get('categoria_fluxo')
    descricao = request.form.get('descricao')
    valor = float(request.form.get('valor') or 0)
    
    conn = get_db_connection()
    conn.execute('INSERT INTO financeiro (tipo, categoria_fluxo, descricao, valor, data) VALUES (?, ?, ?, ?, ?)', 
                 (tipo, categoria, descricao, valor, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_produto', methods=['POST'])
def cadastrar_produto():
    nome = request.form.get('nome')
    categoria = request.form.get('categoria')
    preco = float(request.form.get('preco') or 0)
    estoque = int(request.form.get('estoque') or 0)
    
    conn = get_db_connection()
    conn.execute('INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (?, ?, ?, ?)', (nome, category, preco, estoque))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
